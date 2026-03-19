{
    "name": "Task Planner",
    "version": "19.0.1.0.0",
    "summary": "Custom task planner for employees",
    "category": "Services",
    "author": "alphaIT",
    "license": "LGPL-3",
    "depends": ["base", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "security/alpha_timesheet_rules.xml",
        "views/alpha_timesheet_views.xml",
        "views/alpha_timesheet_menus.xml",
        "views/continue_work_wizard_views.xml",
    ],
    "installable": True,
    "application": True,
}