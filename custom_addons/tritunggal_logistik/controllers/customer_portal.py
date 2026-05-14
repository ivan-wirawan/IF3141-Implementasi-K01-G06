from odoo import fields, http
from odoo.exceptions import AccessError
from odoo.http import request


class TritunggalCustomerPortal(http.Controller):
    def _get_current_partner(self):
        partner = request.env.user.partner_id.commercial_partner_id
        if not partner:
            raise AccessError('Partner tidak ditemukan')
        return partner

    def _get_partner(self):
        if request.env.user.has_group('tritunggal_logistik.group_tritunggal_outsource'):
            raise AccessError('Vendor outsource hanya dapat mengakses portal vendor outsource.')
        return self._get_current_partner()

    def _get_outsource_partner(self):
        if not request.env.user.has_group('tritunggal_logistik.group_tritunggal_outsource'):
            raise AccessError('Anda tidak memiliki akses sebagai vendor outsource.')
        partner = self._get_current_partner()
        if not partner.is_tritunggal_outsource_vendor:
            raise AccessError('Partner user ini belum terdaftar sebagai vendor outsource.')
        return partner

    def _get_customer_orders(self, partner):
        return request.env['tritunggal.pesanan'].sudo().search([
            ('partner_id', '=', partner.id),
        ], order='tgl_pesanan desc, id desc')

    def _get_customer_invoices(self, partner):
        return request.env['tritunggal.invoice'].sudo().search([
            ('partner_id', '=', partner.id),
        ], order='tgl_terbit desc, id desc')

    def _get_customer_tracking_rows(self, partner):
        pesanan_list = self._get_customer_orders(partner)
        if not pesanan_list:
            return []

        pengiriman_list = request.env['tritunggal.pengiriman'].sudo().search([
            ('pesanan_id', 'in', pesanan_list.ids),
        ], order='gps_timestamp desc, id desc')
        penugasan_list = request.env['tritunggal.penugasan_pengiriman'].sudo().search([
            ('pesanan_id', 'in', pesanan_list.ids),
        ], order='tgl_penugasan desc, id desc')

        pengiriman_by_pesanan = {}
        for pengiriman in pengiriman_list:
            pengiriman_by_pesanan.setdefault(pengiriman.pesanan_id.id, pengiriman)

        penugasan_by_pesanan = {}
        for penugasan in penugasan_list:
            penugasan_by_pesanan.setdefault(penugasan.pesanan_id.id, penugasan)

        rows = []
        for pesanan in pesanan_list:
            penugasan = penugasan_by_pesanan.get(pesanan.id)
            pengiriman = pengiriman_by_pesanan.get(pesanan.id) or (penugasan and penugasan.pengiriman_id)
            rows.append({
                'pesanan': pesanan,
                'penugasan': penugasan,
                'pengiriman': pengiriman,
            })
        return rows

    def _get_outsource_orders(self, partner):
        return request.env['tritunggal.pesanan'].sudo().search([
            ('vendor_type', '=', 'outsource'),
            ('mitra_outsourcing_id', '=', partner.id),
        ], order='tgl_pesanan desc, id desc')

    def _get_outsource_order(self, partner, pesanan_id):
        pesanan = request.env['tritunggal.pesanan'].sudo().browse(pesanan_id)
        if not pesanan.exists() or pesanan.vendor_type != 'outsource' or pesanan.mitra_outsourcing_id.id != partner.id:
            raise AccessError('Pesanan tidak ditemukan untuk vendor ini.')
        return pesanan

    def _get_outsource_shipments(self, partner):
        return request.env['tritunggal.pengiriman'].sudo().search([
            ('delivery_provider_type', '=', 'outsource'),
            ('mitra_outsourcing_id', '=', partner.id),
        ], order='gps_timestamp desc, id desc')

    @http.route(['/my/tritunggal', '/my/tritunggal/home'], type='http', auth='user', website=True)
    def portal_home(self, **kwargs):
        partner = self._get_partner()
        pesanan_count = request.env['tritunggal.pesanan'].sudo().search_count([('partner_id', '=', partner.id)])
        invoice_count = request.env['tritunggal.invoice'].sudo().search_count([('partner_id', '=', partner.id)])
        tracking_rows = self._get_customer_tracking_rows(partner)
        return request.render('tritunggal_logistik.portal_home_template', {
            'partner': partner,
            'pesanan_count': pesanan_count,
            'invoice_count': invoice_count,
            'pesanan_recent': self._get_customer_orders(partner)[:5],
            'invoice_recent': self._get_customer_invoices(partner)[:5],
            'tracking_count': len(tracking_rows),
            'tracking_recent': tracking_rows[:5],
        })

    @http.route('/my/tritunggal/pesanan', type='http', auth='user', website=True)
    def portal_pesanan(self, **kwargs):
        partner = self._get_partner()
        tracking_rows = self._get_customer_tracking_rows(partner)
        tracking_by_pesanan = {row['pesanan'].id: row for row in tracking_rows}
        return request.render('tritunggal_logistik.portal_pesanan_list_template', {
            'partner': partner,
            'pesanan_list': self._get_customer_orders(partner),
            'tracking_by_pesanan': tracking_by_pesanan,
        })

    @http.route('/my/tritunggal/invoice', type='http', auth='user', website=True)
    def portal_invoice(self, **kwargs):
        partner = self._get_partner()
        return request.render('tritunggal_logistik.portal_invoice_list_template', {
            'partner': partner,
            'invoice_list': self._get_customer_invoices(partner),
        })

    @http.route('/my/tritunggal/tracking', type='http', auth='user', website=True)
    def portal_tracking(self, **kwargs):
        partner = self._get_partner()
        return request.render('tritunggal_logistik.portal_tracking_template', {
            'partner': partner,
            'tracking_rows': self._get_customer_tracking_rows(partner),
        })

    @http.route(['/my/tritunggal/pesanan/new'], type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=True)
    def portal_new_pesanan(self, **post):
        partner = self._get_partner()
        error_message = None
        success = False

        if request.httprequest.method == 'POST':
            alamat_asal = (post.get('alamat_asal') or '').strip()
            alamat_tujuan = (post.get('alamat_tujuan') or '').strip()

            item_lines = []
            for index in range(1, 4):
                jumlah_barang = post.get(f'jumlah_barang_{index}')
                volume_barang = post.get(f'volume_barang_{index}')
                berat_barang = post.get(f'berat_barang_{index}')
                subtotal_harga = post.get(f'subtotal_harga_{index}')

                if any(value for value in [jumlah_barang, volume_barang, berat_barang, subtotal_harga]):
                    if not jumlah_barang:
                        error_message = 'Jumlah barang harus diisi untuk setiap item yang dikirim.'
                        break
                    item_lines.append((0, 0, {
                        'jumlah_barang': int(jumlah_barang),
                        'volume_barang': float(volume_barang or 0.0),
                        'berat_barang': float(berat_barang or 0.0),
                        'subtotal_harga': float(subtotal_harga or 0.0),
                    }))

            if not error_message:
                if not alamat_asal or not alamat_tujuan:
                    error_message = 'Alamat asal dan tujuan wajib diisi.'
                else:
                    request.env['tritunggal.pesanan'].sudo().create({
                        'partner_id': partner.id,
                        'alamat_asal': alamat_asal,
                        'alamat_tujuan': alamat_tujuan,
                        'status_pesanan': 'draft',
                        'item_ids': item_lines,
                    })
                    success = True

        return request.render('tritunggal_logistik.portal_new_pesanan_template', {
            'partner': partner,
            'error_message': error_message,
            'success': success,
        })

    @http.route('/my/tritunggal/outsource', type='http', auth='user', website=True)
    def portal_outsource_home(self, **kwargs):
        partner = self._get_outsource_partner()
        order_list = self._get_outsource_orders(partner)
        shipment_list = self._get_outsource_shipments(partner)
        return request.render('tritunggal_logistik.portal_outsource_home_template', {
            'partner': partner,
            'order_list': order_list,
            'order_recent': order_list[:5],
            'shipment_list': shipment_list,
            'shipment_recent': shipment_list[:5],
        })

    @http.route('/my/tritunggal/outsource/orders', type='http', auth='user', website=True)
    def portal_outsource_orders(self, **kwargs):
        partner = self._get_outsource_partner()
        return request.render('tritunggal_logistik.portal_outsource_order_list_template', {
            'partner': partner,
            'order_list': self._get_outsource_orders(partner),
        })

    @http.route('/my/tritunggal/outsource/orders/<int:pesanan_id>', type='http', auth='user', website=True)
    def portal_outsource_order_detail(self, pesanan_id, **kwargs):
        partner = self._get_outsource_partner()
        pesanan = self._get_outsource_order(partner, pesanan_id)
        shipment_list = request.env['tritunggal.pengiriman'].sudo().search([
            ('pesanan_id', '=', pesanan.id),
            ('delivery_provider_type', '=', 'outsource'),
            ('mitra_outsourcing_id', '=', partner.id),
        ], order='id desc')
        return request.render('tritunggal_logistik.portal_outsource_order_detail_template', {
            'partner': partner,
            'pesanan': pesanan,
            'shipment_list': shipment_list,
        })

    @http.route('/my/tritunggal/outsource/orders/<int:pesanan_id>/accept', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_outsource_accept_order(self, pesanan_id, **post):
        partner = self._get_outsource_partner()
        pesanan = self._get_outsource_order(partner, pesanan_id)
        pesanan.action_outsource_accept()
        return request.redirect(f'/my/tritunggal/outsource/orders/{pesanan.id}')

    @http.route('/my/tritunggal/outsource/orders/<int:pesanan_id>/reject', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_outsource_reject_order(self, pesanan_id, **post):
        partner = self._get_outsource_partner()
        pesanan = self._get_outsource_order(partner, pesanan_id)
        pesanan.action_outsource_reject()
        return request.redirect(f'/my/tritunggal/outsource/orders/{pesanan.id}')

    @http.route('/my/tritunggal/outsource/shipments', type='http', auth='user', website=True)
    def portal_outsource_shipments(self, **kwargs):
        partner = self._get_outsource_partner()
        return request.render('tritunggal_logistik.portal_outsource_shipment_list_template', {
            'partner': partner,
            'shipment_list': self._get_outsource_shipments(partner),
        })

    @http.route('/my/tritunggal/outsource/shipments/<int:shipment_id>/update', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_outsource_update_shipment(self, shipment_id, **post):
        partner = self._get_outsource_partner()
        pengiriman = request.env['tritunggal.pengiriman'].sudo().browse(shipment_id)
        if not pengiriman.exists() or pengiriman.mitra_outsourcing_id.id != partner.id:
            raise AccessError('Pengiriman tidak ditemukan untuk vendor ini.')

        allowed_statuses = {'draft', 'berangkat', 'dalam_perjalanan', 'tiba', 'terkendala'}
        values = {}
        status = post.get('status_pengiriman')
        if status in allowed_statuses:
            values['status_pengiriman'] = status
        lokasi = (post.get('lokasi_terkini') or '').strip()
        if lokasi:
            values['lokasi_terkini'] = lokasi

        lat = (post.get('gps_lat') or '').strip()
        lng = (post.get('gps_lng') or '').strip()
        if lat and lng:
            try:
                values['gps_lat'] = float(lat)
                values['gps_lng'] = float(lng)
                values['gps_timestamp'] = fields.Datetime.now()
            except ValueError:
                pass

        if values:
            pengiriman.write(values)
        return request.redirect('/my/tritunggal/outsource/shipments')
