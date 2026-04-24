from odoo import http
from odoo.http import request


class TritunggalGpsController(http.Controller):
    @http.route('/tritunggal_logistik/gps/update', type='json', auth='user', methods=['POST'], csrf=False)
    def update_gps(self, **payload):
        pengiriman_id = payload.get('pengiriman_id')
        kode_pengiriman = payload.get('id_pengiriman')
        lat = payload.get('lat')
        lng = payload.get('lng')
        timestamp = payload.get('timestamp')
        lokasi = payload.get('lokasi')

        if lat is None or lng is None:
            return {'success': False, 'message': 'lat dan lng wajib diisi'}

        pengiriman = None
        if pengiriman_id:
            pengiriman = request.env['tritunggal.pengiriman'].sudo().browse(int(pengiriman_id))
        elif kode_pengiriman:
            pengiriman = request.env['tritunggal.pengiriman'].sudo().search([('id_pengiriman', '=', kode_pengiriman)], limit=1)

        if not pengiriman:
            return {'success': False, 'message': 'Pengiriman tidak ditemukan'}

        pengiriman.catat_koordinat(lat=float(lat), lng=float(lng), timestamp=timestamp, lokasi=lokasi)
        return {'success': True}
