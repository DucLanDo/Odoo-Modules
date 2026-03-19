from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AlphaTimesheetEntry(models.Model):
    _name = "alpha.timesheet.entry"
    _description = "Task Planner Entry"
    _order = "date desc, time_from desc"

    display_ticket_id = fields.Char(
        string="Ticket ID",
        compute="_compute_display_ticket_id",
        store=False,
    )

    name = fields.Text(string="Description", required=True)

    description_first_line = fields.Char(
        string="Description",
        compute="_compute_description_first_line",
        store=True,
    )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        domain=[("is_company", "=", True)],
    )

    partner_street = fields.Char(
        string="Street",
        related="partner_id.street",
        readonly=True,
    )
    partner_zip = fields.Char(
        string="ZIP",
        related="partner_id.zip",
        readonly=True,
    )
    partner_city = fields.Char(
        string="City",
        related="partner_id.city",
        readonly=True,
    )
    partner_email = fields.Char(
        string="E-Mail",
        related="partner_id.email",
        readonly=True,
    )
    partner_phone = fields.Char(
        string="Phone",
        related="partner_id.phone",
        readonly=True,
    )

    employee_user_id = fields.Many2one(
        "res.users",
        string="Created By",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )

    status = fields.Selection(
        [
            ("todo", "To Do"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="todo",
        required=True,
    )

    time_from = fields.Float(
        string="Time From",
        required=True,
        help="Example: 08:30",
    )

    time_to = fields.Float(
        string="Time To",
        required=True,
        help="Example: 16:30",
    )

    time_from_display = fields.Char(
        string="Time From",
        compute="_compute_time_display",
        store=False,
    )

    time_to_display = fields.Char(
        string="Time To",
        compute="_compute_time_display",
        store=False,
    )

    duration_minutes = fields.Integer(
        string="Minutes",
        compute="_compute_duration_minutes",
        store=True,
        readonly=True,
    )

    source_entry_id = fields.Many2one(
        "alpha.timesheet.entry",
        string="Continued From",
        readonly=True,
    )

    continued_entry_ids = fields.One2many(
        "alpha.timesheet.entry",
        "source_entry_id",
        string="Direct Continued Entries",
        readonly=True,
    )

    chain_entry_ids = fields.Many2many(
        "alpha.timesheet.entry",
        compute="_compute_chain_entry_ids",
        string="All Related Entries",
        readonly=True,
    )

    total_chain_minutes = fields.Integer(
        string="Total Minutes (All Related Entries)",
        compute="_compute_total_chain_minutes",
        readonly=True,
    )

    def _compute_display_ticket_id(self):
        for rec in self:
            rec.display_ticket_id = f"T-{rec.id}" if rec.id else ""

    @api.depends("name")
    def _compute_description_first_line(self):
        for rec in self:
            if rec.name:
                rec.description_first_line = rec.name.splitlines()[0]
            else:
                rec.description_first_line = ""

    @api.depends("time_from", "time_to")
    def _compute_time_display(self):
        for rec in self:
            rec.time_from_display = rec._float_to_hhmm(rec.time_from)
            rec.time_to_display = rec._float_to_hhmm(rec.time_to)

    @api.depends("time_from", "time_to")
    def _compute_duration_minutes(self):
        for rec in self:
            if rec.time_from is not False and rec.time_to is not False and rec.time_to >= rec.time_from:
                rec.duration_minutes = int(round((rec.time_to - rec.time_from) * 60))
            else:
                rec.duration_minutes = 0

    @api.depends(
        "source_entry_id",
        "source_entry_id.source_entry_id",
        "continued_entry_ids",
        "continued_entry_ids.source_entry_id",
        "continued_entry_ids.continued_entry_ids",
    )
    def _compute_chain_entry_ids(self):
        for rec in self:
            chain = rec._get_full_chain()
            rec.chain_entry_ids = [(6, 0, chain.ids)]

    @api.depends(
        "duration_minutes",
        "source_entry_id",
        "source_entry_id.duration_minutes",
        "continued_entry_ids",
        "continued_entry_ids.duration_minutes",
        "continued_entry_ids.continued_entry_ids",
    )
    def _compute_total_chain_minutes(self):
        for rec in self:
            chain = rec._get_full_chain()
            rec.total_chain_minutes = sum(chain.mapped("duration_minutes"))

    @api.constrains("time_from", "time_to")
    def _check_times(self):
        for rec in self:
            if rec.time_to < rec.time_from:
                raise ValidationError("Time To must be later than Time From.")

    def _float_to_hhmm(self, value):
        if value is False:
            return ""
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        return f"{hours:02d}:{minutes:02d}"

    def _get_root_entry(self):
        self.ensure_one()
        current = self
        while current.source_entry_id:
            current = current.source_entry_id
        return current

    def _get_descendants_from_root(self, root):
        self.ensure_one()
        entries = self.env["alpha.timesheet.entry"]
        stack = [root.id]
        visited_ids = set()

        while stack:
            entry_id = stack.pop()
            if entry_id in visited_ids:
                continue

            visited_ids.add(entry_id)
            entry = self.env["alpha.timesheet.entry"].browse(entry_id)
            entries |= entry

            child_ids = entry.continued_entry_ids.ids
            for child_id in child_ids:
                if child_id not in visited_ids:
                    stack.append(child_id)

        return entries.sorted(key=lambda r: (r.date or fields.Date.today(), r.time_from or 0.0, r.id))

    def _get_full_chain(self):
        self.ensure_one()
        root = self._get_root_entry()
        return self._get_descendants_from_root(root)

    def action_open_continue_work_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Continue Work",
            "res_model": "alpha.timesheet.continue.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_entry_id": self.id,
                "default_date": fields.Date.context_today(self),
                "default_time_from": self.time_to or 0.0,
                "default_time_to": self.time_to or 0.0,
            },
        }