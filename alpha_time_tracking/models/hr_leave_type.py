from odoo import api, fields, models


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    alpha_dashboard_color = fields.Char(
        string="Dashboard Color",
        compute="_compute_alpha_dashboard_helpers",
    )

    alpha_dashboard_icon_url = fields.Char(
        string="Dashboard Icon URL",
        compute="_compute_alpha_dashboard_helpers",
    )

    def _color_index_to_hex(self, color_index):
        palette = {
            0: "#6c757d",
            1: "#F06050",
            2: "#F4A460",
            3: "#F7CD1F",
            4: "#6CC1ED",
            5: "#814968",
            6: "#EB7E7F",
            7: "#2C8397",
            8: "#475577",
            9: "#D6145F",
            10: "#30C381",
            11: "#9365B8",
        }
        return palette.get(color_index or 0, "#6c757d")

    def _guess_icon_url(self):
        self.ensure_one()

        candidates = [
            "cover_image",
            "cover_image_128",
            "image_128",
            "image_512",
            "image_1920",
            "icon_image",
            "icon",
            "cover_image_id",
            "icon_id",
        ]

        for field_name in candidates:
            if field_name not in self._fields:
                continue

            field = self._fields[field_name]
            value = self[field_name]

            if not value:
                continue

            if field.type == "binary":
                return f"/web/image/{self._name}/{self.id}/{field_name}"

            if field.type == "many2one":
                related = value
                if not related:
                    continue

                related_image_candidates = [
                    "image_128",
                    "image_512",
                    "image_1920",
                    "image",
                ]
                for related_field in related_image_candidates:
                    if related_field in related._fields:
                        return f"/web/image/{related._name}/{related.id}/{related_field}"

        return False

    @api.depends("color")
    def _compute_alpha_dashboard_helpers(self):
        for record in self:
            record.alpha_dashboard_color = record._color_index_to_hex(record.color)
            record.alpha_dashboard_icon_url = record._guess_icon_url()