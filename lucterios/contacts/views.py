# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL, FORMTYPE_REFRESH, CLOSE_NO, StubAction, ActionsManage
from lucterios.framework.xfergraphic import XferContainerCustom
from lucterios.framework.xferadvance import XferDelete, XferAddEditor, XferListEditor
from lucterios.framework.xfercomponents import XferCompImage, XferCompLabelForm, XferCompEdit, XferCompGrid
from lucterios.contacts.models import PostalCode, Function, StructureType, LegalEntity, Individual
from django.utils import six
from django.core.exceptions import ObjectDoesNotExist
from lucterios.CORE.models import LucteriosUser
from lucterios.CORE.views_usergroup import UsersEdit

@MenuManage.describ(None, FORMTYPE_NOMODAL, 'core.general', _('View my account.'))
class Account(XferContainerCustom):
    caption = _("My account")
    icon = "account.png"

    def fillresponse(self):
        img = XferCompImage('img')
        img.set_value('contacts/images/account.png')
        img.set_location(0, 0, 1, 2)
        self.add_component(img)
        lab = XferCompLabelForm("title")
        lab.set_value_as_title(_('View my account.'))
        lab.set_location(1, 0, 2)
        self.add_component(lab)
        try:
            self.item = Individual.objects.get(user=self.request.user)  # pylint: disable=no-member
            self.add_action(AccountAddModify().get_changed(_("Edit"), "images/edit.png"), {'close':CLOSE_NO, 'params':{'individual':six.text_type(self.item.id)}})
        except ObjectDoesNotExist:
            self.item = LucteriosUser.objects.get(id=self.request.user.id)  # pylint: disable=no-member
            self.add_action(UsersEdit().get_changed(_("Edit"), "images/edit.png"), {'close':CLOSE_NO, 'params':{'user_actif':six.text_type(self.request.user.id)}})
        self.fill_from_model(1, 1, True)
        self.add_action(StubAction(_("Close"), "images/close.png"), {})

@MenuManage.describ(None)
class AccountAddModify(XferAddEditor):
    icon = "account.png"
    model = Individual
    field_id = 'individual'
    caption_add = _("My account")
    caption_modify = _("My account")
    locked = True

@MenuManage.describ('', FORMTYPE_NOMODAL, 'core.general', _('Our structure and its management'))
class CurrentStructure(XferContainerCustom):
    caption = _("Our details")
    icon = "ourDetails.png"
    model = LegalEntity
    field_id = 1

    def fillresponse(self):
        self.params['legal_entity'] = '1'
        img = XferCompImage('img')
        img.set_value('contacts/images/fields.png')
        img.set_location(0, 0, 1, 2)
        self.add_component(img)
        lab = XferCompLabelForm("title")
        lab.set_value_as_title(_('Our structure and its management'))
        lab.set_location(1, 0, 2)
        self.add_component(lab)
        self.fill_from_model(1, 1, True)
        self.add_action(CurrentStructureAddModify().get_changed(_("Edit"), "images/edit.png"), {'close':CLOSE_NO})
        self.add_action(StubAction(_("Close"), "images/close.png"), {})

@MenuManage.describ('CORE.add_parameter')
class CurrentStructureAddModify(XferAddEditor):
    icon = "ourDetails.png"
    model = LegalEntity
    field_id = 1
    caption_add = _("Our details")
    caption_modify = _("Our details")
    locked = True

MenuManage.add_sub("contact.conf", "core.extensions", "", _("Contact"), "", 1)

@MenuManage.describ('CORE.change_parameter', FORMTYPE_NOMODAL, 'contact.conf', _('Management functions of individuals and categories of legal entities.'))
class Configuration(XferContainerCustom):
    caption = _("Contacts configuration")
    icon = "contactsConfig.png"

    def _fill_functions(self):
        self.new_tab(_("Functions and responsabilities"))
        img = XferCompImage('imgFunction')
        img.set_value('contacts/images/function.png')
        img.set_location(0, 0)
        self.add_component(img)
        img = XferCompLabelForm('titleFunction')
        img.set_value_as_title(_("Functions list"))
        img.set_location(1, 0)
        self.add_component(img)
        self.model = Function
        dbfunction = Function.objects.all()  # pylint: disable=no-member
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
        img.set_value('contacts/images/category.png')
        img.set_location(0, 0)
        self.add_component(img)
        img = XferCompLabelForm('titleType')
        img.set_value_as_title(_('Structure types list'))
        img.set_location(1, 0)
        self.add_component(img)
        self.model = StructureType
        dbcategorie = StructureType.objects.all()  # pylint: disable=no-member
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

    def fillresponse(self):
        self._fill_functions()
        self._fill_structuretype()
        self.add_action(StubAction(_("Close"), "images/close.png"), {})

@ActionsManage.affect('Function', 'add')
@MenuManage.describ('CORE.add_parameter')
class FunctionAddModify(XferAddEditor):
    icon = "function.png"
    model = Function
    field_id = 'function'
    caption_add = _("Add function")
    caption_modify = _("Modify function")

@ActionsManage.affect('Function', 'del')
@MenuManage.describ('CORE.add_parameter')
class FunctionDel(XferDelete):
    caption = _("Delete function")
    icon = "function.png"
    model = Function
    field_id = 'function'

@ActionsManage.affect('StructureType', 'add')
@MenuManage.describ('CORE.add_parameter')
class StructureTypeAddModify(XferAddEditor):
    icon = "function.png"
    model = StructureType
    field_id = 'structure_type'
    caption_add = _("Add structure type")
    caption_modify = _("Modify structure type")

@ActionsManage.affect('StructureType', 'del')
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
            local_struct = LegalEntity.objects.get(id=1)  # pylint: disable=no-member
            filter_postal_code = six.text_type(local_struct.postal_code)
        lbl = XferCompLabelForm('filtre')
        lbl.set_value_as_name(_('Filtrer by postal code'))
        lbl.set_location(1, 0)
        self.add_component(lbl)
        comp = XferCompEdit('filter_postal_code')
        comp.set_value(filter_postal_code)
        comp.set_action(self.request, self, {'modal':FORMTYPE_REFRESH, 'close':CLOSE_NO})
        comp.set_location(1, 1)
        self.add_component(comp)
        self.filter = {'postal_code__startswith':filter_postal_code}
