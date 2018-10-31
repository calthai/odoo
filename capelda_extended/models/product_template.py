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

    # is_check_avilable = fields.Boolean(string='Check Avilable', default=True)
    text_remark = fields.Text(string="Location/QTY", compute='_compute_product_template_availability', copy=False)
    sequence_id = fields.Many2one('ir.sequence', string="Sequence ID.", readonly=True, copy=False)

    @api.multi
    @api.depends('text_remark')
    def _compute_product_template_availability(self):
        # print '_compute_product_template_availability'
        for product in self.env['product.template'].search([]):
            if product.type == 'product':
                quant_ids = self.env['stock.quant'].search(
                    [('product_id', '=', product.id), ('company_id', '=', product.company_id.id)])
                if quant_ids:
                    quant_s = {}
                    i = 0
                    for quant in quant_ids:
                        found = False
                        if i > 0:
                            # print "more than one"
                            for x in xrange(0, i):
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
                            # print 'first time'

                            quant_s[i] = {
                                'location_id': quant.location_id.name,
                                'quantity': quant.quantity,
                            }
                            i += 1

                    quant_s = [value for key, value in quant_s.items()]
                    remark = ''
                    for qs in quant_s:
                        remark += str(qs['location_id'])
                        remark += ' = '
                        remark += str(qs['quantity'])
                        remark += ', '

                    product.text_remark = remark


    # @api.multi
    # @api.depends('text_remark')
    # def _compute_product_template_availability(self):
    #     # print '_compute_product_template_availability'
    #     for product in self.env['product.template'].search([]):
    #         if product.type == 'product':
    #             quant_ids = self.env['stock.quant'].search([('product_id','=',product.id),('company_id','=',product.company_id.id)])
    #             print quant_ids
    #             if quant_ids:
    #                 location_ids = []
    #                 remark = ''
    #                 for quant in quant_ids:
    #                     if quant.location_id.id not in location_ids:
    #                         location_ids.append(quant.location_id.id)
    #                 print location_ids
    #                 if location_ids:
    #                     # print '======1'
    #
    #                     for quant in quant_ids:
    #                         if quant.location_id.id in location_ids:
    #                             # print '===========2'
    #                             quantity = 0.00
    #                             for x in range(0, len(location_ids), 1):
    #                                 # print x
    #                                 if quant.location_id.id == location_ids[x]:
    #                                     # print '======3'
    #                                     # print quant.quantity
    #                                     quantity += quant.quantity
    #
    #                                     remark += quant.location_id.name
    #                                     remark += ' = '
    #                                     remark += str(quantity)
    #                                     remark += ', '
    #
    #                 product.text_remark = remark


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

