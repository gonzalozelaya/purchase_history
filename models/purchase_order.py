from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    version = fields.Char(string='Versión', readonly=True)

    def button_approve(self, force=False):
        res = super(PurchaseOrder,self).button_approve()
        self.version = 1
        return {}

    