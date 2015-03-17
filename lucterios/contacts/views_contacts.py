# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL, \
    FORMTYPE_REFRESH, CLOSE_NO
from lucterios.framework.xfergraphic import XferContainerCustom
from lucterios.contacts.models import LegalEntity, Individual
from lucterios.framework.xferadvance import XferAddEditor, XferDelete, XferShowEditor, XferListEditor
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompEdit

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

@MenuManage.describ('contacts.change_individual', FORMTYPE_NOMODAL, 'contact.actions', _('To find an individual following a set of criteria.'))
class IndividualSearch(XferContainerCustom):
    caption = _("Individual search")
    icon = "individualFind.png"

@MenuManage.describ('contacts.change_individual', FORMTYPE_NOMODAL, 'contact.actions', _('To find a legal entity following a set of criteria.'))
class LegalEntitySearch(XferContainerCustom):
    caption = _("Legal entity search")
    icon = "legalEntityFind.png"
