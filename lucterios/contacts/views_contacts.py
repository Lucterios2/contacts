# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL
from lucterios.framework.xfergraphic import XferContainerCustom
from lucterios.contacts.models import LegalEntity, Individual
from lucterios.framework.xferadvance import XferAddEditor, XferDelete, XferShowEditor, XferListEditor

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

@MenuManage.describ('contacts.change_individual', FORMTYPE_NOMODAL, 'contact.actions', _('To find an individual following a set of criteria.'))
class IndividualSearch(XferContainerCustom):
    caption = _("Individual search")
    icon = "individualFind.png"

@MenuManage.describ('contacts.change_individual', FORMTYPE_NOMODAL, 'contact.actions', _('To find a legal entity following a set of criteria.'))
class LegalEntitySearch(XferContainerCustom):
    caption = _("Legal entity search")
    icon = "legalEntityFind.png"
