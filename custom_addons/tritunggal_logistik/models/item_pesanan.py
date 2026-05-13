from odoo import api, fields, models


class TritunggalItemPesanan(models.Model):
    _name = 'tritunggal.item_pesanan'
    _description = 'Item Pesanan'
    _rec_name = 'id_item'

    id_item = fields.Char(string='ID Item', required=True)
    jumlah_barang = fields.Integer(string='Jumlah Barang', required=True)
    volume_barang = fields.Float(string='Volume Barang')
    berat_barang = fields.Float(string='Berat Barang')
    subtotal_harga = fields.Float(string='Subtotal Harga')

    pesanan_id = fields.Many2one(
        comodel_name='tritunggal.pesanan',
        string='Pesanan',
        required=True,
        ondelete='cascade',
    )

    def _get_next_id(self):
        """Generate next incremental ID for item pesanan."""
        next_number = 0
        for record in self.search([]):
            identifier = record.id_item or ''
            digits = ''.join(ch for ch in identifier if ch.isdigit())
            if digits:
                next_number = max(next_number, int(digits))
        return str(next_number + 1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_item'):
                vals['id_item'] = self._get_next_id()
        return super().create(vals_list)

    def action_back(self):
        """Close the current window without saving changes"""
        return {'type': 'ir.actions.act_window_close'}
