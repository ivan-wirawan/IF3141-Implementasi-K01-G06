from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_tritunggal_outsource_vendor = fields.Boolean(string='Vendor Outsource Tritunggal')
