from odoo import api, fields, models


class TritunggalInvoice(models.Model):
    _name = 'tritunggal.invoice'
    _description = 'Invoice'
    _rec_name = 'id_invoice'

    id_invoice = fields.Char(string='ID Invoice', required=True)
    tgl_terbit = fields.Date(string='Tanggal Terbit', default=fields.Date.context_today)
    tgl_jatuh_tempo = fields.Date(string='Tanggal Jatuh Tempo')
    status_pembayaran = fields.Char(string='Status Pembayaran')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        related='pesanan_id.partner_id',
        string='Customer',
        store=True,
        readonly=True,
    )
    total_biaya = fields.Float(
        related='pesanan_id.total_biaya',
        string='Total Biaya',
        store=True,
        readonly=True,
    )

    pesanan_id = fields.Many2one(
        comodel_name='tritunggal.pesanan',
        string='Pesanan',
        required=True,
        ondelete='cascade',
    )

    _sql_constraints = [
        ('pesanan_unique', 'unique(pesanan_id)', 'Invoice untuk pesanan ini sudah ada.'),
    ]

    def _get_next_id(self):
        """Generate next incremental ID for invoice."""
        next_number = 0
        for record in self.search([]):
            identifier = record.id_invoice or ''
            digits = ''.join(ch for ch in identifier if ch.isdigit())
            if digits:
                next_number = max(next_number, int(digits))
        return str(next_number + 1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_invoice'):
                vals['id_invoice'] = self._get_next_id()
        return super().create(vals_list)

    def action_back(self):
        """Close the current window without saving changes"""
        return {'type': 'ir.actions.act_window_close'}
