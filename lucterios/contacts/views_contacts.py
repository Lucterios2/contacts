# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL, FORMTYPE_REFRESH, CLOSE_NO, icon_path, SubAction
from lucterios.framework.xfergraphic import XferContainerCustom
from lucterios.contacts.models import LegalEntity, Individual
from lucterios.framework.xferadvance import XferAddEditor, XferDelete, XferShowEditor, XferListEditor, XferSave
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompEdit, XferCompImage
from lucterios.CORE.models import LucteriosUser
from lucterios.CORE.views_usergroup import UsersEdit
from django.utils import six

MenuManage.add_sub("office", None, "contacts/images/office.png", _("Office"), _("Office tools"), 70)

MenuManage.add_sub("contact.actions", "office", "contacts/images/contacts.png", _("Addresses and contacts"), _("Management of men or women and organizations saved."), 50)

@MenuManage.describ('contacts.add_legalentity')
class LegalEntityAddModify(XferAddEditor):
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'
    caption_add = _("Add legal entity")
    caption_modify = _("Modify legal entity")

@MenuManage.describ('contacts.add_legalentity')

class LegalEntityShow(XferShowEditor):
    caption = _("Show legal entity")
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'
    modify_class = LegalEntityAddModify

@MenuManage.describ('contacts.delete_legalentity')
class LegalEntityDel(XferDelete):
    caption = _("Delete legal entity")
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'

@MenuManage.describ('contacts.change_legalentity', FORMTYPE_NOMODAL, 'contact.actions', _('Management of a structure or organization of people (company, association, administration, ...)'))
class LegalEntityList(XferListEditor):
    caption = _("Legal entities")
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'
    field_names = ["name", 'tel1', 'tel2', 'email']
    show_class = LegalEntityShow
    add_class = LegalEntityAddModify
    del_class = LegalEntityDel

    def fillresponse_header(self):
        self.fill_from_model(0, 2, False, ['structure_type'])
        obj_strtype = self.get_components('structure_type')
        obj_strtype.set_action(self.request, self, {'modal':FORMTYPE_REFRESH, 'close':CLOSE_NO})
        structure_type = self.getparam('structure_type')
        if (structure_type is not None) and (structure_type != '0'):
            self.filter = {'structure_type':int(structure_type)}

@MenuManage.describ('contacts.add_individual')
class IndividualAddModify(XferAddEditor):
    icon = "individual.png"
    model = Individual
    field_id = 'individual'
    caption_add = _("Add individual")
    caption_modify = _("Modify individual")

@MenuManage.describ('contacts.change_individual')
class IndividualShow(XferShowEditor):
    caption = _("Show individual")
    icon = "individual.png"
    model = Individual
    field_id = 'individual'
    modify_class = IndividualAddModify

@MenuManage.describ('contacts.delete_individual')
class IndividualDel(XferDelete):
    caption = _("Delete individual")
    icon = "individual.png"
    model = Individual
    field_id = 'individual'

@MenuManage.describ('contacts.change_individual', FORMTYPE_NOMODAL, 'contact.actions', _('Management of men and women registered'))
class IndividualList(XferListEditor):
    caption = _("Individuals")
    icon = "individual.png"
    model = Individual
    field_id = 'individual'
    field_names = ["firstname", "lastname", 'tel1', 'tel2', 'email']
    show_class = IndividualShow
    add_class = IndividualAddModify
    del_class = IndividualDel

    def fillresponse_header(self):
        name_filter = self.getparam('filter')
        if name_filter is None:
            name_filter = ""
        lbl = XferCompLabelForm('lbl_filtre')
        lbl.set_value_as_name(_('Filtrer by name'))
        lbl.set_location(0, 2)
        self.add_component(lbl)
        comp = XferCompEdit('filter')
        comp.set_value(name_filter)
        comp.set_action(self.request, self, {'modal':FORMTYPE_REFRESH, 'close':CLOSE_NO})
        comp.set_location(1, 2)
        self.add_component(comp)
        if name_filter != "":
            from django.db.models import Q
            self.filter = [Q(firstname__contains=name_filter) | Q(lastname__contains=name_filter)]

@MenuManage.describ('auth.add_user')
class IndividualUserAdd(XferContainerCustom):
    # pylint: disable=too-many-public-methods
    caption = _("Add as an users")
    icon = "user.png"
    model = LucteriosUser

    def fillresponse(self):
        img = XferCompImage('img')
        img.set_value(icon_path(self))
        img.set_location(0, 0, 1, 3)
        self.add_component(img)
        self.fill_from_model(1, 0, False, ['username'])
        self.add_action(IndividualUserValid().get_changed(_('Ok'), 'images/ok.png'), {})
        self.add_action(SubAction(_('Cancel'), 'images/cancel.png'), {})

@MenuManage.describ('auth.add_user')
class IndividualUserValid(XferSave):
    # pylint: disable=too-many-public-methods
    caption = _("Add as an users")
    icon = "user.png"
    model = LucteriosUser

    def fillresponse(self, individual):
        XferSave.fillresponse(self)
        if self.except_msg == '':
            obj_indiv = Individual.objects.get(pk=individual) # pylint: disable=no-member
            obj_indiv.user = self.item
            obj_indiv.save()
            self.item.saving(self)
            self.params['user_actif'] = six.text_type(self.item.id)
            self.params['IDENT_READ'] = 'YES'
            self.redirect_action(UsersEdit())

@MenuManage.describ('contacts.change_individual', FORMTYPE_NOMODAL, 'contact.actions', _('To find an individual following a set of criteria.'))
class IndividualSearch(XferContainerCustom):
    caption = _("Individual search")
    icon = "individualFind.png"

@MenuManage.describ('contacts.change_individual', FORMTYPE_NOMODAL, 'contact.actions', _('To find a legal entity following a set of criteria.'))
class LegalEntitySearch(XferContainerCustom):
    caption = _("Legal entity search")
    icon = "legalEntityFind.png"
