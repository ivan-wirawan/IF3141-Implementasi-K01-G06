from odoo import api, fields, models
from odoo.exceptions import ValidationError, AccessError
from odoo.osv import expression


class TritunggalPenugasanPengiriman(models.Model):
    _name = 'tritunggal.penugasan_pengiriman'
    _description = 'Penugasan Pengiriman'
    _rec_name = 'id_penugasan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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
        tracking=True,
    )
    catatan = fields.Text(string='Catatan')
    mitra_outsourcing_id = fields.Many2one(
        comodel_name='res.partner',
        string='Mitra Outsourcing',
        ondelete='set null',
    )
    status_output_mitra = fields.Selection(
        [('draft', 'Draft'), ('siap_dikirim', 'Siap Dikirim'), ('sudah_dikirim', 'Sudah Dikirim')],
        string='Status Output Mitra',
        default='draft',
    )

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

    _sql_constraints = [
        (
            'id_penugasan_unique',
            'UNIQUE(id_penugasan)',
            'ID Penugasan harus unik untuk setiap dokumen.',
        ),
    ]

    @api.constrains('supir_id', 'armada_id')
    def _check_driver_and_vehicle_availability(self):
        """
        Validasi bahwa supir dan armada tidak sedang bertugas atau perbaikan
        """
        for record in self:
            # Cek armada
            if record.armada_id.status_armada != 'tersedia':
                raise ValidationError(
                    f'Armada "{record.armada_id.plat_nomor}" tidak tersedia. '
                    f'Status saat ini: {record.armada_id.status_armada}. '
                    f'Pilih armada dengan status "Tersedia".'
                )

            # Cek supir tidak sedang aktif di penugasan lain
            active_assignments = self.search([
                ('supir_id', '=', record.supir_id.id),
                ('status_penugasan', 'in', ['ditugaskan', 'berjalan']),
                ('id', '!=', record.id),
            ])
            if active_assignments:
                raise ValidationError(
                    f'Supir "{record.nama_supir}" sedang bertugas pada penugasan lain. '
                    f'Tunggu sampai penugasan sebelumnya selesai sebelum menugaskan kembali.'
                )

    @api.constrains('employee_id')
    def _check_employee_not_duplicate(self):
        """
        Pastikan employee dalam satu penugasan tidak duplikat dengan supir
        """
        for record in self:
            if record.supir_id == record.employee_id:
                raise ValidationError(
                    'Field Supir dan Employee tidak boleh sama. '
                    'Pilih employee yang berbeda dari supir.'
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_penugasan'):
                vals['id_penugasan'] = self.env['ir.sequence'].next_by_code('tritunggal.penugasan_pengiriman')
        records = super().create(vals_list)
        # Log pembuatan penugasan
        for record in records:
            record.message_post(
                body=f'Penugasan dibuat oleh {self.env.user.name}',
                message_type='notification',
            )
        return records

    def write(self, vals):
        result = super().write(vals)
        # Otomatisasi: saat penugasan selesai, buat invoice
        if vals.get('status_penugasan') == 'selesai':
            self._trigger_invoice_creation()
        return result

    def _trigger_invoice_creation(self):
        """
        Otomatisasi: saat penugasan berubah status menjadi 'selesai',
        buat draft invoice jika belum ada
        """
        for record in self:
            pesanan = record.pesanan_id
            if pesanan and not pesanan.invoice_id:
                pesanan.generate_invoice()
                record.message_post(
                    body=f'Invoice otomatis dibuat untuk pesanan {pesanan.id_pesanan}',
                    message_type='notification',
                )

    def action_change_to_assigned(self):
        """Tombol untuk mengubah status menjadi 'Ditugaskan'"""
        self.write({'status_penugasan': 'ditugaskan'})
        self.message_post(body='Status diubah menjadi Ditugaskan', message_type='comment')

    def action_change_to_running(self):
        """Tombol untuk mengubah status menjadi 'Berjalan'"""
        self.write({'status_penugasan': 'berjalan'})
        self.message_post(body='Status diubah menjadi Berjalan', message_type='comment')

    def action_change_to_done(self):
        """Tombol untuk mengubah status menjadi 'Selesai'"""
        self.write({'status_penugasan': 'selesai'})
        self.message_post(body='Status diubah menjadi Selesai', message_type='comment')

    def action_cancel(self):
        """Tombol untuk membatalkan penugasan"""
        self.write({'status_penugasan': 'batal'})
        self.message_post(body='Penugasan dibatalkan', message_type='comment')

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """
        Domain filter: Supir hanya bisa melihat penugasan mereka sendiri
        """
        user = self.env.user
        if user.has_group('tritunggal_logistik.group_tritunggal_supir') and not user.has_group('base.group_system'):
            # Cari employee terkait user
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                # Supir hanya lihat penugasan mereka
                args = expression.AND([args, [('supir_id', '=', employee.id)]])
        return super()._search(args, offset, limit, order, count, access_rights_uid)