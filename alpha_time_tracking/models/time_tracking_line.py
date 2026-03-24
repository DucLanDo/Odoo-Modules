from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AlphaTimeTrackingLine(models.Model):
    _name = "alpha.time.tracking.line"
    _description = "Time Tracking Line"
    _order = "time_from asc, id asc"

    day_id = fields.Many2one(
        "alpha.time.tracking.day",
        string="Day",
        required=True,
        ondelete="cascade",
    )

    project_id = fields.Many2one(
        "project.project",
        string="Project",
    )

    activity_description = fields.Text(
        string="Activity Description",
    )

    time_from = fields.Float(
        string="From",
        required=True,
    )

    time_to = fields.Float(
        string="To",
        required=True,
    )

    duration_minutes = fields.Integer(
        string="Duration (Minutes)",
        compute="_compute_duration_fields",
        store=True,
    )

    duration_display = fields.Char(
        string="Duration",
        compute="_compute_duration_fields",
        store=True,
    )

    attendance_id = fields.Many2one(
        "hr.attendance",
        string="Attendance",
        readonly=True,
        copy=False,
    )

    @api.depends("time_from", "time_to")
    def _compute_duration_fields(self):
        for record in self:
            if (
                record.time_from is not False
                and record.time_to is not False
                and record.time_to > record.time_from
            ):
                total_minutes = round((record.time_to - record.time_from) * 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60

                record.duration_minutes = total_minutes
                record.duration_display = f"{hours}h {minutes}m"
            else:
                record.duration_minutes = 0
                record.duration_display = "0h 0m"

    @api.constrains("time_from", "time_to")
    def _check_time_range(self):
        for record in self:
            if record.time_to <= record.time_from:
                raise ValidationError("The end time must be later than the start time.")

    @api.constrains("time_from", "time_to", "day_id")
    def _check_overlap(self):
        for record in self:
            siblings = record.day_id.line_ids.filtered(lambda l: l.id != record.id)

            for sibling in siblings:
                overlaps = (
                    record.time_from < sibling.time_to
                    and record.time_to > sibling.time_from
                )
                if overlaps:
                    raise ValidationError(
                        "Working time entries for the same day must not overlap."
                    )

    def _float_to_utc_naive(self, date_value, float_value):
        hours = int(float_value)
        minutes = int(round((float_value - hours) * 60))

        if minutes == 60:
            hours += 1
            minutes = 0

        local_naive = datetime.combine(date_value, datetime.min.time()) + timedelta(
            hours=hours,
            minutes=minutes,
        )

        user_tz_name = self.env.user.tz or "UTC"
        user_tz = ZoneInfo(user_tz_name)

        local_aware = local_naive.replace(tzinfo=user_tz)
        utc_aware = local_aware.astimezone(ZoneInfo("UTC"))

        return utc_aware.replace(tzinfo=None)

    def _create_or_update_attendance(self):
        for record in self:
            if not record.day_id.employee_id or not record.day_id.date:
                continue

            check_in = record._float_to_utc_naive(record.day_id.date, record.time_from)
            check_out = record._float_to_utc_naive(record.day_id.date, record.time_to)

            vals = {
                "employee_id": record.day_id.employee_id.id,
                "check_in": check_in,
                "check_out": check_out,
            }

            if record.attendance_id:
                record.attendance_id.with_context(from_time_tracking_sync=True).write(vals)
            else:
                attendance = self.env["hr.attendance"].with_context(
                    from_time_tracking_sync=True
                ).create(vals)
                record.attendance_id = attendance.id
                attendance.time_tracking_line_id = record.id

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if not self.env.context.get("from_attendance_sync"):
            record._create_or_update_attendance()
        return record

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("from_attendance_sync"):
            self._create_or_update_attendance()
        return res

    def unlink(self):
        if self.env.context.get("from_attendance_sync"):
            return super().unlink()

        attendances = self.mapped("attendance_id")
        res = super().unlink()
        if attendances:
            attendances.with_context(from_time_tracking_sync=True).unlink()
        return res