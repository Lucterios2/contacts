# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL, \
    FORMTYPE_REFRESH, CLOSE_NO
from lucterios.framework.xfergraphic import XferContainerAcknowledge, \
    XferContainerCustom, XferSave
from lucterios.framework.xfercomponents import XferCompImage, XferCompLabelForm, \
    XferCompEdit, XferCompGrid
from lucterios.contacts.models import PostalCode

@MenuManage.describ(None, FORMTYPE_NOMODAL, 'core.general', _('View my account.'))
class Account(XferContainerAcknowledge):
    caption = _("My account")
    icon = "account.png"

@MenuManage.describ('', FORMTYPE_NOMODAL, 'core.general', _('Our structure and its management'))
class CurrentStructure(XferContainerAcknowledge):
    caption = _("Our details")
    icon = "ourDetails.png"

MenuManage.add_sub("contact.conf", "core.extensions", "", _("Contact"), "", 1)

@MenuManage.describ('', FORMTYPE_NOMODAL, 'contact.conf', _('Management functions of individuals and categories of legal entities.'))
class Configuration(XferContainerAcknowledge):
    caption = _("Contacts configuration")
    icon = "contactsConfig.png"

@MenuManage.describ('', FORMTYPE_NOMODAL, 'contact.conf', _('Management of postal codes associated with their communes.'))
class PostalCodeList(XferContainerCustom):
    caption = _("Postal code")
    icon = "postalCode.png"

    def fillresponse(self, filter_postal_code=''):
        img = XferCompImage('img')
        img.set_value('contacts/images/postalCode.png')
        img.set_location(0, 0, 1, 2)
        self.add_component(img)
        # TODO: search postal code of current structure
#         if filtre_postal_code == '':
#             local_struct = DBObj_org_lucterios_contacts_personneMorale
#             local_struct.get(1)
#             filtre_postal_code = local_struct.postal_code
        lbl = XferCompLabelForm('filtre')
        lbl.set_value("{[bold]}%s{[/bold]}" % _('Filtrer by postal code'))
        lbl.set_location(1, 0)
        self.add_component(lbl)
        comp = XferCompEdit('filter_postal_code')
        comp.set_value(filter_postal_code)
        comp.set_action(self.request, self.get_changed("", ""), {'modal':FORMTYPE_REFRESH, 'close':CLOSE_NO})
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
        self.add_action(XferContainerAcknowledge().get_changed(_("close"), "images/close.png"), {})

@MenuManage.describ('')
class PostalCodeAdd(XferContainerCustom):
    caption = _("Add postal code")
    icon = "postalCode.png"
    model = PostalCode
    field_id = 'postalCode'

    def fillresponse(self):
        img = XferCompImage('img')
        img.set_value('contacts/images/postalCode.png')
        img.set_location(0, 0, 1, 6)
        self.add_component(img)
        self.fill_from_model(1, 0, False, ['postal_code', 'city', 'country'])

        self.add_action(PostalCodeModify().get_changed(_('Ok'), 'images/ok.png'), {})
        self.add_action(XferContainerAcknowledge().get_changed(_('Cancel'), 'images/cancel.png'), {})

@MenuManage.describ('')
class PostalCodeModify(XferSave):
    caption = _("Delete postal code")
    icon = "postalCode.png"
    model = PostalCode
    field_id = 'postalCode'
    raise_except_class = PostalCodeAdd

@MenuManage.describ('', FORMTYPE_NOMODAL, 'contact.conf', _('Configuring settings to send email'))
class ConfigMail(XferContainerAcknowledge):
    caption = _("Email configuration")
    icon = "emailconf.png"
