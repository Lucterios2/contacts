# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL
from lucterios.framework.xfergraphic import XferContainerAcknowledge

MenuManage.add_sub("office", None, "contacts/images/office.png", _("Office"), _("Office tools"), 70)

MenuManage.add_sub("contact.actions", "office", "contacts/images/contacts.png", _("Addresses and contacts"), _("Management of men or women and organizations saved."), 50)

@MenuManage.describ('', FORMTYPE_NOMODAL, 'contact.actions', _('Management of a structure or organization of people (company, association, administration, ...)'))
class LegalEntityList(XferContainerAcknowledge):
    caption = _("Legal entities")
    icon = "legalEntity.png"

@MenuManage.describ('', FORMTYPE_NOMODAL, 'contact.actions', _('Management of men and women registered'))
class IndividualList(XferContainerAcknowledge):
    caption = _("Individuals")
    icon = "individual.png"

@MenuManage.describ('', FORMTYPE_NOMODAL, 'contact.actions', _('To find an individual following a set of criteria.'))
class IndividualSearch(XferContainerAcknowledge):
    caption = _("Individual search")
    icon = "individualFind.png"

@MenuManage.describ('', FORMTYPE_NOMODAL, 'contact.actions', _('To find a legal entity following a set of criteria.'))
class LegalEntitySearch(XferContainerAcknowledge):
    caption = _("Legal entity search")
    icon = "legalEntityFind.png"
