from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)
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
    version_name = fields.Char(string='Versión Nombre', compute='_compute_version_name')
    version_number = fields.Char(string='Versión')
    
    # Copia de todos los campos relevantes del PO
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
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

    requisition_id = fields.Many2one('purchase.requisition',string="Requirimiento")
    
    facturacion = fields.Many2one('x_facturacion_de_obra',string="Facturación")
    logistica = fields.Boolean('Logística')
    validez_oferta = fields.Datetime('Validez de oferta')
    
    @api.depends('change_date')
    def _compute_version_name(self):
        for record in self:
            record.version_name = f"Versión {record.version_number}"

class PurchaseOrderHistoryLine(models.Model):
    _name = 'purchase.order.history.line'
    _description = 'Líneas históricas de órdenes de compra'
    
    history_id = fields.Many2one('purchase.order.history', string='Historial', ondelete='cascade')
    currency_id = fields.Many2one(related='history_id.currency_id', store=True, string='Currency', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto')
    product_qty = fields.Float(string='Cantidad')
    price_unit = fields.Float(string='Precio unitario')
    taxes_id = fields.Many2many('account.tax', string='Taxes', context={'active_test': False})
    discount = fields.Float(string="Descuento (%)")
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Float(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)
    discount = fields.Float()
    # Copia todos los campos necesarios de purchase.order.line

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = next(iter(tax_results['totals'].values()))
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.history_id.partner_id,
            currency=self.history_id.original_order_id.currency_id,
            product=self.product_id,
            taxes=self.taxes_id,
            price_unit=self.price_unit,
            quantity=self.product_qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    history_ids = fields.One2many('purchase.order.history', 'original_order_id', string='Historial de versiones')

    def get_version_number(self):
        for record in self:
            if record.state != 'purchase':
                # Convertir a float primero
                version_float = float(record.version)
                # Separar parte entera y decimal
                version_int = int(version_float)
                decimal_part = version_float - version_int
                
                # Calcular nuevo decimal
                new_decimal = decimal_part + 0.1
                # Redondear para evitar problemas de precisión flotante
                new_version = round(version_int + new_decimal, 2)
                
                _logger.info(f"{version_int},{decimal_part},{new_decimal},{new_version}")
                
                # Manejar el caso cuando decimal llega a 1.0
                if new_version >= version_int + 1.0:
                    new_version = round(version_int + 0.9 + (new_decimal - 1.0), 2)
                    
                return new_version
            else:
                # Para purchase, incremento entero normal
                return float(record.version) + 1
    
    def write(self, vals):
        # Crear snapshot antes de guardar cambios
        for record in self:
            # Prepara los valores para el histórico
            history_vals = {
                'original_order_id': record.id,
                'partner_id': record.partner_id.id,
                'currency_id':record.currency_id.id,
                'date_order': record.date_order,
                'state': record.state,
                'requisition_id': record.requisition_id.id,
                'facturacion':record.x_studio_facturacin.id,
                'logistica':record.x_studio_logstica,
                'validez_oferta':record.validez_oferta,
                'version_number': record.version
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
                    'taxes_id':line.taxes_id.ids,
                    #'price_subtotal':line.price_subtotal,
                    # Copia todos los campos necesarios de la línea
                })
            vals['version'] = str(self.get_version_number())
            _logger.info(self.get_version_number())
        return super().write(vals)