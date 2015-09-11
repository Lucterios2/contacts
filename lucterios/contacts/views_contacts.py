# -*- coding: utf-8 -*-
'''
Viewer of legal entity, individual and responsability actions

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
from django.db.models import Q

from lucterios.framework.tools import MenuManage, WrapAction, ActionsManage
from lucterios.framework.tools import FORMTYPE_NOMODAL, FORMTYPE_REFRESH, CLOSE_NO, FORMTYPE_MODAL, CLOSE_YES, SELECT_SINGLE
from lucterios.framework.xfergraphic import XferContainerCustom
from lucterios.framework.xferadvance import XferAddEditor, XferDelete, XferShowEditor, XferListEditor, XferSave
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompEdit, XferCompImage, XferCompGrid
from lucterios.framework.xfersearch import XferSearchEditor
from lucterios.CORE.models import LucteriosUser
from lucterios.CORE.xferprint import XferPrintAction, XferPrintListing, \
    XferPrintLabel
from lucterios.contacts.models import LegalEntity, Individual, Responsability, \
    AbstractContact
from lucterios.framework import signal_and_lock
from lucterios.CORE.editors import XferSavedCriteriaSearchEditor

MenuManage.add_sub(
    "office", None, "lucterios.contacts/images/office.png", _("Office"), _("Office tools"), 70)

MenuManage.add_sub("contact.actions", "office", "lucterios.contacts/images/contacts.png",
                   _("Addresses and contacts"), _("Management of men or women and organizations saved."), 50)


@ActionsManage.affect('LegalEntity', 'add', 'modify')
@MenuManage.describ('contacts.add_abstractcontact')
class LegalEntityAddModify(XferAddEditor):
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'
    caption_add = _("Add legal entity")
    caption_modify = _("Modify legal entity")


@ActionsManage.affect('LegalEntity', 'show')
@MenuManage.describ('contacts.change_legalentity')
class LegalEntityShow(XferShowEditor):
    caption = _("Show legal entity")
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'


@ActionsManage.affect('LegalEntity', 'print')
@MenuManage.describ('contacts.change_legalentity')
class LegalEntityPrint(XferPrintAction):
    caption = _("Show legal entity")
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'
    action_class = LegalEntityShow


@ActionsManage.affect('LegalEntity', 'delete')
@MenuManage.describ('contacts.delete_abstractcontact')
class LegalEntityDel(XferDelete):
    caption = _("Delete legal entity")
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'


@MenuManage.describ('contacts.change_abstractcontact', FORMTYPE_NOMODAL, 'contact.actions', _('Management of a structure or organization of people (company, association, administration, ...)'))
class LegalEntityList(XferListEditor):
    caption = _("Legal entities")
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'

    def fillresponse_header(self):
        self.fill_from_model(0, 2, False, ['structure_type'])
        obj_strtype = self.get_components('structure_type')
        obj_strtype.set_action(
            self.request, self.get_action(), {'modal': FORMTYPE_REFRESH, 'close': CLOSE_NO})
        structure_type = self.getparam('structure_type')
        if (structure_type is not None) and (structure_type != '0'):
            self.filter = Q(structure_type=int(structure_type))

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        self.item.editor.add_email_selector(self, 0, self.get_max_row() + 1, 2)


@ActionsManage.affect('LegalEntity', 'listing')
@MenuManage.describ('contacts.change_abstractcontact')
class LegalEntityListing(XferPrintListing):
    caption = _("Legal entities")
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'

    def get_filter(self):
        structure_type = self.getparam('structure_type')
        if (structure_type is not None) and (structure_type != '0'):
            return Q(structure_type=int(structure_type))
        else:
            return XferPrintListing.get_filter(self)


@ActionsManage.affect('LegalEntity', 'label')
@MenuManage.describ('contacts.change_abstractcontact')
class LegalEntityLabel(XferPrintLabel):
    caption = _("Legal entities")
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'

    def get_filter(self):
        structure_type = self.getparam('structure_type')
        if (structure_type is not None) and (structure_type != '0'):
            return [Q(structure_type=int(structure_type))]
        else:
            return XferPrintLabel.get_filter(self)


@ActionsManage.affect('Individual', 'add', 'modify')
@MenuManage.describ('contacts.add_abstractcontact')
class IndividualAddModify(XferAddEditor):
    icon = "individual.png"
    model = Individual
    field_id = 'individual'
    caption_add = _("Add individual")
    caption_modify = _("Modify individual")


@ActionsManage.affect('Individual', 'show')
@MenuManage.describ('contacts.change_abstractcontact')
class IndividualShow(XferShowEditor):
    caption = _("Show individual")
    icon = "individual.png"
    model = Individual
    field_id = 'individual'


@ActionsManage.affect('Individual', 'print')
@MenuManage.describ('contacts.change_abstractcontact')
class IndividualPrint(XferPrintAction):
    caption = _("Show individual")
    icon = "individual.png"
    model = Individual
    field_id = 'individual'
    action_class = IndividualShow


@ActionsManage.affect('Individual', 'delete')
@MenuManage.describ('contacts.delete_abstractcontact')
class IndividualDel(XferDelete):
    caption = _("Delete individual")
    icon = "individual.png"
    model = Individual
    field_id = 'individual'


@MenuManage.describ('contacts.change_abstractcontact', FORMTYPE_NOMODAL, 'contact.actions', _('Management of men and women registered'))
class IndividualList(XferListEditor):
    caption = _("Individuals")
    icon = "individual.png"
    model = Individual
    field_id = 'individual'

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
        comp.set_action(self.request, self.get_action(),
                        {'modal': FORMTYPE_REFRESH, 'close': CLOSE_NO})
        comp.set_location(1, 2)
        self.add_component(comp)
        if name_filter != "":
            self.filter = Q(firstname__contains=name_filter) | Q(
                lastname__contains=name_filter)

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        self.item.editor.add_email_selector(self, 0, self.get_max_row() + 1, 2)


@ActionsManage.affect('Individual', 'label')
@MenuManage.describ('contacts.change_abstractcontact')
class IndividualLabel(XferPrintLabel):
    caption = _("Individuals")
    icon = "individual.png"
    model = Individual
    field_id = 'individual'

    def get_filter(self):
        name_filter = self.getparam('filter')
        if (name_filter is not None) and (name_filter != ""):
            return [Q(firstname__contains=name_filter) | Q(lastname__contains=name_filter)]
        else:
            return XferPrintLabel.get_filter(self)


@ActionsManage.affect('Individual', 'listing')
@MenuManage.describ('contacts.change_abstractcontact')
class IndividualListing(XferPrintListing):
    caption = _("Individuals")
    icon = "individual.png"
    model = Individual
    field_id = 'individual'
    with_text_export = True

    def get_filter(self):
        name_filter = self.getparam('filter')
        if (name_filter is not None) and (name_filter != ""):
            return Q(firstname__contains=name_filter) | Q(lastname__contains=name_filter)
        else:
            return XferPrintListing.get_filter(self)


@ActionsManage.affect('Individual', 'useradd')
@MenuManage.describ('auth.add_user')
class IndividualUserAdd(XferContainerCustom):

    caption = _("Add as an users")
    icon = "user.png"
    model = LucteriosUser

    def fillresponse(self):
        img = XferCompImage('img')
        img.set_value(self.icon_path())
        img.set_location(0, 0, 1, 3)
        self.add_component(img)
        self.fill_from_model(1, 0, False, ['username'])
        self.add_action(
            IndividualUserValid.get_action(_('Ok'), 'images/ok.png'), {})
        self.add_action(WrapAction(_('Cancel'), 'images/cancel.png'), {})


@MenuManage.describ('auth.add_user')
class IndividualUserValid(XferSave):

    caption = _("Add as an users")
    icon = "user.png"
    model = LucteriosUser

    def fillresponse(self, individual):
        XferSave.fillresponse(self)
        if self.except_msg == '':
            obj_indiv = Individual.objects.get(
                pk=individual)
            obj_indiv.user = self.item
            obj_indiv.save()
            obj_indiv.editor.saving(self)
            self.redirect_action(ActionsManage.get_act_changed('LucteriosUser', 'edit', '', ''), {
                                 'params': {'user_actif': six.text_type(self.item.id), 'IDENT_READ': 'YES'}})


@ActionsManage.affect('Responsability', 'add')
@MenuManage.describ('contacts.change_responsability')
class ResponsabilityAdd(XferContainerCustom):

    caption = _("Add responsability")
    icon = "function.png"
    model = Responsability
    field_id = 'responsability_set'

    def fillresponse(self, legal_entity=0, name_filter=''):
        self.item.legal_entity = LegalEntity.objects.get(
            id=legal_entity)
        img = XferCompImage('img')
        img.set_value(self.icon_path())
        img.set_location(0, 0, 1, 3)
        self.add_component(img)
        self.fill_from_model(1, 0, True, ['legal_entity'])
        lbl = XferCompLabelForm('lbl_filtre')
        lbl.set_value_as_name(_('Filtrer by name'))
        lbl.set_location(1, 2)
        self.add_component(lbl)
        comp = XferCompEdit('filter')
        comp.set_value(name_filter)
        comp.set_action(self.request, self.get_action(),
                        {'modal': FORMTYPE_REFRESH, 'close': CLOSE_NO})
        comp.set_location(2, 2)
        self.add_component(comp)
        identfilter = []
        if name_filter != "":
            identfilter = [
                Q(firstname__contains=name_filter) | Q(lastname__contains=name_filter)]
        lbl = XferCompLabelForm('lbl_individual')
        lbl.set_value_as_name(_('individual'))
        lbl.set_location(1, 3)
        self.add_component(lbl)
        items = Individual.objects.filter(
            *identfilter)
        grid = XferCompGrid('individual')
        grid.set_model(items, None, self)
        grid.set_location(2, 3)
        grid.add_action(self.request, ResponsabilityModify.get_action(_("Select"), "images/ok.png"),
                        {'modal': FORMTYPE_MODAL, 'close': CLOSE_YES, 'unique': SELECT_SINGLE, 'params': {"SAVE": "YES"}})
        grid.add_action(self.request, IndividualShow.get_action(
            _("Show"), "images/edit.png"), {'modal': FORMTYPE_MODAL, 'close': CLOSE_NO, 'unique': SELECT_SINGLE})
        grid.add_action(self.request, ActionsManage.get_act_changed("Individual", "add", _(
            "Add"), "images/add.png"), {'modal': FORMTYPE_MODAL, 'close': CLOSE_NO})
        self.add_component(grid)


@ActionsManage.affect('Responsability', 'edit')
@MenuManage.describ('contacts.change_responsability')
class ResponsabilityModify(XferAddEditor):

    caption = _("Modify responsability")
    icon = "function.png"
    model = Responsability
    field_id = 'responsability'


@ActionsManage.affect('Responsability', 'delete')
@MenuManage.describ('contacts.delete_responsability')
class ResponsabilityDel(XferDelete):

    caption = _("Delete responsability")
    icon = "function.png"
    model = Responsability
    field_id = 'responsability'


@MenuManage.describ('contacts.change_abstractcontact', FORMTYPE_NOMODAL, 'contact.actions', _('To find an individual following a set of criteria.'))
class IndividualSearch(XferSavedCriteriaSearchEditor):
    caption = _("Individual search")
    icon = "individualFind.png"
    model = Individual
    field_id = 'individual'

    def fillresponse(self):
        XferSearchEditor.fillresponse(self)
        self.item.editor.add_email_selector(self, 0, self.get_max_row() + 1, 5)


@MenuManage.describ('contacts.change_abstractcontact', FORMTYPE_NOMODAL, 'contact.actions', _('To find a legal entity following a set of criteria.'))
class LegalEntitySearch(XferSavedCriteriaSearchEditor):
    caption = _("Legal entity search")
    icon = "legalEntityFind.png"
    model = LegalEntity
    field_id = 'legal_entity'

    def fillresponse(self):
        XferSearchEditor.fillresponse(self)
        self.item.editor.add_email_selector(self, 0, self.get_max_row() + 1, 5)


@ActionsManage.affect('AbstractContact', 'show')
@MenuManage.describ('contacts.change_abstractcontact')
class AbstractContactShow(XferShowEditor):
    icon = "contacts.png"
    model = AbstractContact
    field_id = 'abstractcontact'
    caption = _("Show contact")


@ActionsManage.affect('AbstractContact', 'delete')
@MenuManage.describ('contacts.delete_abstractcontact')
class AbstractContactDel(XferDelete):
    icon = "contacts.png"
    model = AbstractContact
    field_id = 'abstractcontact'
    caption = _("Delete contact")


@signal_and_lock.Signal.decorate('summary')
def summary_contacts(xfer):
    row = xfer.get_max_row() + 1
    lab = XferCompLabelForm('contactstitle')
    lab.set_value_as_infocenter(_("Addresses and contacts"))
    lab.set_location(0, row, 4)
    xfer.add_component(lab)
    nb_legal_entities = len(
        LegalEntity.objects.all())
    lbl_doc = XferCompLabelForm('lbl_nblegalentities')
    lbl_doc.set_location(0, row + 1, 4)
    lbl_doc.set_value_center(
        _("Total number of legal entities: %d") % nb_legal_entities)
    xfer.add_component(lbl_doc)
    nb_individual = len(Individual.objects.all())
    lbl_doc = XferCompLabelForm('lbl_nbindividuals')
    lbl_doc.set_location(0, row + 2, 4)
    lbl_doc.set_value_center(
        _("Total number of individuals: %d") % nb_individual)
    xfer.add_component(lbl_doc)
    lab = XferCompLabelForm('contactsend')
    lab.set_value_center('{[hr/]}')
    lab.set_location(0, row + 3, 4)
    xfer.add_component(lab)
    return True
