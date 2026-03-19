from odoo import fields, models
from odoo.exceptions import ValidationError


class AlphaTimesheetContinueWizard(models.TransientModel):
    _name = "alpha.timesheet.continue.wizard"
    _description = "Continue Task Planner Work Wizard"

    entry_id = fields.Many2one(
        "alpha.timesheet.entry",
        string="Original Entry",
        required=True,
        readonly=True,
    )

    date = fields.Date(
        string="New Date",
        required=True,
        default=fields.Date.context_today,
    )

    time_from = fields.Float(
        string="Time From",
        required=True,
    )

    time_to = fields.Float(
        string="Time To",
        required=True,
    )

    def action_continue_work(self):
        self.ensure_one()

        if self.time_to < self.time_from:
            raise ValidationError("Time To must be later than Time From.")

        original = self.entry_id

        new_entry = self.env["alpha.timesheet.entry"].create({
            "name": original.name,
            "date": self.date,
            "partner_id": original.partner_id.id,
            "employee_user_id": self.env.user.id,
            "status": "todo",
            "time_from": self.time_from,
            "time_to": self.time_to,
            "source_entry_id": original.id,
        })

        original.status = "done"

        return {
            "type": "ir.actions.act_window",
            "name": "Task Planner Entry",
            "res_model": "alpha.timesheet.entry",
            "res_id": new_entry.id,
            "view_mode": "form",
            "target": "current",
        }