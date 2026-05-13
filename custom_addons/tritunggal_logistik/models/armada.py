from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TritunggalArmada(models.Model):
    _name = 'tritunggal.armada'
    _description = 'Armada'
    _rec_name = 'id_armada'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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
        tracking=True,
    )
    tgl_servis_terakhir = fields.Date(string='Tanggal Servis Terakhir')
    nama_supir = fields.Char(string='Nama Supir')

    _sql_constraints = [
        (
            'plat_nomor_unique',
            'UNIQUE(plat_nomor)',
            'Plat nomor harus unik. Setiap armada harus memiliki plat nomor yang berbeda.',
        ),
    ]

    def cek_ketersediaan(self):
        for record in self:
            if record.status_armada != 'tersedia':
                raise ValidationError('Armada tidak tersedia untuk penugasan.')
        return True

    def cekKetersediaan(self):
        return self.cek_ketersediaan()

    def _get_next_id(self):
        """Generate next incremental ID for armada."""
        next_number = 0
        for record in self.search([]):
            identifier = record.id_armada or ''
            digits = ''.join(ch for ch in identifier if ch.isdigit())
            if digits:
                next_number = max(next_number, int(digits))
        return str(next_number + 1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_armada'):
                vals['id_armada'] = self._get_next_id()
        records = super().create(vals_list)
        # Log pembuatan armada
        for record in records:
            record.message_post(
                body=f'Armada dibuat oleh {self.env.user.name}',
                message_type='notification',
            )
        return records

    def action_back(self):
        """Close the current window without saving changes"""
        return {'type': 'ir.actions.act_window_close'}
