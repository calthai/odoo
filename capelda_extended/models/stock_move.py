# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero

class stock_move(models.Model):
    _inherit = 'stock.move'

    new_location_id = fields.Many2one('stock.location',string='New Source Location')
