# -*- coding: utf-8 -*-
from atom import data
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    is_selected = fields.Boolean(string='Is Selected', default=False)

    @api.multi
    def gen_lot(self):
        # print "GEN LOT"
        if self.picking_type_code == 'incoming':
            # print "INCOMMING"
            for product in self.move_lines:
                # print '=========1'
                if product.show_details_visible:
                    # print '=========2'
                    qty_done = product.product_uom_qty
                    product.move_line_ids.unlink()

                    for x in range(0, int(qty_done), 1):
                        # print '====2222'
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
                            'qty_done': 1,
                            'lot_id': lot_id.id,
                            'lot_name': lot_id.name,
                        }
                        # print '==================='
                        # print val
                        self.env['stock.move.line'].create(val)


    @api.multi
    def button_validate(self):
        # print 'button_validate=====1'
        self.ensure_one()
        if not self.move_lines and not self.move_line_ids:
            raise UserError(_('Please add some lines to move'))

        # If no lots when needed, raise error
        picking_type = self.picking_type_id
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # for move_line in self.move_line_ids:
        #     print move_line.qty_done
        #     print move_line.product_qty
        #     print move_line.product_id.name

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
        return super(stock_picking, self).button_validate()

    @api.multi
    def action_copy_receive(self):
        if self.is_selected == False:
            picking_obj = self.env['stock.picking']

            picking_type_ids = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

            state = 'draft'
            location_id = self.location_dest_id.id
            location_dest_id = self.location_dest_id.id
            picking_type_id = picking_type_ids.id

            picking_obj = picking_obj.create({
                # 'name': self.env['ir.sequence'].next_by_code('stock.picking') or '/',
                'name': picking_type_ids.sequence_id.next_by_id(),
                'state': state,
                'picking_type_code': 'internal',
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'picking_type_id': picking_type_id,
            })

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
                    'location_dest_id': new_location_id,
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
                    'name': picking_type_ids.sequence_id.next_by_id(),
                    'picking_id': move_line.picking_id.id,
                    'product_id': move_line.product_id.id,
                    'location_id': move_line.location_dest_id.id,
                    'location_dest_id': move_line.location_dest_id.id,
                    'lot_id': move_line.lot_id.id,
                    'lot_name': move_line.lot_id.name,
                    'qty_done': move_line.qty_done,
                    'product_uom_id': move_line.product_uom_id.id,
                    # 'lots_visible': True,
                    'has_tracking': True,
                }

                picking_obj.write({'move_line_ids': [(0, 0, vals)]})

            picking_obj.action_confirm()
            # picking_obj.action_assign()

        else:
            raise UserError(_('You have already pressed this button.'))

        self.is_selected = True

    @api.model
    def create(self, vals):
        # print 'create=========1'
        # print vals.get('move_lines')
        if vals.get('move_lines'):
            # print self.move_lines
            location_dest_ids = []
            for move in vals['move_lines']:
                # print '========1'
                if len(move) == 3:
                    location_dest_ids.append(move[2]['location_dest_id'])
        res = super(stock_picking, self).create(vals)
        i = 0
        for move in res.move_lines:
            move.location_dest_id = location_dest_ids[i]
            i = i+1
        return res


