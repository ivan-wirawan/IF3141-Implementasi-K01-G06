from odoo import api, fields, models


class TritunggalRiwayatPerawatan(models.Model):
    _name = 'tritunggal.riwayat_perawatan'
    _description = 'Riwayat Perawatan Armada'
    _rec_name = 'id_perawatan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    id_perawatan = fields.Char(string='ID Perawatan', required=True)
    armada_id = fields.Many2one(
        comodel_name='tritunggal.armada',
        string='Armada',
        required=True,
        ondelete='cascade',
    )
    tanggal_perawatan = fields.Date(
        string='Tanggal Perawatan',
        default=fields.Date.context_today,
        required=True,
    )
    jenis_perawatan = fields.Selection(
        [
            ('servis_rutin', 'Servis Rutin'),
            ('perbaikan', 'Perbaikan'),
            ('penggantian_komponen', 'Penggantian Komponen'),
            ('inspeksi', 'Inspeksi'),
            ('lainnya', 'Lainnya'),
        ],
        string='Jenis Perawatan',
        default='servis_rutin',
        required=True,
    )
    deskripsi = fields.Text(string='Deskripsi', required=True)
    biaya = fields.Float(string='Biaya')
    petugas_id = fields.Many2one(
        comodel_name='res.users',
        string='Petugas',
        default=lambda self: self.env.user,
        required=True,
    )

    _sql_constraints = [
        (
            'id_perawatan_unique',
            'UNIQUE(id_perawatan)',
            'ID Perawatan harus unik untuk setiap catatan.',
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_perawatan'):
                vals['id_perawatan'] = self.env['ir.sequence'].next_by_code('tritunggal.riwayat_perawatan')
        records = super().create(vals_list)
        for record in records:
            if record.armada_id:
                record.armada_id.write({'tgl_servis_terakhir': record.tanggal_perawatan})
                if record.armada_id.status_armada == 'perbaikan':
                    record.armada_id.write({'status_armada': 'tersedia'})
        return records