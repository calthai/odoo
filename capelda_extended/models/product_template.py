# -*- coding: utf-8 -*-

import time
import math

from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _


class product_template(models.Model):
    _inherit = 'product.template'

    # # is_check_avilable = fields.Boolean(string='Check Avilable', default=True)
    # # text_remark = fields.Text(string="Location/QTY",compute='_compute_product_template_availability')
    # text_remark = fields.Text(string="Location/QTY")
    stock_info_text = fields.Text(string='Stock Info',compute='_get_product_template_availability')
    sequence_id = fields.Many2one('ir.sequence', string="Sequence ID.", readonly=True, copy=False)




    @api.multi
    def button_gen_sequence_all(self):
        for product in self:
            product.button_gen_sequence()


    @api.multi
    def button_gen_sequence(self):
        # print 'button_gen_sequence'
        if self.tracking == 'serial':
            if self.default_code:
                if not self.sequence_id:
                    sequence_val = {
                        'name': self.default_code,
                        'code': self.default_code,
                        'prefix': 'Y%(y)s%(month)s',
                        'padding': 4,
                    }
                    sequence_id = self.env['ir.sequence'].create(sequence_val)
                    self.sequence_id = sequence_id
                # else:
                #     raise UserError(_('Sequence is button gen.'))


    def _get_product_template_availability(self):
        for product in self:
            if product.type == 'product':
                product_id = self.env['product.product'].sudo().search([('product_tmpl_id', '=', product.id)])
                quant_ids =self.env['stock.quant'].search(
                                    [('product_id', '=', product_id[0].id), ('company_id', '=', product_id[0].company_id.id)])

                print(quant_ids)
                if quant_ids:
                    quant_s = {}
                    i = 0
                    for quant in quant_ids:
                        found = False
                        if i > 0:
                            print("more than one")
                            for x in range(0, i):
                                # first time
                                # print quant.location_id.id
                                # print quant_s[x]['location_id']
                                if quant.location_id.name == quant_s[x]['location_id']:
                                    found = True
                                    quant_s[x]['quantity'] += quant.quantity
                                    break

                            if not found:
                                # print "not found same product"
                                quant_s[i] = {
                                    'location_id': quant.location_id.name,
                                    'quantity': quant.quantity,
                                }
                                i += 1
                        else:
                            print('first time')

                            quant_s[i] = {
                                'location_id': quant.location_id.name,
                                'quantity': quant.quantity,
                            }
                            i += 1

                    quant_s = [value for key, value in quant_s.items()]
                    remark = ''
                    # print(quant_s)
                    for qs in quant_s:
                        remark += str(qs['location_id'])
                        remark += ' = '
                        remark += str(qs['quantity'])
                        remark += ', '

                    # print (remark)
                    product.stock_info_text = remark
