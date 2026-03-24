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
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/time_tracking_day_views.xml",
        "views/time_tracking_menus.xml",
    ],
    "installable": True,
    "application": True,
}