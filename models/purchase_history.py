from odoo import models, fields, api

class PurchaseOrderHistory(models.Model):
    _name = 'purchase.order.history'
    _description = 'Snapshot histórico de órdenes de compra'
    _rec_name = 'version_name'
    _order = 'change_date desc'
    
    # Referencia al PO original
    original_order_id = fields.Many2one('purchase.order', string='Orden original', required=True, ondelete='cascade')
    
    # Metadatos del cambio
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self: self.env.user)
    change_date = fields.Datetime(string='Fecha de cambio', default=fields.Datetime.now)
    version_name = fields.Char(string='Versión', compute='_compute_version_name')
    
    # Copia de todos los campos relevantes del PO
    partner_id = fields.Many2one('res.partner', string='Proveedor')
    order_line = fields.One2many('purchase.order.history.line', 'history_id', string='Líneas de orden')
    date_order = fields.Datetime(string='Fecha de orden')
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Estado')
    # Agrega aquí todos los demás campos que necesites copiar
    
    @api.depends('change_date')
    def _compute_version_name(self):
        for record in self:
            record.version_name = f"Versión del {record.change_date}"

class PurchaseOrderHistoryLine(models.Model):
    _name = 'purchase.order.history.line'
    _description = 'Líneas históricas de órdenes de compra'
    
    history_id = fields.Many2one('purchase.order.history', string='Historial', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Producto')
    product_qty = fields.Float(string='Cantidad')
    price_unit = fields.Float(string='Precio unitario')
    # Copia todos los campos necesarios de purchase.order.line

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    history_ids = fields.One2many('purchase.order.history', 'original_order_id', string='Historial de versiones')
    
    def write(self, vals):
        # Crear snapshot antes de guardar cambios
        for record in self:
            # Prepara los valores para el histórico
            history_vals = {
                'original_order_id': record.id,
                'partner_id': record.partner_id.id,
                'date_order': record.date_order,
                'state': record.state,
                # Copia todos los campos necesarios
            }
            
            # Crea el registro histórico
            history = self.env['purchase.order.history'].create(history_vals)
            
            # Copia las líneas del pedido
            for line in record.order_line:
                self.env['purchase.order.history.line'].create({
                    'history_id': history.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    # Copia todos los campos necesarios de la línea
                })
        
        return super().write(vals)