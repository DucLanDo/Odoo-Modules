from odoo import api, fields, models


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    time_off_type_display = fields.Char(
        string="Type",
        compute="_compute_time_off_type_display",
    )

    @api.depends("holiday_id", "holiday_id.holiday_status_id", "name")
    def _compute_time_off_type_display(self):
        for record in self:
            if record.holiday_id and record.holiday_id.holiday_status_id:
                record.time_off_type_display = record.holiday_id.holiday_status_id.name or "Time Off"
            else:
                record.time_off_type_display = "Holiday"