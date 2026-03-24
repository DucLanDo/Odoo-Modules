from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    time_tracking_line_id = fields.Many2one(
        "alpha.time.tracking.line",
        string="Time Tracking Line",
        readonly=True,
        copy=False,
    )

    def _attendance_to_local_date_and_floats(self):
        self.ensure_one()

        if not self.check_in or not self.check_out:
            raise ValidationError("Check in and check out are required.")

        local_check_in = fields.Datetime.context_timestamp(self, self.check_in)
        local_check_out = fields.Datetime.context_timestamp(self, self.check_out)

        if local_check_in.date() != local_check_out.date():
            raise ValidationError(
                "Attendances across multiple days are not supported in Time Tracking yet."
            )

        date_value = local_check_in.date()
        time_from = local_check_in.hour + (local_check_in.minute / 60.0)
        time_to = local_check_out.hour + (local_check_out.minute / 60.0)

        return date_value, time_from, time_to

    def _get_or_create_day(self):
        self.ensure_one()

        if not self.employee_id or not self.employee_id.user_id:
            raise ValidationError(
                "The employee needs to be linked to a user before syncing to Time Tracking."
            )

        date_value, _, _ = self._attendance_to_local_date_and_floats()

        day = self.env["alpha.time.tracking.day"].search(
            [
                ("user_id", "=", self.employee_id.user_id.id),
                ("date", "=", date_value),
            ],
            limit=1,
        )

        if not day:
            day = self.env["alpha.time.tracking.day"].with_context(
                from_attendance_sync=True
            ).create(
                {
                    "user_id": self.employee_id.user_id.id,
                    "date": date_value,
                }
            )

        return day

    def _sync_to_time_tracking(self):
        for attendance in self:
            if not attendance.employee_id or not attendance.employee_id.user_id:
                continue

            if not attendance.check_in or not attendance.check_out:
                continue

            date_value, time_from, time_to = attendance._attendance_to_local_date_and_floats()
            day = attendance._get_or_create_day()

            vals = {
                "day_id": day.id,
                "time_from": time_from,
                "time_to": time_to,
                "attendance_id": attendance.id,
            }

            if attendance.time_tracking_line_id:
                attendance.time_tracking_line_id.with_context(
                    from_attendance_sync=True
                ).write(vals)
            else:
                line = self.env["alpha.time.tracking.line"].with_context(
                    from_attendance_sync=True
                ).create(vals)
                attendance.time_tracking_line_id = line.id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("from_time_tracking_sync"):
            records._sync_to_time_tracking()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("from_time_tracking_sync"):
            self._sync_to_time_tracking()
        return res

    def unlink(self):
        if self.env.context.get("from_time_tracking_sync"):
            return super().unlink()

        linked_lines = self.mapped("time_tracking_line_id")
        res = super().unlink()

        if linked_lines:
            days = linked_lines.mapped("day_id")
            linked_lines.with_context(from_attendance_sync=True).unlink()

            empty_days = days.filtered(lambda d: not d.line_ids)
            if empty_days:
                empty_days.with_context(from_attendance_sync=True).unlink()

        return res