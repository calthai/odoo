# -*- coding: utf-8 -*-
# from atom import data
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    def _get_default_partner(self):
        # print ('_get_default_partner')
        # print (self.env.context)
        if 'active_id' in self.env.context:
            picking_type_ids = self.env['stock.picking.type'].browse(self.env.context['active_id'])
            for type in picking_type_ids:
                # print (type.code)
                if type.code == 'incoming':
                    default_partner_id = self.env['res.partner'].search([('name','=','Calpeda Italy')], limit=1)
                    # print (default_partner_id.name)
                    return default_partner_id.id
                elif type.code == 'outgoing':
                    default_partner_id = self.env['res.partner'].search([('name','=','Partner')], limit=1)
                    # print (default_partner_id.name)
                    return default_partner_id.id

    is_selected = fields.Boolean(string='Is Selected', default=False)
    is_checked = fields.Boolean(string='Is Checked', default=False)
    is_gen_lot = fields.Boolean(string='Is Gen Lot', default=False, compute='get_is_gen_lot')
    rec_ref_id = fields.Many2one('stock.picking', string='Receipt Ref')
    int_ref_id = fields.Many2one('stock.picking', string='Internal Ref')
    is_put_in_pack = fields.Boolean(string='Is Put in Pack',default=False, compute='get_is_put_in_pack')
    partner_id = fields.Many2one(
        'res.partner', 'Partner',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},  default=_get_default_partner)

    @api.multi
    def _compute_show_check_availability(self):
        print('_compute_show_check_availability====2')
        for picking in self:
            has_moves_to_reserve = any(
                move.state in ('waiting', 'confirmed', 'partially_available') and
                float_compare(move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding)
                for move in picking.move_lines
            )
            # print(has_moves_to_reserve)
            # print(picking.is_checked)
            if picking.is_checked:
                # print('==================1')
                picking.show_check_availability = False
            if picking.picking_type_code == 'incoming':
                if not picking.is_gen_lot and picking.is_put_in_pack:
                    picking.show_check_availability = True
                elif picking.is_gen_lot and not picking.is_put_in_pack:
                    picking.show_check_availability = True
                elif not picking.is_gen_lot and not picking.is_put_in_pack:
                    picking.show_check_availability = True
            else:
                # print('==================2')
                picking.show_check_availability = picking.is_locked and picking.state in (
                'confirmed', 'waiting', 'assigned') and has_moves_to_reserve

    @api.depends('move_line_ids')
    def get_is_put_in_pack(self):
        print ('get_is_put_in_pack')

        for picking in self:
            picking.is_put_in_pack = True
            if picking.move_line_ids and len(picking.move_line_ids):
                i = 0
                for line in picking.move_line_ids:
                    if not line.result_package_id:
                        print ('============1')
                        i += 1
                print (i)
                if i > 0:
                    picking.is_put_in_pack = False
                else:
                    picking.is_put_in_pack = True

    @api.depends('move_lines')
    def get_is_gen_lot(self):
        # self.is_gen_lot = True
        # print (self.is_gen_lot)
        for picking in self:
            picking.is_gen_lot = True
            if picking.move_lines and len(picking.move_lines):
                if len(picking.move_lines) and picking.state in ('draft','done'):
                    picking.show_validate = False
                else:
                    picking.show_validate = True

                i = 0
                for pic in picking.move_lines:
                    if not pic.quantity_done:
                        # print('============1')
                        i += 1
                print(i)
                if i > 0:
                    picking.is_gen_lot = False
                else:
                    picking.is_gen_lot = True

    @api.multi
    def gen_lot(self):
        # print "GEN LOT"
        if self.picking_type_code == 'incoming':
            # print "INCOMMING"
            # if not self.is_gen_lot:
            for product in self.move_lines:
                # print '=========1'
                if not product.quantity_done:
                    # print '=========2'
                    qty_done = product.product_uom_qty
                    product.move_line_ids.unlink()

                    for x in range(0, int(qty_done), 1):
                        # print '====2222'
                        if not product.product_id.sequence_id:
                            product.product_id.product_tmpl_id.button_gen_sequence()
                        lot_name = product.product_id.sequence_id.next_by_id()
                        lot_val = {
                            'product_id': product.product_id.id,
                            'name': lot_name,
                            'product_qty': 1,
                        }
                        lot_id = self.env['stock.production.lot'].search(
                            [('product_id', '=', product.product_id.id), ('name', '=', lot_name)], limit=1)
                        if not lot_id:
                            lot_id = self.env['stock.production.lot'].create(lot_val)

                        val = {
                            'picking_id': self.id,
                            'move_id': product.id,
                            'product_id': product.product_id.id,
                            'product_uom_id': product.product_uom.id,
                            'location_id': product.location_id.id,
                            'location_dest_id': product.location_dest_id.id,
                            # 'product_qty': 1,
                            'product_uom_qty': 1,
                            'qty_done': 1,
                            'lot_id': lot_id.id,
                            'lot_name': lot_id.name,
                        }
                        # print '==================='
                        print (val)
                        self.env['stock.move.line'].create(val)

            # self.is_put_in_pack = True
            self.action_assign()
            # else:
            #     raise UserError(_('You have already pressed this button Gen Serial.'))
            #
            # self.is_gen_lot = True

    @api.multi
    def button_validate(self):
        super(stock_picking, self).button_validate()
        # print 'button_validate=====1'
        self.ensure_one()
        if not self.move_lines and not self.move_line_ids:
            raise UserError(_('Please add some lines to move'))

        ######### add restriction to assign package before validate #########
        ######### 16/12/2018 by Jatupong ##########
        if self.picking_type_code == 'incoming' and self.move_line_ids and not self.move_line_ids[0].result_package_id:
            raise UserError(_('Please assign package first'))
        #########end 16/12/2018 #################

        # If no lots when needed, raise error
        picking_type = self.picking_type_id
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # for move_line in self.move_line_ids:
        #     print move_line.qty_done
        #     print move_line.product_qty
        #     print move_line.product_id.name

        #########add done qty to be 1 if lot_id is assigned
        ######### 16/12/2018 by Jatupong ##########
        if self.picking_type_code != 'incoming':
            for move_line in self.move_line_ids:
                if move_line.lot_id and move_line.product_uom_qty:
                    move_line.qty_done = 1

        #########end 16/12/2018 #################
        no_quantities_done = all(
            float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in self.move_line_ids)
        no_reserved_quantities = all(
            float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in
            self.move_line_ids)


        # print '========================start'
        # print no_quantities_done
        # print no_reserved_quantities
        # print '========================end'
        if no_reserved_quantities and no_quantities_done:
            raise UserError(_(
                'You cannot validate a transfer if you have not processed any quantity. You should rather cancel the transfer.'))

        if picking_type.use_create_lots or picking_type.use_existing_lots:
            # print '================111111'
            lines_to_check = self.move_line_ids
            if not no_quantities_done:
                lines_to_check = lines_to_check.filtered(
                    lambda line: float_compare(line.qty_done, 0,
                                               precision_rounding=line.product_uom_id.rounding)
                )

            for line in lines_to_check:
                product = line.product_id
                if product and product.tracking != 'none':
                    if not line.lot_name and not line.lot_id:
                        raise UserError(_('You need to supply a lot/serial number for %s.') % product.display_name)

                if self.picking_type_code == 'outgoing':
                    # print '**************'
                    if line.lot_id:
                        str_y = line.lot_id.name.split('Y')
                        if not str_y[0]:
                            raise UserError(_("You can be not use Lot start with 'Y' !"))

        if no_quantities_done:
            # print '=====================22222'
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
            # print '===============33333333333'
            view = self.env.ref('stock.view_overprocessed_transfer')
            wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.overprocessed.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        # Check backorder should check for other barcodes
        if self._check_backorder():
            return self.action_generate_backorder_wizard()
        self.action_done()
        return
        # return super(stock_picking, self).button_validate()

    @api.multi
    def action_copy_receive(self):
        if self.is_selected == False:
            picking_obj = self.env['stock.picking']

            picking_type_ids = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

            state = 'draft'
            location_id = self.location_dest_id.id
            location_dest_id = self.location_dest_id.id
            picking_type_id = picking_type_ids.id
            # show_check_availability  = False
            location_dest_id1 = self.env['stock.location'].search([('name','=','WH')], limit=1)

            picking_obj = picking_obj.create({
                # 'name': self.env['ir.sequence'].next_by_code('stock.picking') or '/',
                'name': picking_type_ids.sequence_id.next_by_id(),
                'state': state,
                'picking_type_code': 'internal',
                'location_id': location_id,
                'location_dest_id': location_dest_id1.id,
                'picking_type_id': picking_type_id,
                'is_checked': True,
                'rec_ref_id': self.id,
                # 'show_check_availability': show_check_availability,
            })

            self.write({'int_ref_id': picking_obj.id})
            # print (picking_obj.name)

            # if picking_obj.move_lines:
            #     picking_obj.move_lines.unlink()

            for line in self.move_lines:
                # line.unlink()
                if line.new_location_id:
                    new_location_id = line.new_location_id.id
                else:
                    new_location_id = picking_type_ids.default_location_dest_id.id
                vals = {
                    # 'name': self.env['ir.sequence'].next_by_code('stock.picking') or '/',
                    'name': picking_obj.name,
                    'picking_id': line.picking_id.id,
                    'product_id': line.product_id.id,
                    'location_id': line.location_id.id,
                    'location_dest_id': location_dest_id1.id,
                    'product_uom_qty': line.product_uom_qty,
                    'quantity_done': line.quantity_done,
                    'product_uom': line.product_uom.id,
                        }

                picking_obj.update({'move_lines': [(0, 0, vals)]})

            if picking_obj.move_line_ids:
                picking_obj.move_line_ids.unlink()
            #
            for move_line in self.move_line_ids:
                # move_line.unlink()
                vals = {
                    # 'name': self.env['ir.sequence'].next_by_code('stock.picking') or '/',
                    'name': picking_type_ids.name,
                    'picking_id': move_line.picking_id.id,
                    'product_id': move_line.product_id.id,
                    'location_id': move_line.location_dest_id.id,
                    'location_dest_id': location_dest_id1.id,
                    'lot_id': move_line.lot_id.id,
                    'lot_name': move_line.lot_id.name,
                    'qty_done': move_line.qty_done,
                    'product_uom_id': move_line.product_uom_id.id,
                    'package_id': move_line.result_package_id.id,
                    'result_package_id': move_line.result_package_id.id,
                    # 'lots_visible': True,
                    # 'has_tracking': True,
                }

                picking_obj.write({'move_line_ids': [(0, 0, vals)]})

            picking_obj.action_confirm()
            # picking_obj.action_assign()
            self.is_selected = True
        else:
            raise UserError(_('You have already pressed this button.'))


    @api.model
    def create(self, vals):
        print ('create=========1')
        print (vals.get('move_lines'))

        if vals.get('move_lines'):
            # print self.move_lines
            location_dest_ids = []
            location_ids = []
            for move in vals['move_lines']:
                # print '========1'
                if len(move) == 3:
                    location_dest_ids.append(move[2]['location_dest_id'])
                    location_ids.append(move[2]['location_id'])

                if move[2]['product_uom_qty'] <= 0:
                    raise UserError(_('Initial quantity should more than 0'))

        res = super(stock_picking, self).create(vals)
        i = 0
        for move in res.move_lines:
            move.location_dest_id = location_dest_ids[i]
            move.location_id = location_ids[i]
            i = i+1
        print (res)
        return res

    @api.onchange('move_line_ids','move_line_ids.location_dest_id')
    def _create_function_package(self):
        print ('_create_function_package')
        self.show_validate = False
        self.is_put_in_pack = True
        if self.move_line_ids:
            line_s = {}
            i = 0
            for line in self.move_line_ids:
                if line.auto_set:
                    found = False
                    if i > 0:
                        for x in range(0, i):
                            if line.package_id.id == line_s[x]['package_id']:
                                print ('=========1')
                                found = True
                                line.write({'location_dest_id': line_s[x]['location_dest_id'],
                                            })

                        if not found:
                            print('=========2')
                            line_s[i] = {
                                'package_id': line.package_id.id,
                                'location_dest_id': line.location_dest_id.id,
                            }
                            i += 1
                    else:
                        print('=========3')
                        line_s[i] = {
                            'package_id': line.package_id.id,
                            'location_dest_id': line.location_dest_id.id,
                        }
                        i += 1

            line_s = [value for key, value in line_s.items()]
            print (line_s)



                    # if line.package_id.id not in package_ids:
                    #     package_ids.append(line.package_id.id)
                    #     if package_ids:
                    #         for package in package_ids:
                    #             if package == line.package_id.id:


    def _put_in_pack(self):
        package = False
        for pick in self.filtered(lambda p: p.state not in ('done', 'cancel')):
            operations = pick.move_line_ids.filtered(lambda o: o.qty_done > 0 and not o.result_package_id)
            operation_ids = self.env['stock.move.line']
            if operations:
                package = self.env['stock.quant.package'].create({})
                for operation in operations:
                    if operation.is_gen_put:
                        if float_compare(operation.qty_done, operation.product_uom_qty, precision_rounding=operation.product_uom_id.rounding) >= 0:
                            operation_ids |= operation
                        else:
                            quantity_left_todo = float_round(
                                operation.product_uom_qty - operation.qty_done,
                                precision_rounding=operation.product_uom_id.rounding,
                                rounding_method='UP')
                            done_to_keep = operation.qty_done
                            new_operation = operation.copy(
                                default={'product_uom_qty': 0, 'qty_done': operation.qty_done})
                            operation.write({'product_uom_qty': quantity_left_todo, 'qty_done': 0.0})
                            new_operation.write({'product_uom_qty': done_to_keep})
                            operation_ids |= new_operation

                operation_ids.write({'result_package_id': package.id})
            else:
                raise UserError(_('Please process some quantities to put in the pack first!'))
        return package


