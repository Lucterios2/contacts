# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL, \
    FORMTYPE_REFRESH, CLOSE_NO, SELECT_SINGLE, SELECT_NONE
from lucterios.framework.xfergraphic import XferContainerAcknowledge, \
    XferContainerCustom
from lucterios.framework.xferadvance import XferDelete, XferAddEditor
from lucterios.framework.xfercomponents import XferCompImage, XferCompLabelForm, \
    XferCompEdit, XferCompGrid
from lucterios.contacts.models import PostalCode, Function, StructureType, \
    LegalEntity, Individual
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
            self.item = Individual.objects.get(user=self.request.user) # pylint: disable=no-member
            self.add_action(AccountAddModify().get_changed(_("Edit"), "images/edit.png"), {'close':CLOSE_NO, 'params':{'individual':six.text_type(self.item.id)}})
        except ObjectDoesNotExist:
            self.item = LucteriosUser.objects.get(id=self.request.user.id) # pylint: disable=no-member
            self.add_action(UsersEdit().get_changed(_("Edit"), "images/edit.png"), {'close':CLOSE_NO, 'params':{'user_actif':six.text_type(self.request.user.id)}})
        self.fill_from_model(1, 1, True)
        self.add_action(XferContainerAcknowledge().get_changed(_("Close"), "images/close.png"), {})

@MenuManage.describ(None)
class AccountAddModify(XferAddEditor):
    icon = "account.png"
    model = Individual
    field_id = 'individual'
    caption_add = _("My account")
    caption_modify = _("My account")

@MenuManage.describ('', FORMTYPE_NOMODAL, 'core.general', _('Our structure and its management'))
class CurrentStructure(XferContainerCustom):
    caption = _("Our details")
    icon = "ourDetails.png"
    model = LegalEntity
    field_id = 1

    def fillresponse(self):
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
        self.add_action(XferContainerAcknowledge().get_changed(_("Close"), "images/close.png"), {})

@MenuManage.describ('CORE.add_parameter')
class CurrentStructureAddModify(XferAddEditor):
    icon = "ourDetails.png"
    model = LegalEntity
    field_id = 1
    caption_add = _("Our details")
    caption_modify = _("Our details")

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
        dbfunction = Function.objects.all()  # pylint: disable=no-member
        grid = XferCompGrid("function")
        grid.set_model(dbfunction, ["name"], self)
        grid.add_action(self.request, FunctionAddModify().get_changed(_("Add"), "images/add.png"), {'close':CLOSE_NO, 'unique':SELECT_NONE})
        grid.add_action(self.request, FunctionDel().get_changed(_("Delete"), "images/suppr.png"), {'close':CLOSE_NO, 'unique':SELECT_SINGLE})
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
        dbcategorie = StructureType.objects.all()  # pylint: disable=no-member
        grid = XferCompGrid("structure_type")
        grid.set_model(dbcategorie, ["name"], self)
        grid.add_action(self.request, StructureTypeAddModify().get_changed(_("Add"), "images/add.png"), {'close':CLOSE_NO, 'select':SELECT_NONE})
        grid.add_action(self.request, StructureTypeDel().get_changed(_("Delete"), "images/suppr.png"), {'close':CLOSE_NO, 'select':SELECT_SINGLE})
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
        self.new_tab(_("Customized fields"))
        img = XferCompImage('imgfield')
        img.set_value('contacts/images/fields.png')
        img.set_location(0, 10)
        self.add_component(img)
        lab = XferCompLabelForm("titlefields")
        lab.set_value_as_title(_("Addon fields to customize contacts"))
        lab.set_location(1, 10, 5)
        self.add_component(lab)
        self.add_action(XferContainerAcknowledge().get_changed(_("Close"), "images/close.png"), {})

@MenuManage.describ('CORE.add_parameter')
class FunctionAddModify(XferAddEditor):
    icon = "function.png"
    model = Function
    field_id = 'function'
    caption_add = _("Add function")
    caption_modify = _("Modify function")

@MenuManage.describ('CORE.add_parameter')
class FunctionDel(XferDelete):
    caption = _("Delete function")
    icon = "function.png"
    model = Function
    field_id = 'function'

@MenuManage.describ('CORE.add_parameter')
class StructureTypeAddModify(XferAddEditor):
    icon = "function.png"
    model = StructureType
    field_id = 'structure_type'
    caption_add = _("Add structure type")
    caption_modify = _("Modify structure type")

@MenuManage.describ('CORE.add_parameter')
class StructureTypeDel(XferDelete):
    caption = _("Delete structure type")
    icon = "function.png"
    model = StructureType
    field_id = 'structure_type'

@MenuManage.describ('contacts.change_postalcode', FORMTYPE_NOMODAL, 'contact.conf', _('Management of postal codes associated with their communes.'))
class PostalCodeList(XferContainerCustom):
    caption = _("Postal code")
    icon = "postalCode.png"

    def fillresponse(self, filter_postal_code):
        self.caption = _("Postal code")
        img = XferCompImage('img')
        img.set_value('contacts/images/postalCode.png')
        img.set_location(0, 0, 1, 2)
        self.add_component(img)
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
        if filter_postal_code == '':
            postcode = PostalCode.objects.all()  # pylint: disable=no-member
        else:
            postcode = PostalCode.objects.filter(postal_code__startswith=filter_postal_code)  # pylint: disable=no-member
        grid = XferCompGrid("postalCode")
        grid.set_model(postcode, ['postal_code', 'city', 'country'], self)
        grid.add_action(self.request, PostalCodeAdd().get_changed(_("Add"), "images/add.png"), {'close':CLOSE_NO})
        grid.set_location(0, 2, 3)
        grid.set_size(300, 750)
        self.add_component(grid)
        lbl = XferCompLabelForm("nb")
        lbl.set_location(0, 3, 3)
        lbl.set_value(_("Total number of postal codes/city: %d") % grid.nb_lines)
        self.add_component(lbl)
        self.add_action(XferContainerAcknowledge().get_changed(_("Close"), "images/close.png"), {})

@MenuManage.describ('contacts.add_postalcode')
class PostalCodeAdd(XferAddEditor):
    caption_add = _("Add function")
    caption_modify = _("Add postal code")
    icon = "postalCode.png"
    model = PostalCode
    field_id = 'postalCode'

@MenuManage.describ('CORE.change_parameter', FORMTYPE_NOMODAL, 'contact.conf', _('Configuring settings to send email'))
class ConfigMail(XferContainerAcknowledge):
    caption = _("Email configuration")
    icon = "emailconf.png"
