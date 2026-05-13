from odoo import api, fields, models


class TritunggalLaporanKerusakan(models.Model):
    _name = 'tritunggal.laporan_kerusakan'
    _description = 'Laporan Kerusakan Armada'
    _rec_name = 'id_laporan'

    id_laporan = fields.Char(string='ID Laporan', required=True)
    armada_id = fields.Many2one(
        comodel_name='tritunggal.armada',
        string='Armada',
        required=True,
        ondelete='cascade',
    )
    pelapor_id = fields.Many2one(
        comodel_name='res.users',
        string='Pelapor',
        default=lambda self: self.env.user,
        required=True,
    )
    tgl_laporan = fields.Date(string='Tanggal Laporan', default=fields.Date.context_today, required=True)
    deskripsi = fields.Text(string='Deskripsi Kerusakan', required=True)
    bukti_foto = fields.Image(string='Bukti Foto')

    def _get_next_id(self):
        """Generate next incremental ID for laporan kerusakan."""
        next_number = 0
        for record in self.search([]):
            identifier = record.id_laporan or ''
            digits = ''.join(ch for ch in identifier if ch.isdigit())
            if digits:
                next_number = max(next_number, int(digits))
        return str(next_number + 1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_laporan'):
                vals['id_laporan'] = self._get_next_id()
        records = super().create(vals_list)
        for record in records:
            if record.armada_id:
                record.armada_id.write({'status_armada': 'perbaikan'})
        return records

    def action_back(self):
        """Close the current window without saving changes"""
        return {'type': 'ir.actions.act_window_close'}
