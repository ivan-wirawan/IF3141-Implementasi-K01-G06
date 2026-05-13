from odoo import api, fields, models


class TritunggalPenugasanPengiriman(models.Model):
    _name = 'tritunggal.penugasan_pengiriman'
    _description = 'Penugasan Pengiriman'
    _rec_name = 'id_penugasan'

    id_penugasan = fields.Char(string='ID Penugasan', required=True)
    tgl_penugasan = fields.Date(
        string='Tanggal Penugasan',
        default=fields.Date.context_today,
        required=True,
    )
    status_penugasan = fields.Selection(
        [
            ('draft', 'Draft'),
            ('ditugaskan', 'Ditugaskan'),
            ('berjalan', 'Berjalan'),
            ('selesai', 'Selesai'),
            ('batal', 'Batal'),
        ],
        string='Status Penugasan',
        default='draft',
        required=True,
    )
    catatan = fields.Text(string='Catatan')

    pesanan_id = fields.Many2one(
        comodel_name='tritunggal.pesanan',
        string='Pesanan',
        required=True,
        ondelete='cascade',
    )
    pengiriman_id = fields.Many2one(
        comodel_name='tritunggal.pengiriman',
        string='Pengiriman',
        ondelete='set null',
    )
    supir_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Supir',
        required=True,
        ondelete='restrict',
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
    )
    armada_id = fields.Many2one(
        comodel_name='tritunggal.armada',
        string='Kendaraan',
        required=True,
        ondelete='restrict',
    )

    nama_supir = fields.Char(related='supir_id.name', string='Nama Supir', store=True, readonly=True)
    nama_employee = fields.Char(related='employee_id.name', string='Nama Employee', store=True, readonly=True)
    plat_nomor = fields.Char(related='armada_id.plat_nomor', string='Plat Nomor', store=True, readonly=True)
    alamat_tujuan = fields.Char(related='pesanan_id.alamat_tujuan', string='Alamat Tujuan', store=True, readonly=True)
    status_pesanan = fields.Selection(related='pesanan_id.status_pesanan', string='Status Pesanan', store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_penugasan'):
                vals['id_penugasan'] = self.env['ir.sequence'].next_by_code('tritunggal.penugasan_pengiriman')
        return super().create(vals_list)