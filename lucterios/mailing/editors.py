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
from lucterios.framework.xfercomponents import XferCompGrid
from lucterios.mailing.functions import will_mail_send
from lucterios.documents.views import DocumentShow
from lucterios.framework.tools import FORMTYPE_MODAL, CLOSE_NO, SELECT_SINGLE,\
    SELECT_NONE, SELECT_MULTI
from lucterios.framework.xferadvance import TITLE_EDIT
from lucterios.mailing.views_message import MessageRemoveDoc, MessageInsertDoc


class MessageEditor(LucteriosEditor):

    def edit(self, xfer):
        obj_body = xfer.get_components('body')
        obj_body.with_hypertext = True
        obj_body.set_size(500, 600)
        return LucteriosEditor.edit(self, xfer)

    def show(self, xfer):
        obj_body = xfer.get_components('body')
        obj_body.value = "{[div style='border:1px solid black;background-color:#EEE;padding:5px;']}%s{[div]}" % obj_body.value

        xfer.move_components('body', 0, 2)
        obj_recipients = xfer.get_components('recipients')
        new_recipients = XferCompGrid('recipient_list')
        new_recipients.tab = obj_recipients.tab
        new_recipients.set_location(obj_recipients.col, obj_recipients.row, obj_recipients.colspan)
        new_recipients.add_header("model", _('model'))
        new_recipients.add_header("filter", _('filter'))
        compid = 0
        for model_title, filter_desc in self.item.recipients_description:
            new_recipients.set_value(compid, "model", model_title)
            new_recipients.set_value(compid, "filter", filter_desc)
            compid += 1
        if compid == 0:
            xfer.remove_component('contact_nb')
        if not will_mail_send() or (len(self.item.get_contacts(False)) == 0):
            xfer.remove_component('contact_noemail')
        xfer.remove_component('recipients')
        new_recipients.add_action_notified(xfer, 'recipient_list')
        xfer.tab = new_recipients.tab
        xfer.add_component(new_recipients)

        old_documents = xfer.get_components('attachments')
        xfer.remove_component('attachments')
        if xfer.item.is_dynamic:
            xfer.remove_component('__tab_3')
            xfer.remove_component('doc_in_link')
            xfer.remove_component('empty')
        else:
            new_documents = XferCompGrid('attachments')
            new_documents.tab = old_documents.tab
            new_documents.set_location(old_documents.col, old_documents.row, old_documents.colspan)
            new_documents.set_model(self.item.attachments.all(), ["name", "description", "date_modification"], xfer)
            new_documents.add_action(xfer.request, DocumentShow.get_action(TITLE_EDIT, "images/show.png"),
                                     modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_SINGLE)
            if self.item.status == 0:
                new_documents.add_action(xfer.request, MessageRemoveDoc.get_action(_("Remove"), "images/delete.png"),
                                         modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_MULTI)
                new_documents.add_action(xfer.request, MessageInsertDoc.get_action(_("Insert"), "images/add.png"),
                                         modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_NONE)
            xfer.tab = new_documents.tab
            xfer.add_component(new_documents)
        contact_nb = xfer.get_components('contact_nb')
        if (contact_nb is not None) and (self.item.nb_total > 0):
            xfer.tab = contact_nb.tab
            xfer.fill_from_model(contact_nb.col, contact_nb.row + 1, True, [((_('statistic'), 'statistic'),)])
        return LucteriosEditor.show(self, xfer)
