from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


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
        compute="_compute_duration_minutes",
        store=True,
    )

    attendance_id = fields.Many2one(
        "hr.attendance",
        string="Attendance",
        readonly=True,
        copy=False,
    )

    @api.depends("time_from", "time_to")
    def _compute_duration_minutes(self):
        for record in self:
            if (
                record.time_from is not False
                and record.time_to is not False
                and record.time_to > record.time_from
            ):
                record.duration_minutes = round((record.time_to - record.time_from) * 60)
            else:
                record.duration_minutes = 0

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
                record.attendance_id.write(vals)
            else:
                attendance = self.env["hr.attendance"].create(vals)
                record.attendance_id = attendance.id

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._create_or_update_attendance()
        return record

    def write(self, vals):
        res = super().write(vals)
        self._create_or_update_attendance()
        return res