# Copyright 2020 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    role_ids = fields.Many2many(
        comodel_name="res.role",
        relation="res_role_menu_rel",
        column1="menu_id",
        column2="role_id",
        string="Roles",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not self.env.context.get("role_policy_init") and "groups_id" in vals:
                del vals["groups_id"]
            if "role_ids" in vals:
                roles = self.env["res.role"].browse(vals["role_ids"][0][2])
                vals["groups_id"] = [(6, 0, [x.id for x in roles.mapped("group_id")])]
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get("role_policy_init") and "groups_id" in vals:
            del vals["groups_id"]
        res = super().write(vals)
        if "role_ids" in vals:
            for menu in self:
                menu.groups_id = menu.role_ids.mapped("group_id")
        return res

    @api.model
    def _visible_menu_ids(self, debug=False):
        """
        Hide all menus without the role_group(s) or the user.
        """
        visible_ids = super()._visible_menu_ids(debug=debug)
        admin = self.env.ref("base.user_admin")
        root = self.env.ref("base.user_root")
        if self.env.user not in (admin, root):
            user_roles = self.env.user.role_ids
            user_groups = user_roles.mapped("group_id")
            menus = self.browse()
            for menu in self.browse(visible_ids):
                for group in menu.groups_id:
                    if group in user_groups:
                        menus |= menu
                        continue

            # remove menus without action menu
            action_menus = menus.filtered(lambda m: m.action and m.action.exists())
            # folder_menus = menus - action_menus
            filtered_ids = []

            def get_parent_ids(menu, menu_ids):
                parent = menu.parent_id
                if parent:
                    if parent in menus:
                        menu_ids.append(parent.id)
                        return get_parent_ids(parent, menu_ids)
                    else:
                        return []
                else:
                    return menu_ids

            for menu in action_menus:
                filtered_ids += get_parent_ids(menu, [menu.id])

            visible_ids = set(filtered_ids)
        return visible_ids
