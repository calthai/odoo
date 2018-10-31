# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class stock_location(models.Model):
    _inherit = 'stock.location'

    is_check_avilable = fields.Boolean(string='Check Avilable', default=True)

