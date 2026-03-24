from odoo import api, fields, models


class AlphaTimeTrackingDay(models.Model):
    _name = "alpha.time.tracking.day"
    _description = "Time Tracking Day"
    _order = "date desc, id desc"
    _rec_name = "date"

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        default=lambda self: self.env.user,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        compute="_compute_employee_id",
        store=True,
    )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )

    line_ids = fields.One2many(
        "alpha.time.tracking.line",
        "day_id",
        string="Working Times",
    )

    total_minutes = fields.Integer(
        string="Total Minutes",
        compute="_compute_totals",
        store=True,
    )

    total_time_display = fields.Char(
        string="Total Time",
        compute="_compute_totals",
        store=True,
    )

    activity_description = fields.Text(
        string="Activities",
    )

    _sql_constraints = [
        (
            "unique_user_date",
            "unique(user_id, date)",
            "Only one time tracking record per user and date is allowed.",
        )
    ]

    # ----------------------------
    # COMPUTE
    # ----------------------------
    @api.depends("user_id")
    def _compute_employee_id(self):
        for record in self:
            employee = self.env["hr.employee"].search(
                [("user_id", "=", record.user_id.id)],
                limit=1,
            )
            record.employee_id = employee

    @api.depends("line_ids.duration_minutes")
    def _compute_totals(self):
        for record in self:
            total_minutes = sum(record.line_ids.mapped("duration_minutes"))
            hours = total_minutes // 60
            minutes = total_minutes % 60

            record.total_minutes = total_minutes
            record.total_time_display = f"{hours:02d}:{minutes:02d}"

    # ----------------------------
    # DISPLAY NAME
    # ----------------------------
    def name_get(self):
        result = []
        for record in self:
            user_name = record.user_id.name or "User"
            label = f"{user_name} - {record.date}" if record.date else user_name
            result.append((record.id, label))
        return result