from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TritunggalArmada(models.Model):
    _name = 'tritunggal.armada'
    _description = 'Armada'
    _rec_name = 'id_armada'

    id_armada = fields.Char(string='ID Armada', required=True)
    plat_nomor = fields.Char(string='Plat Nomor', required=True)
    kapasitas = fields.Float(string='Kapasitas')
    status_armada = fields.Selection(
        [
            ('tersedia', 'Tersedia'),
            ('perbaikan', 'Perbaikan'),
            ('digunakan', 'Digunakan'),
        ],
        string='Status Armada',
        default='tersedia',
        required=True,
    )
    tgl_servis_terakhir = fields.Date(string='Tanggal Servis Terakhir')
    nama_supir = fields.Char(string='Nama Supir')

    def cek_ketersediaan(self):
        for record in self:
            if record.status_armada != 'tersedia':
                raise ValidationError('Armada tidak tersedia untuk penugasan.')
        return True

    def cekKetersediaan(self):
        return self.cek_ketersediaan()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_armada'):
                vals['id_armada'] = self.env['ir.sequence'].next_by_code('tritunggal.armada')
        return super().create(vals_list)
