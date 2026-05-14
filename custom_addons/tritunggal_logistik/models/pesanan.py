from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TritunggalPesanan(models.Model):
    _name = 'tritunggal.pesanan'
    _description = 'Pesanan'
    _rec_name = 'id_pesanan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    id_pesanan = fields.Char(string='ID Pesanan', required=True, default=lambda self: self._get_next_id())
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
    vendor_type = fields.Selection(
        [
            ('internal', 'Internal'),
            ('outsource', 'Outsource'),
        ],
        string='Tipe Vendor',
        default='internal',
        required=True,
        tracking=True,
    )
    mitra_outsourcing_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor Outsource',
        domain=[('is_tritunggal_outsource_vendor', '=', True)],
        ondelete='set null',
    )
    status_vendor = fields.Selection(
        [
            ('draft', 'Draft'),
            ('waiting_acceptance', 'Menunggu Persetujuan'),
            ('accepted', 'Diterima'),
            ('rejected', 'Ditolak'),
        ],
        string='Status Vendor',
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
    pengiriman_ids = fields.One2many(
        comodel_name='tritunggal.pengiriman',
        inverse_name='pesanan_id',
        string='Pengiriman',
        readonly=True,
    )

    @api.onchange('vendor_type')
    def _onchange_vendor_type(self):
        if self.vendor_type == 'internal':
            self.mitra_outsourcing_id = False
            self.status_vendor = 'draft'
        elif self.vendor_type == 'outsource' and self.status_vendor == 'draft':
            self.status_vendor = 'waiting_acceptance'

    @api.onchange('mitra_outsourcing_id')
    def _onchange_mitra_outsourcing_id(self):
        if self.vendor_type == 'outsource' and self.mitra_outsourcing_id:
            self.status_vendor = 'waiting_acceptance'

    @api.constrains('vendor_type', 'mitra_outsourcing_id')
    def _check_vendor_selection(self):
        for record in self:
            if record.vendor_type == 'outsource' and not record.mitra_outsourcing_id:
                raise ValidationError('Vendor outsource wajib dipilih jika tipe vendor adalah Outsource.')
            if record.vendor_type == 'internal' and record.mitra_outsourcing_id:
                raise ValidationError('Vendor outsource hanya boleh diisi jika tipe vendor adalah Outsource.')

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
        for record in self:
            values = {'status_pesanan': 'terverifikasi'}
            if record.vendor_type == 'outsource':
                values['status_vendor'] = 'waiting_acceptance'
            record.write(values)
        self.generate_invoice()
        return True

    def action_complete(self):
        self.write({'status_pesanan': 'selesai'})
        return True

    def action_back(self):
        """Close the current window without saving changes"""
        return {'type': 'ir.actions.act_window_close'}

    def _get_next_id(self):
        """Generate next incremental ID for pesanan."""
        next_number = 0
        for record in self.search([]):
            identifier = record.id_pesanan or ''
            digits = ''.join(ch for ch in identifier if ch.isdigit())
            if digits:
                next_number = max(next_number, int(digits))
        return str(next_number + 1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['id_pesanan'] = self._get_next_id()
            if vals.get('mitra_outsourcing_id') and not vals.get('vendor_type'):
                vals['vendor_type'] = 'outsource'
            if vals.get('vendor_type') == 'internal':
                vals['mitra_outsourcing_id'] = False
                vals.setdefault('status_vendor', 'draft')
            elif vals.get('vendor_type') == 'outsource':
                vals.setdefault('status_vendor', 'waiting_acceptance')
        records = super().create(vals_list)
        records.filtered(lambda rec: rec.status_pesanan == 'terverifikasi').generate_invoice()
        return records

    def write(self, vals):
        if vals.get('vendor_type') == 'internal':
            vals['mitra_outsourcing_id'] = False
            vals['status_vendor'] = 'draft'
        elif vals.get('vendor_type') == 'outsource':
            vals.setdefault('status_vendor', 'waiting_acceptance')
        elif vals.get('mitra_outsourcing_id') and 'status_vendor' not in vals:
            vals['status_vendor'] = 'waiting_acceptance'
        result = super().write(vals)
        if vals.get('status_pesanan') == 'terverifikasi':
            self.filtered(lambda rec: not rec.invoice_id).generate_invoice()
        return result

    def _get_outsource_pengiriman(self):
        self.ensure_one()
        return self.env['tritunggal.pengiriman'].search([
            ('pesanan_id', '=', self.id),
            ('delivery_provider_type', '=', 'outsource'),
            ('mitra_outsourcing_id', '=', self.mitra_outsourcing_id.id),
        ], limit=1)

    def action_outsource_accept(self):
        for record in self:
            if record.vendor_type != 'outsource' or not record.mitra_outsourcing_id:
                raise ValidationError('Pesanan ini bukan pesanan outsource.')
            if record.status_pesanan != 'terverifikasi':
                raise ValidationError('Pesanan harus diverifikasi sebelum dapat diterima vendor.')
            if record.status_vendor == 'accepted':
                continue
            if record.status_vendor != 'waiting_acceptance':
                raise ValidationError('Pesanan hanya dapat diterima saat menunggu persetujuan vendor.')
            record.write({'status_vendor': 'accepted'})
            if not record._get_outsource_pengiriman():
                pengiriman = self.env['tritunggal.pengiriman'].create({
                    'pesanan_id': record.id,
                    'delivery_provider_type': 'outsource',
                    'mitra_outsourcing_id': record.mitra_outsourcing_id.id,
                    'status_pengiriman': 'draft',
                    'lokasi_terkini': record.alamat_asal,
                })
                record.message_post(
                    body=f'Vendor outsource menerima pesanan. Pengiriman {pengiriman.id_pengiriman} dibuat.',
                    message_type='notification',
                )
        return True

    def action_outsource_reject(self):
        for record in self:
            if record.vendor_type != 'outsource' or not record.mitra_outsourcing_id:
                raise ValidationError('Pesanan ini bukan pesanan outsource.')
            if record.status_vendor != 'waiting_acceptance':
                raise ValidationError('Pesanan hanya dapat ditolak saat menunggu persetujuan vendor.')
            record.write({'status_vendor': 'rejected'})
            record.message_post(
                body='Vendor outsource menolak pesanan. Pesanan siap dialihkan oleh operasional.',
                message_type='notification',
            )
        return True

    def action_create_penugasan_draft(self):
        """
        Tombol untuk membuat draf Penugasan Pengiriman otomatis
        saat pesanan dikonfirmasi dan menampilkan konfirmasi
        """
        for record in self:
            if record.vendor_type != 'internal':
                raise ValidationError('Penugasan internal hanya dapat dibuat untuk pesanan dengan tipe vendor Internal.')
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
