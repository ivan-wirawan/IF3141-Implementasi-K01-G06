from odoo import http
from odoo.http import request


class TritunggalGpsController(http.Controller):
    @http.route('/tritunggal_logistik/gps/update', type='json', auth='public', methods=['POST'], csrf=False)
    def update_gps(self, **payload):
        pengiriman_id = payload.get('pengiriman_id')
        kode_pengiriman = payload.get('id_pengiriman')
        lat = payload.get('lat')
        lng = payload.get('lng')
        timestamp = payload.get('timestamp')
        lokasi = payload.get('lokasi')
        api_key = payload.get('api_key') or request.httprequest.headers.get('X-Tritunggal-GPS-Token')

        configured_token = request.env['ir.config_parameter'].sudo().get_param('tritunggal_logistik.gps_api_token')
        if not configured_token:
            return {'success': False, 'message': 'Token GPS belum dikonfigurasi di pengaturan sistem'}
        if api_key != configured_token:
            return {'success': False, 'message': 'Token GPS tidak valid'}

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
