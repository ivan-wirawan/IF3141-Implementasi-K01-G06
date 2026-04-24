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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('id_item'):
                vals['id_item'] = self.env['ir.sequence'].next_by_code('tritunggal.item_pesanan')
        return super().create(vals_list)
