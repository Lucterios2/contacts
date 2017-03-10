# -*- coding: utf-8 -*-
'''
Describe database model for Django

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2015 sd-libre.fr
@license: This file is part of Lucterios.

Lucterios is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Lucterios is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Lucterios.  If not, see <http://www.gnu.org/licenses/>.
'''

from __future__ import unicode_literals

from django.utils.translation import ugettext as _

from lucterios.framework.editors import LucteriosEditor
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompGrid
from lucterios.framework.tools import ActionsManage, SELECT_NONE, FORMTYPE_MODAL, SELECT_SINGLE


class MessageEditor(LucteriosEditor):

    def edit(self, xfer):
        obj_body = xfer.get_components('body')
        obj_body.with_hypertext = True
        obj_body.set_size(500, 600)
        return LucteriosEditor.edit(self, xfer)

    def show(self, xfer):
        xfer.move_components('lbl_body', 0, 2)
        xfer.move_components('body', 0, 2)
        obj_recipients = xfer.get_components('recipients')
        new_recipients = XferCompGrid('recipient_list')
        new_recipients.set_location(obj_recipients.col, obj_recipients.row, obj_recipients.colspan)
        new_recipients.add_header("model", _('model'))
        new_recipients.add_header("filter", _('filter'))
        compid = 0
        for model_title, filter_desc in self.item.recipients_description:
            new_recipients.set_value(compid, "model", model_title)
            new_recipients.set_value(compid, "filter", filter_desc)
            compid += 1
        if compid > 0:
            nb_contact = len(self.item.get_contacts())
            contact_nb = XferCompLabelForm('contact_nb')
            contact_nb.set_location(obj_recipients.col, obj_recipients.row + 1, obj_recipients.colspan)
            contact_nb.set_value(_("Message defined for %d contacts") % nb_contact)
            xfer.add_component(contact_nb)
        lbl = XferCompLabelForm('sep_body')
        lbl.set_location(obj_recipients.col - 1, obj_recipients.row + 2, 4)
        lbl.set_value("{[hr/]}")
        xfer.add_component(lbl)
        xfer.remove_component('recipients')
        new_recipients.add_action_notified(xfer, 'recipient_list')
        xfer.add_component(new_recipients)
        return LucteriosEditor.show(self, xfer)
