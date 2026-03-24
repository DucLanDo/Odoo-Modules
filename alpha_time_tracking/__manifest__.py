{
    "name": "Time Tracking",
    "version": "19.0.1.0.0",
    "summary": "Custom daily time tracking with attendance synchronization",
    "description": """
Custom Time Tracking module
- Daily time entries
- Multiple time blocks per day
- Synchronization with Attendances
""",
    "author": "alphaIT",
    "website": "",
    "category": "Human Resources",
    "license": "LGPL-3",
    "depends": [
        "base",
        "hr",
        "hr_attendance",
        "project",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/time_tracking_day_views.xml",
        "views/time_tracking_dashboard_action.xml",
        "views/time_tracking_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "alpha_time_tracking/static/src/js/time_tracking_dashboard.js",
            "alpha_time_tracking/static/src/xml/time_tracking_dashboard.xml",
            "alpha_time_tracking/static/src/scss/time_tracking_dashboard.scss",
        ],
    },
    "installable": True,
    "application": True,
}