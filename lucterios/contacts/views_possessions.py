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

from lucterios.framework.tools import MenuManage, FORMTYPE_MODAL, ActionsManage, SELECT_SINGLE,\
    FORMTYPE_NOMODAL, CLOSE_YES, SELECT_MULTI, CLOSE_NO, WrapAction
from lucterios.framework.xferadvance import XferListEditor, XferAddEditor, TITLE_ADD, TITLE_MODIFY,\
    TITLE_CREATE, TITLE_EDIT, XferShowEditor, TITLE_DELETE, XferDelete


from lucterios.contacts.models import CustomField, CategoryPossession,\
    AbstractContact, Possession
from lucterios.CORE.editors import XferSavedCriteriaSearchEditor
from lucterios.contacts.tools import ContactSelection
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework import signal_and_lock
from lucterios.framework.xfercomponents import XferCompGrid
from lucterios.framework.error import LucteriosException, IMPORTANT

MenuManage.add_sub("contact.possessions", "office", "lucterios.contacts/images/contacts.png",
                   _("Possessions"), _("Management of things, living or inanimate, possessed by contacts."), 51)


@MenuManage.describ('CORE.change_parameter', FORMTYPE_MODAL, 'contact.conf', _('Configure and manage possessions.'))
class ConfPossession(XferListEditor):
    caption = _("Possession configuration")
    icon = "possession.png"
    model = CategoryPossession
    field_id = 'category_possession'

    def fillresponse_header(self):
        self.params['basic_model'] = 'contacts.Possession'
        self.new_tab(_('Categories'))

    def fillresponse(self, show_only_enabled_bank=True):
        XferListEditor.fillresponse(self)
        self.new_tab(_("Possession Custom field"))
        self.fill_grid(0, CustomField, "custom_field", CustomField.get_filter(Possession))
        grid_custom = self.get_components('custom_field')
        grid_custom.delete_header('model_title')


@ActionsManage.affect_grid(TITLE_ADD, "images/add.png")
@ActionsManage.affect_grid(TITLE_MODIFY, "images/edit.png", unique=SELECT_SINGLE)
@MenuManage.describ('contacts.add_possession')
class CategoryAddModify(XferAddEditor):
    icon = "possession.png"
    model = CategoryPossession
    field_id = 'category_possession'
    caption_add = _("Add category")
    caption_modify = _("Modify category")


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_MULTI)
@MenuManage.describ('contacts.delete_possession')
class CategoryDel(XferDelete):
    icon = "possession.png"
    model = CategoryPossession
    field_id = 'category_possession'
    caption = _("Delete category")


def right_to_possession_list(request):
    if WrapAction(caption='', icon_path='', is_view_right='contacts.change_possession').check_permission(request):
        return CategoryPossession.objects.all().count() > 0
    else:
        return False


@MenuManage.describ(right_to_possession_list, FORMTYPE_NOMODAL, "contact.possessions", _('Management of possession list'))
class PossessionList(XferListEditor):
    icon = "possession.png"
    model = Possession
    field_id = 'possession'
    caption = _("Possession")


@MenuManage.describ(right_to_possession_list, FORMTYPE_NOMODAL, "contact.possessions", _('To find a possession following a set of criteria.'))
class PossessionSearch(XferSavedCriteriaSearchEditor):
    icon = "possession.png"
    model = Possession
    field_id = 'possession'
    caption = _("Search possession")


def owner_to_possession(request):
    if hasattr(request, "owner_id"):
        owner = AbstractContact.objects.get(id=getattr(request, "owner_id")).get_final_child()
        return hasattr(owner, "user") and (owner.user_id == request.user.id)
    elif "owner" in request.GET:
        owner = AbstractContact.objects.get(id=request.GET["owner"]).get_final_child()
        return hasattr(owner, "user") and (owner.user_id == request.user.id)
    elif "owner" in request.POST:
        owner = AbstractContact.objects.get(id=request.POST["owner"]).get_final_child()
        return hasattr(owner, "user") and (owner.user_id == request.user.id)
    else:
        return False


