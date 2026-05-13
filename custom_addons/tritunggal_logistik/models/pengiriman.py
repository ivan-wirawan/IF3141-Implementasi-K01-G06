from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TritunggalPengiriman(models.Model):
    _name = 'tritunggal.pengiriman'
    _description = 'Pengiriman'
    _rec_name = 'id_pengiriman'

    id_pengiriman = fields.Char(string='ID Pengiriman', required=True)
    tgl_berangkat = fields.Date(string='Tanggal Berangkat')
    estimasi_tiba = fields.Date(string='Estimasi Tiba')
    status_pengiriman = fields.Selection(
        [
            ('draft', 'Draft'),
            ('berangkat', 'Berangkat'),
            ('dalam_perjalanan', 'Dalam Perjalanan'),
            ('tiba', 'Tiba'),
            ('terkendala', 'Terkendala'),
        ],
        string='Status Pengiriman',
        default='draft',
        required=True,
    )
    lokasi_terkini = fields.Char(string='Lokasi Terkini')
    bukti_foto = fields.Image(string='Bukti Foto')
    gps_lat = fields.Float(string='GPS Latitude')
    gps_lng = fields.Float(string='GPS Longitude')
    gps_timestamp = fields.Datetime(string='GPS Timestamp')

    pesanan_id = fields.Many2one(
        comodel_name='tritunggal.pesanan',
        string='Pesanan',
        required=True,
        ondelete='cascade',
    )
    armada_id = fields.Many2one(
        comodel_name='tritunggal.armada',
        string='Armada',
        ondelete='set null',
    )

    def _assign_armada(self, armada):
        if armada:
            armada.cek_ketersediaan()
            armada.write({'status_armada': 'digunakan'})

    def update_status_logistik(self, status=None, lokasi=None, bukti=None):
        for record in self:
            if not status:
                raise ValidationError('Status pengiriman wajib diisi.')
            if not (bukti or record.bukti_foto):
                raise ValidationError('Bukti foto wajib diunggah.')
            values = {
                'status_pengiriman': status,
            }
            if lokasi is not None:
                values['lokasi_terkini'] = lokasi
            if bukti is not None:
                values['bukti_foto'] = bukti
            record.write(values)
            if status == 'tiba' and record.armada_id:
                record.armada_id.write({'status_armada': 'tersedia'})

    def updateStatusLogistik(self, status=None, lokasi=None, bukti=None):
        return self.update_status_logistik(status=status, lokasi=lokasi, bukti=bukti)

    def update_status_pengiriman(self, status=None, lokasi=None, bukti=None):
        return self.update_status_logistik(status=status, lokasi=lokasi, bukti=bukti)

    def updateStatusPengiriman(self, status=None, lokasi=None, bukti=None):
        return self.update_status_pengiriman(status=status, lokasi=lokasi, bukti=bukti)

    def catat_koordinat(self, lat, lng, timestamp=None, lokasi=None):
        for record in self:
            record.write(
                {
                    'gps_lat': lat,
                    'gps_lng': lng,
                    'gps_timestamp': timestamp or fields.Datetime.now(),
                    'lokasi_terkini': lokasi or record.lokasi_terkini,
                }
            )
        return True

    def catatKoordinat(self, lat, lng, timestamp=None, lokasi=None):
        return self.catat_koordinat(lat=lat, lng=lng, timestamp=timestamp, lokasi=lokasi)

    def _get_next_id(self):
        """Generate next incremental ID for pengiriman."""
        next_number = 0
        for record in self.search([]):
            identifier = record.id_pengiriman or ''
            digits = ''.join(ch for ch in identifier if ch.isdigit())
            if digits:
                next_number = max(next_number, int(digits))
        return str(next_number + 1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_pengiriman'):
                vals['id_pengiriman'] = self._get_next_id()
        records = super().create(vals_list)
        for record in records:
            if record.armada_id:
                record._assign_armada(record.armada_id)
        return records

    def write(self, vals):
        if vals.get('armada_id'):
            armada = self.env['tritunggal.armada'].browse(vals['armada_id'])
            if armada:
                self._assign_armada(armada)
        return super().write(vals)

    def action_back(self):
        """Close the current window without saving changes"""
        return {'type': 'ir.actions.act_window_close'}
