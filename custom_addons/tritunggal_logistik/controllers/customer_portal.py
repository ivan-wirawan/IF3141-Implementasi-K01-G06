from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class TritunggalCustomerPortal(http.Controller):
    def _get_partner(self):
        partner = request.env.user.partner_id.commercial_partner_id
        if not partner:
            raise AccessError('Partner customer tidak ditemukan')
        return partner

    def _get_customer_orders(self, partner):
        return request.env['tritunggal.pesanan'].sudo().search([
            ('partner_id', '=', partner.id),
        ], order='tgl_pesanan desc, id desc')

    def _get_customer_invoices(self, partner):
        return request.env['tritunggal.invoice'].sudo().search([
            ('partner_id', '=', partner.id),
        ], order='tgl_terbit desc, id desc')

    @http.route(['/my/tritunggal', '/my/tritunggal/home'], type='http', auth='user', website=True)
    def portal_home(self, **kwargs):
        partner = self._get_partner()
        pesanan_count = request.env['tritunggal.pesanan'].sudo().search_count([('partner_id', '=', partner.id)])
        invoice_count = request.env['tritunggal.invoice'].sudo().search_count([('partner_id', '=', partner.id)])
        return request.render('tritunggal_logistik.portal_home_template', {
            'partner': partner,
            'pesanan_count': pesanan_count,
            'invoice_count': invoice_count,
            'pesanan_recent': self._get_customer_orders(partner)[:5],
            'invoice_recent': self._get_customer_invoices(partner)[:5],
        })

    @http.route('/my/tritunggal/pesanan', type='http', auth='user', website=True)
    def portal_pesanan(self, **kwargs):
        partner = self._get_partner()
        return request.render('tritunggal_logistik.portal_pesanan_list_template', {
            'partner': partner,
            'pesanan_list': self._get_customer_orders(partner),
        })

    @http.route('/my/tritunggal/invoice', type='http', auth='user', website=True)
    def portal_invoice(self, **kwargs):
        partner = self._get_partner()
        return request.render('tritunggal_logistik.portal_invoice_list_template', {
            'partner': partner,
            'invoice_list': self._get_customer_invoices(partner),
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