def right_to_possession_addmodify(request):
    if WrapAction(caption='', icon_path='', is_view_right='contacts.add_possession').check_permission(request):
        return True
    else:
        return owner_to_possession(request)


@ActionsManage.affect_grid(TITLE_CREATE, "images/new.png")
@ActionsManage.affect_show(TITLE_MODIFY, "images/edit.png", close=CLOSE_YES)
@MenuManage.describ(right_to_possession_addmodify)
class PossessionAddModify(XferAddEditor):
    icon = "possession.png"
    model = Possession
    field_id = 'possession'
    caption_add = _("Add possession")
    caption_modify = _("Modify possession")

    def fill_simple_fields(self):
        owner_id = self.getparam('owner', 0)
        if (owner_id != 0) and (self.item.id is not None) and (self.item.owner_id != owner_id):
            raise LucteriosException(IMPORTANT, _("Bad permission for '%s'") % self.request.user)
        XferAddEditor.fill_simple_fields(self)


def right_to_possession_show(request):
    if WrapAction(caption='', icon_path='', is_view_right='contacts.change_possession').check_permission(request):
        return True
    else:
        return owner_to_possession(request)


@ActionsManage.affect_grid(TITLE_EDIT, "images/show.png", unique=SELECT_SINGLE)
@MenuManage.describ(right_to_possession_show)
class PossessionShow(XferShowEditor):
    caption = _("Show possession")
    icon = "possession.png"
    model = Possession
    field_id = 'possession'

    def clear_fields_in_params(self):
        owner_id = self.getparam('owner', 0)
        if (owner_id != 0) and (self.item.owner_id != owner_id):
            raise LucteriosException(IMPORTANT, _("Bad permission for '%s'") % self.request.user)
        XferShowEditor.clear_fields_in_params(self)

    def fillresponse(self):
        XferShowEditor.fillresponse(self)
        if not self.getparam('mng_owner', True):
            add_action_id = -1
            for action_id in range(len(self.actions)):
                if self.actions[action_id][0].url_text == 'lucterios.contacts/possessionAddModify':
                    add_action_id = action_id
                    break
            if add_action_id != -1:
                action = self.actions[action_id]
                self.actions[action_id] = (action[0], action[1], action[2], action[3], {'mng_owner': False, 'owner': self.item.owner_id})


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_MULTI)
@MenuManage.describ('contacts.delete_possession')
class PossessionDel(XferDelete):
    icon = "possession.png"
    model = Possession
    field_id = 'possession'
    caption = _("Delete possession")


@MenuManage.describ('contacts.add_possession')
class PossessionOwnerSave(XferContainerAcknowledge):
    icon = "possession.png"
    model = Possession
    field_id = 'possession'

    def fillresponse(self, pkname=''):
        self.item.owner_id = self.getparam(pkname)
        self.item.save()


@ActionsManage.affect_other(TITLE_EDIT, "images/edit.png", close=CLOSE_NO)
@MenuManage.describ('contacts.add_possession')
class PossessionOwner(ContactSelection):
    icon = "possession.png"
    model = Possession
    select_class = PossessionOwnerSave
    field_id = 'possession'
    caption = _("Change owner to possession")


@signal_and_lock.Signal.decorate('show_contact')
def show_contact_possession(contact, xfer):
    if CategoryPossession.objects.all().count() > 0:
        xfer.new_tab(_("Possessions"))
        xfer.params['mng_owner'] = False
        xfer.params['owner'] = contact.id
        xfer.request.owner_id = contact.id
        possession_grid = XferCompGrid('possession')
        possession_grid.set_model(Possession.objects.filter(owner=contact).distinct(), Possession.get_other_fields(), xfer)
        possession_grid.add_action_notified(xfer, Possession)
        possession_grid.set_location(0, 3, 2)
        xfer.add_component(possession_grid)
