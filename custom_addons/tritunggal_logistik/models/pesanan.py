from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TritunggalPesanan(models.Model):
    _name = 'tritunggal.pesanan'
    _description = 'Pesanan'
    _rec_name = 'id_pesanan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    id_pesanan = fields.Char(string='ID Pesanan', required=True)
    tgl_pesanan = fields.Date(string='Tanggal Pesanan', default=fields.Date.context_today, required=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        ondelete='set null',
    )
    alamat_asal = fields.Char(string='Alamat Asal', required=True)
    alamat_tujuan = fields.Char(string='Alamat Tujuan', required=True)
    status_pesanan = fields.Selection(
        [
            ('draft', 'Draft'),
            ('terverifikasi', 'Terverifikasi'),
            ('selesai', 'Selesai'),
        ],
        string='Status Pesanan',
        default='draft',
        required=True,
        tracking=True,
    )
    total_biaya = fields.Float(string='Total Biaya', compute='_compute_total', store=True)

    item_ids = fields.One2many(
        comodel_name='tritunggal.item_pesanan',
        inverse_name='pesanan_id',
        string='Item Pesanan',
    )
    invoice_id = fields.One2many(
        comodel_name='tritunggal.invoice',
        inverse_name='pesanan_id',
        string='Invoice',
        readonly=True,
    )

    @api.depends('item_ids.subtotal_harga')
    def _compute_total(self):
        self.compute_total()

    def compute_total(self):
        for record in self:
            record.total_biaya = sum(record.item_ids.mapped('subtotal_harga'))

    def hitung_total(self):
        self.compute_total()
        return self.total_biaya

    def hitungTotal(self):
        return self.hitung_total()

    def generate_invoice(self):
        for record in self.filtered(lambda rec: not rec.invoice_id):
            tgl_terbit = fields.Date.context_today(self)
            tgl_jatuh_tempo = tgl_terbit + relativedelta(days=14)
            self.env['tritunggal.invoice'].create(
                {
                    'tgl_terbit': tgl_terbit,
                    'tgl_jatuh_tempo': tgl_jatuh_tempo,
                    'status_pembayaran': 'Belum Lunas',
                    'pesanan_id': record.id,
                }
            )

    def generateInvoice(self):
        return self.generate_invoice()

    @api.model
    def buat_pesanan(self, values):
        return self.create(values)

    @api.model
    def buatPesanan(self, values):
        return self.buat_pesanan(values)

    def update_status(self, status):
        self.write({'status_pesanan': status})
        if status == 'terverifikasi':
            self.generate_invoice()
        return True

    def updateStatus(self, status):
        return self.update_status(status)

    def action_verify(self):
        self.write({'status_pesanan': 'terverifikasi'})
        self.generate_invoice()
        return True

    def action_complete(self):
        self.write({'status_pesanan': 'selesai'})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_pesanan'):
                vals['id_pesanan'] = self.env['ir.sequence'].next_by_code('tritunggal.pesanan')
        records = super().create(vals_list)
        records.filtered(lambda rec: rec.status_pesanan == 'terverifikasi').generate_invoice()
        return records

    def write(self, vals):
        result = super().write(vals)
        if vals.get('status_pesanan') == 'terverifikasi':
            self.filtered(lambda rec: not rec.invoice_id).generate_invoice()
        return result

    def action_create_penugasan_draft(self):
        """
        Tombol untuk membuat draf Penugasan Pengiriman otomatis
        saat pesanan dikonfirmasi dan menampilkan konfirmasi
        """
        for record in self:
            if record.status_pesanan != 'terverifikasi':
                raise ValidationError(
                    f'Pesanan {record.id_pesanan} belum diverifikasi. '
                    f'Verifikasi pesanan terlebih dahulu sebelum membuat penugasan.'
                )
            
            # Cek apakah penugasan sudah ada
            existing = self.env['tritunggal.penugasan_pengiriman'].search([
                ('pesanan_id', '=', record.id),
                ('status_penugasan', '!=', 'batal'),
            ])
            
            if existing:
                raise ValidationError(
                    f'Penugasan untuk pesanan ini sudah ada. '
                    f'ID Penugasan: {existing.id_penugasan}'
                )
            
            # Buat penugasan draft
            penugasan = self.env['tritunggal.penugasan_pengiriman'].create({
                'pesanan_id': record.id,
                'status_penugasan': 'draft',
            })
            
            record.message_post(
                body=f'Penugasan pengiriman draft telah dibuat otomatis: {penugasan.id_penugasan}',
                message_type='notification',
            )
            
            # Return action untuk membuka form penugasan dan tampilkan pesan
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Penugasan Pengiriman Dibuat',
                    'message': f'Penugasan {penugasan.id_penugasan} berhasil dibuat. Silakan isi supir, employee, dan armada sebelum menetapkan penugasan.',
                    'type': 'success',
                    'sticky': False,
                },
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'tritunggal.penugasan_pengiriman',
                    'res_id': penugasan.id,
                    'views': [[False, 'form']],
                    'target': 'current',
                }
            }
