# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models

from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job
from datetime import datetime


class PickingListener(Component):
    _name = 'picking.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['stock.picking']

    def on_record_create(self, record, fields=None):
        picking = record
        if picking.partner_id.commercial_partner_id.web \
                and picking.partner_id.commercial_partner_id.active \
                and picking.picking_type_id.code == 'outgoing' \
                and not picking.not_sync \
                and picking.company_id.id == 1:
            record.with_delay(priority=1, eta=60).export_picking()

    def on_record_write(self, record, fields=None):
        picking = record
        up_fields = ["date_done", "move_type", "carrier_name", "carrier_tracking_ref",
                     "state", "not_sync", "company_id", "partner_id"]
        model_name = 'stock.picking'
        if picking.partner_id.commercial_partner_id.web \
                and picking.partner_id.commercial_partner_id.active \
                and picking.picking_type_id.code == 'outgoing' \
                and not picking.not_sync \
                and picking.company_id.id == 1:
            if 'name' in fields or 'partner_id' in fields or \
                    ('not_sync' in fields and not record.not_sync):
                record.with_delay(priority=1, eta=60).export_picking()
                picking_products = self.env['stock.move'].search([('picking_id', '=', picking.id)])
                for product in picking_products:
                    product.with_delay(priority=1, eta=120).export_pickingproduct()
            elif 'state' in fields and record.state == 'cancel' \
                    or 'not_sync' in fields and record.not_sync \
                    or 'company_id' in fields and record.company_id != 1:
                picking_products = self.env['stock.move'].search([('picking_id', '=', picking.id)])
                for product in picking_products:
                    product.with_delay(priority=1, eta=120).unlink_pickingproduct()
                record.with_delay(priority=5, eta=120).unlink_picking()
            else:
                for field in up_fields:
                    if field in fields:
                        record.with_delay(priority=2, eta=120).update_picking(fields=fields)
                        break
        else:
            job = self.env['queue.job'].sudo().search([('func_string', 'like', '%, ' + str(picking.id) + ')%'),
                                                       ('model_name', '=', model_name)], order='date_created desc',
                                                      limit=1)
            if job and 'unlink' not in job.name:
                record.with_delay(priority=5, eta=120).unlink_picking()

    def on_record_unlink(self, record):
        picking = record
        if picking.partner_id.commercial_partner_id.web \
                and picking.partner_id.commercial_partner_id.active \
                and picking.picking_type_id.code == 'outgoing' \
                and not picking.not_sync \
                and picking.company_id.id == 1:
            picking_products = self.env['stock.move'].search([('picking_id', '=', picking.id)])
            for product in picking_products:
                product.with_delay(priority=1, eta=120).unlink_pickingproduct()
            record.with_delay(priority=5, eta=120).unlink_picking()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_picking(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_picking(self, fields):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_picking(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True

    def button_validate(self):
        if self.claim_id:
            if self.picking_type_code == 'incoming':
                field = 'date_in'
            else:
                field = 'date_out'
            products = [x.product_id.id for x in self.item_ids]
            for claim_line in self.claim_id.claim_line_ids:
                if claim_line.product_id.id in products:
                    claim_line[field] = datetime.now()
        return super().button_validate()


class StockMoveListener(Component):
    _name = 'stock.move.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['stock.move']

    def on_record_create(self, record, fields=None):
        for move_line in record:
            if move_line.picking_id.partner_id.commercial_partner_id.web \
                    and move_line.picking_id.partner_id.commercial_partner_id.active \
                    and move_line.picking_id.picking_type_id.code == 'outgoing' \
                    and not move_line.picking_id.not_sync \
                    and move_line.picking_id.company_id.id == 1:
                record.with_delay(priority=1, eta=180).export_pickingproduct()

    def on_record_write(self, record, fields=None):
        up_fields = ["parent_id", "product_uom_qty", "product_id", "picking_id"]
        for move_line in record:
            if move_line.picking_id.partner_id.commercial_partner_id.web \
                    and move_line.picking_id.partner_id.commercial_partner_id.active \
                    and move_line.picking_id.picking_type_id.code == 'outgoing'\
                    and not move_line.picking_id.not_sync \
                    and move_line.picking_id.company_id.id == 1:
                for field in up_fields:
                    if field in fields:
                        record.with_delay(priority=2, eta=240).update_pickingproduct(fields=fields)

    def on_record_unlink(self, record):
        for move_line in record:
            if move_line.picking_id.partner_id.commercial_partner_id.web \
                    and move_line.picking_id.partner_id.commercial_partner_id.active \
                    and move_line.picking_id.picking_type_id.code == 'outgoing' \
                    and not move_line.picking_id.not_sync \
                    and move_line.picking_id.company_id.id == 1:
                record.with_delay(priority=5, eta=240).unlink_pickingproduct()

    def on_stock_move_change(self, record):
        if record.product_id.show_stock_outside:
            record.product_id.with_delay(priority=2, eta=30).update_product()
        #TODO: Migrar
        # ~ is_pack = session.env['product.pack.line'].search([('product_id', '=', move.product_id.id)])
        # ~ for pack in is_pack:
            # ~ update_product.delay(session, "product.product", pack.parent_product_id.id, priority=2, eta=30)


class StockMove(models.Model):
    _inherit = 'stock.move'

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_pickingproduct(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_pickingproduct(self, fields):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_pickingproduct(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True

    # TODO: Debería ser al asignar un producto, al cancelarlo, al finalizarlo y al eliminar la reserve
    @api.multi
    def write(self, vals):
        res = super(StockMove, self).write(vals)
        picking_done = []
        for move in self:
            if vals.get('picking_id', False) or (vals.get('state', False) and move.picking_id):
                vals_picking = {}
                if vals.get('state', False):
                    vals_picking = {'state': vals['state']}
                else:
                    vals_picking = {'state': move.picking_id.state}
                if move.picking_id.id not in picking_done:
                    self._event('on_record_write').notify(self, fields=vals_picking.keys())
                    picking_done.append(move.picking_id.id)

            if vals.get('state', False) and vals["state"] != "draft":
                self._event('on_stock_move_change').notify(move)
        return res
