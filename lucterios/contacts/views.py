# -*- coding: utf-8 -*-
'''
Viewers for configuration and generic actions

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
from django.utils import six
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL, FORMTYPE_REFRESH, CLOSE_NO, WrapAction, ActionsManage, \
    FORMTYPE_MODAL
from lucterios.framework.xfergraphic import XferContainerCustom
from lucterios.framework.xferadvance import XferDelete, XferAddEditor, XferListEditor
from lucterios.framework.xfercomponents import XferCompImage, XferCompLabelForm, XferCompEdit, XferCompGrid
from lucterios.CORE.models import LucteriosUser
from lucterios.CORE.views_usergroup import UsersEdit
from lucterios.CORE.xferprint import XferPrintAction
from lucterios.contacts.models import PostalCode, Function, StructureType, LegalEntity, Individual, \
    CustomField
from lucterios.framework import signal_and_lock
from lucterios.CORE.parameters import Params


@MenuManage.describ(None, FORMTYPE_MODAL, 'core.general', _('View my account.'))
class Account(XferContainerCustom):
    caption = _("My account")
    icon = "account.png"

    def fillresponse(self):
        img = XferCompImage('img')
        img.set_value('lucterios.contacts/images/account.png')
        img.set_location(0, 0, 1, 2)
        self.add_component(img)
        lab = XferCompLabelForm("title")
        lab.set_value_as_title(_('View my account.'))
        lab.set_location(1, 0, 2)
        self.add_component(lab)
        try:
            self.item = Individual.objects.get(
                user=self.request.user)
            self.add_action(AccountAddModify.get_action(_("Edit"), "images/edit.png"),
                            {'close': CLOSE_NO, 'params': {'individual': six.text_type(self.item.id)}})
        except ObjectDoesNotExist:
            self.item = LucteriosUser.objects.get(
                id=self.request.user.id)
            self.add_action(UsersEdit.get_action(_("Edit"), "images/edit.png"), {
                            'close': CLOSE_NO, 'params': {'user_actif': six.text_type(self.request.user.id)}})
        self.fill_from_model(1, 1, True)
        self.add_action(WrapAction(_("Close"), "images/close.png"), {})


@MenuManage.describ(None)
class AccountAddModify(XferAddEditor):
    icon = "account.png"
    model = Individual
    field_id = 'individual'
    caption_add = _("My account")
    caption_modify = _("My account")
    locked = True


@MenuManage.describ('', FORMTYPE_MODAL, 'core.general', _('Our structure and its management'))
class CurrentStructure(XferContainerCustom):
    caption = _("Our details")
    icon = "ourDetails.png"
    model = LegalEntity
    field_id = 1

    def fillresponse(self):
        self.params['legal_entity'] = '1'
        img = XferCompImage('img')
        img.set_value('lucterios.contacts/images/fields.png')
        img.set_location(0, 0, 1, 2)
        self.add_component(img)
        lab = XferCompLabelForm("title")
        lab.set_value_as_title(_('Our structure and its management'))
        lab.set_location(1, 0, 4)
        self.add_component(lab)
        self.fill_from_model(1, 1, True)
        self.add_action(CurrentStructureAddModify.get_action(
            _("Edit"), "images/edit.png"), {'close': CLOSE_NO})
        self.add_action(CurrentStructurePrint.get_action(
            _("Print"), "images/print.png"), {'close': CLOSE_NO})
        self.add_action(WrapAction(_("Close"), "images/close.png"), {})


@MenuManage.describ('')
class CurrentStructurePrint(XferPrintAction):
    icon = "ourDetails.png"
    model = LegalEntity
    field_id = 1
    caption = _("Our details")
    action_class = CurrentStructure


@MenuManage.describ('CORE.add_parameter')
class CurrentStructureAddModify(XferAddEditor):
    icon = "ourDetails.png"
    model = LegalEntity
    field_id = 1
    caption_add = _("Our details")
    caption_modify = _("Our details")
    locked = True
    redirect_to_show = False

MenuManage.add_sub("contact.conf", "core.extensions", "", _("Contact"), "", 1)


@MenuManage.describ('CORE.change_parameter', FORMTYPE_NOMODAL, 'contact.conf', _('Management functions of individuals and categories of legal entities.'))
class Configuration(XferContainerCustom):
    caption = _("Contacts configuration")
    icon = "contactsConfig.png"

    def _fill_functions(self):
        self.new_tab(_("Functions and responsabilities"))
        img = XferCompImage('imgFunction')
        img.set_value('lucterios.contacts/images/function.png')
        img.set_location(0, 0)
        self.add_component(img)
        img = XferCompLabelForm('titleFunction')
        img.set_value_as_title(_("Functions list"))
        img.set_location(1, 0)
        self.add_component(img)
        self.model = Function
        dbfunction = Function.objects.all()
        grid = XferCompGrid("function")
        grid.set_model(dbfunction, None, self)
        grid.add_actions(self)
        grid.set_location(0, 1, 2)
        grid.set_size(200, 500)
        self.add_component(grid)
        lbl = XferCompLabelForm("nbFunction")
        lbl.set_location(0, 2, 2)
        lbl.set_value(_("Number of function show: %d") % grid.nb_lines)
        self.add_component(lbl)

    def _fill_structuretype(self):
        self.new_tab(_("Structure type"))
        img = XferCompImage('imgType')
        img.set_value('lucterios.contacts/images/category.png')
        img.set_location(0, 0)
        self.add_component(img)
        img = XferCompLabelForm('titleType')
        img.set_value_as_title(_('Structure types list'))
        img.set_location(1, 0)
        self.add_component(img)
        self.model = StructureType
        dbcategorie = StructureType.objects.all()
        grid = XferCompGrid("structure_type")
        grid.set_model(dbcategorie, None, self)
        grid.add_actions(self)
        grid.set_location(0, 1, 2)
        grid.set_size(200, 500)
        self.add_component(grid)
        lbl = XferCompLabelForm("nbType")
        lbl.set_location(0, 2, 2)
        lbl.set_value(_("Number of structure type show: %d") % grid.nb_lines)
        self.add_component(lbl)

    def _fill_customfield(self):
        self.new_tab(_("Custom field"))
        img = XferCompImage('imgField')
        img.set_value('lucterios.contacts/images/fields.png')
        img.set_location(0, 0)
        self.add_component(img)
        img = XferCompLabelForm('titleField')
        img.set_value_as_title(_('custom field list'))
        img.set_location(1, 0)
        self.add_component(img)
        self.model = CustomField
        dbcustom = CustomField.objects.all()
        grid = XferCompGrid("custom_field")
        grid.set_model(dbcustom, None, self)
        grid.add_actions(self)
        grid.set_location(0, 1, 2)
        grid.set_size(200, 500)
        self.add_component(grid)
        lbl = XferCompLabelForm("nbField")
        lbl.set_location(0, 2, 2)
        lbl.set_value(_("Number of custom field show: %d") % grid.nb_lines)
        self.add_component(lbl)

    def fillresponse(self):
        self._fill_functions()
        self._fill_structuretype()
        self._fill_customfield()
        self.add_action(WrapAction(_("Close"), "images/close.png"), {})


@ActionsManage.affect('Function', 'add')
@MenuManage.describ('CORE.add_parameter')
class FunctionAddModify(XferAddEditor):
    icon = "function.png"
    model = Function
    field_id = 'function'
    caption_add = _("Add function")
    caption_modify = _("Modify function")


@ActionsManage.affect('Function', 'delete')
@MenuManage.describ('CORE.add_parameter')
class FunctionDel(XferDelete):
    caption = _("Delete function")
    icon = "function.png"
    model = Function
    field_id = 'function'


@ActionsManage.affect('CustomField', 'add', 'edit')
@MenuManage.describ('CORE.add_parameter')
class CustomFieldAddModify(XferAddEditor):
    icon = "fields.png"
    model = CustomField
    field_id = 'custom_field'
    caption_add = _("Add custom field")
    caption_modify = _("Modify custom field")


@ActionsManage.affect('CustomField', 'delete')
@MenuManage.describ('CORE.add_parameter')
class CustomFieldDel(XferDelete):
    caption = _("Delete custom field")
    icon = "fields.png"
    model = CustomField
    field_id = 'custom_field'


@ActionsManage.affect('StructureType', 'add')
@MenuManage.describ('CORE.add_parameter')
class StructureTypeAddModify(XferAddEditor):
    icon = "function.png"
    model = StructureType
    field_id = 'structure_type'
    caption_add = _("Add structure type")
    caption_modify = _("Modify structure type")


@ActionsManage.affect('StructureType', 'delete')
@MenuManage.describ('CORE.add_parameter')
class StructureTypeDel(XferDelete):
    caption = _("Delete structure type")
    icon = "function.png"
    model = StructureType
    field_id = 'structure_type'


@ActionsManage.affect('PostalCode', 'add')
@MenuManage.describ('contacts.add_postalcode')
class PostalCodeAdd(XferAddEditor):
    caption_add = _("Add function")
    caption_modify = _("Add postal code")
    icon = "postalCode.png"
    model = PostalCode
    field_id = 'postalCode'


@MenuManage.describ('contacts.change_postalcode', FORMTYPE_NOMODAL, 'contact.conf', _('Management of postal codes associated with their communes.'))
class PostalCodeList(XferListEditor):
    caption = _("Postal code")
    icon = "postalCode.png"
    model = PostalCode
    field_id = 'postalCode'

    def fillresponse_header(self):
        filter_postal_code = self.getparam('filter_postal_code')
        if filter_postal_code is None:
            local_struct = LegalEntity.objects.get(
                id=1)
            filter_postal_code = six.text_type(local_struct.postal_code)
        lbl = XferCompLabelForm('filtre')
        lbl.set_value_as_name(_('Filtrer by postal code'))
        lbl.set_location(1, 0)
        self.add_component(lbl)
        comp = XferCompEdit('filter_postal_code')
        comp.set_value(filter_postal_code)
        comp.set_action(self.request, self.get_action(),
                        {'modal': FORMTYPE_REFRESH, 'close': CLOSE_NO})
        comp.set_location(1, 1)
        self.add_component(comp)
        self.filter = Q(postal_code__startswith=filter_postal_code)


@signal_and_lock.Signal.decorate('config')
def config_contacts(xfer):
    Params.fill(xfer, ['contacts-mailtoconfig'], 1, 10)
    xfer.params['params'].append('contacts-mailtoconfig')
    return True
