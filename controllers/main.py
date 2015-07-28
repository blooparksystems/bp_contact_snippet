# -*- coding: utf-8 -*-
##############################################################################
#
# Odoo, an open source suite of business apps
# This module copyright (C) 2015 bloopark systems (<http://bloopark.de>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64
from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.tools.translate import _


class contactus(http.Controller):

    """Contactus class."""

    @http.route(['/page/website.contactus', '/page/contactus'], type='http',
                auth="public", website=True)
    def contact(self, **kwargs):
        """Request contact."""
        values = {}
        for field in ['description', 'partner_name', 'phone', 'contact_name',
                      'email_from', 'name']:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        values.update(kwargs=kwargs.items())
        return request.website.render("website.contactus", values)

    def create_lead(self, request, values, kwargs):
        """Allow to be overrided."""
        cr, context = request.cr, request.context
        return request.registry['crm.lead'].create(
            cr, SUPERUSER_ID, values, context=dict(
                context, mail_create_nosubscribe=True))

    def preRenderThanks(self, values, kwargs):
        """Allow to be overrided."""
        company = request.website.company_id
        return {
            '_values': values,
            '_kwargs': kwargs,
        }

    def get_contactus_response(self, values, kwargs):
        """Get contact."""
        values = self.preRenderThanks(values, kwargs)
        return request.website.render(
            kwargs.get("view_callback",
                       "bp_contact_snippet.contact_snippet_body_thanks"),
            values)

    @http.route(['/contactus_snippet'], type='json', auth="public",
                website=True)
    def contactus(self, name, phone, description):
        """Allow to be overrided."""
        def dict_to_str(title, dictvar):
            ret = "\n\n%s" % title
            for field in dictvar:
                ret += "\n%s" % field
            return ret

        crm_data = {
            'contact_name': name,
            'phone': phone,
            'description': description
        }
        # Only use for behavior, don't stock it
        _TECHNICAL = ['show_info', 'view_from',
                      'view_callback']
        # Allow in description
        _BLACKLIST = ['id', 'create_uid', 'create_date', 'write_uid',
                      'write_date', 'user_id', 'active']
        # Could be improved including required from model
        _REQUIRED = ['name', 'contact_name', 'description']

        # List of file to add to ir_attachment once we have the ID
        post_file = []
        # Info to add after the message
        post_description = []
        values = {}

        values['medium_id'] = request.registry[
            'ir.model.data'].xmlid_to_res_id(
            request.cr, SUPERUSER_ID, 'crm.crm_medium_website')
        values['section_id'] = request.registry[
            'ir.model.data'].xmlid_to_res_id(
            request.cr, SUPERUSER_ID, 'website.salesteam_website_sales')

        for field_name, field_value in crm_data.items():
            if hasattr(field_value, 'filename'):
                post_file.append(field_value)
            elif field_name in request.registry[
                'crm.lead']._fields and field_name not in _BLACKLIST:
                values[field_name] = field_value
            elif field_name not in _TECHNICAL:
                # allow to add some free fields or blacklisted field like ID
                post_description.append("%s: %s" % (field_name, field_value))

        if "name" not in crm_data and values.get(
                "contact_name"):
                # if kwarg.name is empty,
                # it's an error, we cannot copy the contact_name
            values["name"] = values.get("contact_name")
        # fields validation :
        # Check that required field from model crm_lead exists
        error = set(field for field in _REQUIRED if not values.get(field))

        if error:
            values = dict(values, error=error, kwargs=crm_data.items())
            # return request.website.render(kwargs.get(
            # "view_from", "website.contactus"), values)

        # description is required, so it is always already initialized
        if post_description:
            values['description'] += dict_to_str(_("Custom Fields: "),
                                                 post_description)

        if False:
            post_description = []
            environ = request.httprequest.headers.environ
            post_description.append("%s: %s" % ("IP", environ.get(
                "REMOTE_ADDR")))
            post_description.append("%s: %s" % ("USER_AGENT", environ.get(
                "HTTP_USER_AGENT")))
            post_description.append(
                "%s: %s" % ("ACCEPT_LANGUAGE", environ.get(
                    "HTTP_ACCEPT_LANGUAGE")))
            post_description.append("%s: %s" % ("REFERER", environ.get(
                "HTTP_REFERER")))
            values['description'] += dict_to_str(_("Environ Fields: "),
                                                 post_description)

        lead_id = self.create_lead(request, dict(values, user_id=False), {})
        values.update(lead_id=lead_id)
        if lead_id:
            for field_value in post_file:
                attachment_value = {
                    'name': field_value.filename,
                    'res_name': field_value.filename,
                    'res_model': 'crm.lead',
                    'res_id': lead_id,
                    'datas': base64.encodestring(field_value.read()),
                    'datas_fname': field_value.filename,
                }
                request.registry['ir.attachment'].create(
                    request.cr, SUPERUSER_ID, attachment_value,
                    context=request.context)

        if lead_id:
            return {'success': True}
        else:
            return {'success': False}
