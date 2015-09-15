# -*- coding: utf-8 -*-
'''
lucterios.contacts package

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
from django.utils.translation import ugettext_lazy as _
from django.apps import apps

from lucterios.contacts.models import AbstractContact
from lucterios.framework.xfersearch import XferSearchEditor
from lucterios.framework.xfercomponents import XferCompSelect, XferCompLabelForm
from lucterios.framework.tools import FORMTYPE_REFRESH, CLOSE_NO, CLOSE_YES, SELECT_SINGLE
from lucterios.CORE.editors import XferSavedCriteriaSearchEditor


class ContactSelection(XferSavedCriteriaSearchEditor):
    icon = "contacts.png"
    model = AbstractContact
    field_id = 'abstractcontact'
    caption = _("Select contact")
    select_class = None
    final_class = None

    def fillresponse(self):
        self.action_list = []
        if self.final_class is not None:
            self.add_action(
                self.final_class.get_action(_('ok'), "images/ok.png"), {})
        model_current = self.getparam('modelname')
        if model_current is None:
            self.model = AbstractContact
        else:
            self.model = apps.get_model(model_current)
        self.field_id = self.model.__name__.lower()
        self.item = self.model()
        XferSearchEditor.fillresponse(self)
        self.remove_component('title')
        lbl = XferCompLabelForm('modelname_lbl')
        lbl.set_value_as_title(_('model'))
        lbl.set_location(1, 0)
        self.add_component(lbl)
        list_of_modal = []
        list_of_modal.append((AbstractContact.get_long_name(
        ), AbstractContact._meta.verbose_name.title()))
        for sub_class in AbstractContact.__subclasses__():
            list_of_modal.append((sub_class.get_long_name(), sub_class._meta.verbose_name.title(
            )))
        selected_model = XferCompSelect('modelname')
        selected_model.set_value(model_current)
        selected_model.set_select(list_of_modal)
        selected_model.set_location(2, 0, 3)
        selected_model.set_action(
            self.request, self.get_action(), {'modal': FORMTYPE_REFRESH, 'close': CLOSE_NO})
        self.add_component(selected_model)
        if self.select_class is not None:
            grid = self.get_components(self.field_id)
            grid.add_action(self.request, self.select_class.get_action(_("Select"), "images/ok.png"), {
                            'close': CLOSE_YES, 'unique': SELECT_SINGLE, 'params': {'pkname': self.field_id}}, 0)
