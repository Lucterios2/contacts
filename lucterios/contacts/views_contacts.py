# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.utils import six

from lucterios.framework.tools import MenuManage, icon_path, StubAction, ActionsManage
from lucterios.framework.tools import FORMTYPE_NOMODAL, FORMTYPE_REFRESH, CLOSE_NO, FORMTYPE_MODAL, CLOSE_YES, SELECT_SINGLE
from lucterios.framework.xfergraphic import XferContainerCustom
from lucterios.framework.xferadvance import XferAddEditor, XferDelete, XferShowEditor, XferListEditor, XferSave
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompEdit, XferCompImage, XferCompGrid
from lucterios.framework.xfersearch import XferSearchEditor
from lucterios.CORE.models import LucteriosUser
from lucterios.contacts.models import LegalEntity, Individual, Responsability

MenuManage.add_sub("office", None, "contacts/images/office.png", _("Office"), _("Office tools"), 70)

MenuManage.add_sub("contact.actions", "office", "contacts/images/contacts.png", _("Addresses and contacts"), _("Management of men or women and organizations saved."), 50)

@ActionsManage.affect('LegalEntity', 'add')
@MenuManage.describ('contacts.add_legalentity')
class LegalEntityAddModify(XferAddEditor):
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'
    caption_add = _("Add legal entity")
    caption_modify = _("Modify legal entity")

@ActionsManage.affect('LegalEntity', 'show')
@MenuManage.describ('contacts.add_legalentity')
class LegalEntityShow(XferShowEditor):
    caption = _("Show legal entity")
    icon = "legalEntity.png"
    model = LegalEntity
    field_id = 'legal_entity'
    modify_class = LegalEntityAddModify

@ActionsManage.affect('LegalEntity', 'del')
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

    def fillresponse_header(self):
        self.fill_from_model(0, 2, False, ['structure_type'])
        obj_strtype = self.get_components('structure_type')
        obj_strtype.set_action(self.request, self, {'modal':FORMTYPE_REFRESH, 'close':CLOSE_NO})
        structure_type = self.getparam('structure_type')
        if (structure_type is not None) and (structure_type != '0'):
            self.filter = {'structure_type':int(structure_type)}

@ActionsManage.affect('Individual', 'add')
@MenuManage.describ('contacts.add_individual')
class IndividualAddModify(XferAddEditor):
    icon = "individual.png"
    model = Individual
    field_id = 'individual'
    caption_add = _("Add individual")
    caption_modify = _("Modify individual")

@ActionsManage.affect('Individual', 'show')
@MenuManage.describ('contacts.change_individual')
class IndividualShow(XferShowEditor):
    caption = _("Show individual")
    icon = "individual.png"
    model = Individual
    field_id = 'individual'
    modify_class = IndividualAddModify

@ActionsManage.affect('Individual', 'del')
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

@ActionsManage.affect('Individual', 'useradd')
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
        self.add_action(StubAction(_('Cancel'), 'images/cancel.png'), {})

@MenuManage.describ('auth.add_user')
class IndividualUserValid(XferSave):
    # pylint: disable=too-many-public-methods
    caption = _("Add as an users")
    icon = "user.png"
    model = LucteriosUser

    def fillresponse(self, individual):
        XferSave.fillresponse(self)
        if self.except_msg == '':
            obj_indiv = Individual.objects.get(pk=individual)  # pylint: disable=no-member
            obj_indiv.user = self.item
            obj_indiv.save()
            obj_indiv.saving(self)
            self.params['user_actif'] = six.text_type(self.item.id)
            self.params['IDENT_READ'] = 'YES'
            self.redirect_action(ActionsManage.get_act_changed('LucteriosUser', 'edit', '', ''))

@ActionsManage.affect('Responsability', 'add')
@MenuManage.describ('contacts.change_responsability')
class ResponsabilityAdd(XferContainerCustom):
    # pylint: disable=too-many-public-methods
    caption = _("Add responsability")
    icon = "function.png"
    model = Responsability
    field_id = 'responsability_set'

    def fillresponse(self, legal_entity=0, name_filter=''):
        self.item.legal_entity = LegalEntity.objects.get(id=legal_entity)  # pylint: disable=no-member
        img = XferCompImage('img')
        img.set_value(icon_path(self))
        img.set_location(0, 0, 1, 3)
        self.add_component(img)
        self.fill_from_model(1, 0, True, ['legal_entity'])
        lbl = XferCompLabelForm('lbl_filtre')
        lbl.set_value_as_name(_('Filtrer by name'))
        lbl.set_location(1, 2)
        self.add_component(lbl)
        comp = XferCompEdit('filter')
        comp.set_value(name_filter)
        comp.set_action(self.request, self, {'modal':FORMTYPE_REFRESH, 'close':CLOSE_NO})
        comp.set_location(2, 2)
        self.add_component(comp)
        identfilter = []
        if name_filter != "":
            from django.db.models import Q
            identfilter = [Q(firstname__contains=name_filter) | Q(lastname__contains=name_filter)]
        lbl = XferCompLabelForm('lbl_individual')
        lbl.set_value_as_name(_('individual'))
        lbl.set_location(1, 3)
        self.add_component(lbl)
        items = Individual.objects.filter(*identfilter)  # pylint: disable=no-member
        grid = XferCompGrid('individual')
        grid.set_model(items, None, self)
        grid.set_location(2, 3)
        grid.add_action(self.request, ResponsabilityModify().get_changed(_("Select"), "images/ok.png"), {'modal':FORMTYPE_MODAL, 'close':CLOSE_YES, 'unique':SELECT_SINGLE, 'params':{"SAVE":"YES"}})
        grid.add_action(self.request, IndividualShow().get_changed(_("Show"), "images/edit.png"), {'modal':FORMTYPE_MODAL, 'close':CLOSE_NO, 'unique':SELECT_SINGLE})
        grid.add_action(self.request, ActionsManage.get_act_changed("Individual", "add", _("Add"), "images/add.png"), {'modal':FORMTYPE_MODAL, 'close':CLOSE_NO})
        self.add_component(grid)

@ActionsManage.affect('Responsability', 'edit')
@MenuManage.describ('contacts.change_responsability')
class ResponsabilityModify(XferAddEditor):
    # pylint: disable=too-many-public-methods
    caption = _("Modify responsability")
    icon = "function.png"
    model = Responsability
    field_id = 'responsability_set'

@ActionsManage.affect('Responsability', 'del')
@MenuManage.describ('contacts.delete_responsability')
class ResponsabilityDel(XferDelete):
    # pylint: disable=too-many-public-methods
    caption = _("Delete responsability")
    icon = "function.png"
    model = Responsability
    field_id = 'responsability_set'

@MenuManage.describ('contacts.change_individual', FORMTYPE_NOMODAL, 'contact.actions', _('To find an individual following a set of criteria.'))
class IndividualSearch(XferSearchEditor):
    caption = _("Individual search")
    icon = "individualFind.png"
    model = Individual
    field_id = 'individual'

@MenuManage.describ('contacts.change_individual', FORMTYPE_NOMODAL, 'contact.actions', _('To find a legal entity following a set of criteria.'))
class LegalEntitySearch(XferSearchEditor):
    caption = _("Legal entity search")
    icon = "legalEntityFind.png"
    model = LegalEntity
    field_id = 'legal_entity'
