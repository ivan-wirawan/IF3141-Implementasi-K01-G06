from odoo import api, fields, models


class TritunggalInvoice(models.Model):
    _name = 'tritunggal.invoice'
    _description = 'Invoice'
    _rec_name = 'id_invoice'

    id_invoice = fields.Char(string='ID Invoice', required=True)
    tgl_terbit = fields.Date(string='Tanggal Terbit', default=fields.Date.context_today)
    tgl_jatuh_tempo = fields.Date(string='Tanggal Jatuh Tempo')
    status_pembayaran = fields.Char(string='Status Pembayaran')

    pesanan_id = fields.Many2one(
        comodel_name='tritunggal.pesanan',
        string='Pesanan',
        required=True,
        ondelete='cascade',
    )

    _sql_constraints = [
        ('pesanan_unique', 'unique(pesanan_id)', 'Invoice untuk pesanan ini sudah ada.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_invoice'):
                vals['id_invoice'] = self.env['ir.sequence'].next_by_code('tritunggal.invoice')
        return super().create(vals_list)
