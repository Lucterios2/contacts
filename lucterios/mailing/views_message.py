# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from copy import deepcopy

from django.utils.translation import ugettext_lazy as _

from lucterios.framework.xferadvance import XferListEditor, TITLE_EDIT, TITLE_ADD, TITLE_MODIFY, TITLE_DELETE, TITLE_CLONE,\
    XferTransition
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.xferadvance import XferShowEditor
from lucterios.framework.xferadvance import XferDelete
from lucterios.framework.tools import FORMTYPE_NOMODAL, ActionsManage, MenuManage, SELECT_SINGLE, CLOSE_YES, SELECT_MULTI,\
    get_icon_path, FORMTYPE_REFRESH, WrapAction, CLOSE_NO
from lucterios.framework.xfergraphic import XferContainerAcknowledge,\
    XferContainerCustom
from lucterios.CORE.xferprint import XferPrintReporting

from lucterios.contacts.tools import ContactSelection

from lucterios.mailing.models import Message, add_mailing_in_scheduler
from lucterios.framework.xfercomponents import XferCompImage, XferCompLabelForm, XferCompCheck
from lucterios.documents.models import Document
from lucterios.documents.views import DocumentSearch

MenuManage.add_sub("mailing.actions", "office", "lucterios.mailing/images/mailing.png",
                   _("Mailing"), _("Create and send mailing to contacts."), 60)


@MenuManage.describ('mailing.change_message', FORMTYPE_NOMODAL, 'mailing.actions', _('Manage list of message for mailing.'))
class MessageList(XferListEditor):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Messages")

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        add_mailing_in_scheduler(check_nb=True)


@ActionsManage.affect_grid(TITLE_ADD, "images/add.png")
@ActionsManage.affect_show(TITLE_MODIFY, "images/edit.png", close=CLOSE_YES, condition=lambda xfer: xfer.item.status == 0)
@MenuManage.describ('mailing.add_message')
class MessageAddModify(XferAddEditor):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption_add = _("Add message")
    caption_modify = _("Modify message")


@ActionsManage.affect_grid(TITLE_CLONE, "images/clone.png", unique=SELECT_SINGLE)
@MenuManage.describ('mailing.add_message')
class MessageClone(XferContainerAcknowledge):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Add message")

    def fillresponse(self):
        self.item.id = None
        self.item.date = None
        self.item.status = 0
        self.item.save()
        self.redirect_action(MessageShow.get_action('', ''), {'params': {self.field_id: self.item.id}})


@ActionsManage.affect_grid(TITLE_EDIT, "images/show.png", unique=SELECT_SINGLE)
@MenuManage.describ('mailing.change_message')
class MessageShow(XferShowEditor):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Show message")

    def fillresponse(self):
        XferShowEditor.fillresponse(self)
        for action, _modal, _close, _select, params in self.actions:
            if (action.url_text == 'lucterios.mailing/messageTransition') and ('TRANSITION' in params) and (params['TRANSITION'] == 'sending'):
                action.icon_path = get_icon_path("mailing.png", action.url_text)


@ActionsManage.affect_transition("status")
@MenuManage.describ('mailing.add_message')
class MessageTransition(XferTransition):
    icon = "mailing.png"
    model = Message
    field_id = 'message'

    def fill_confirm(self, transition, trans):
        if transition == 'sending':
            if self.confirme(_("Do you want to sent this message to %d contacts?") % len(self.item.get_contacts(True))):
                self._confirmed(transition)
                self.message(_("This message is being transmitted"))
        else:
            XferTransition.fill_confirm(self, transition, trans)


@ActionsManage.affect_show(_("Info"), "images/info.png", modal=FORMTYPE_NOMODAL, condition=lambda xfer: xfer.item.emailsent_set.count() > 0)
@MenuManage.describ('mailing.change_message')
class MessageSentInfo(XferContainerCustom):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Transmission report")

    def fillresponse(self, show_only_failed=False):
        img = XferCompImage('img')
        img.set_value(self.icon_path())
        img.set_location(0, 0, 1, 6)
        self.add_component(img)
        begin = XferCompLabelForm('title')
        begin.set_location(1, 0, 2)
        begin.set_value_as_title(_('Transmission report'))
        self.add_component(begin)

        self.filltab_from_model(1, 1, True, [((_('date begin of send'), 'date_begin'), (_('date end of send'), 'date_end')), ('emailsent_set',)])
        if not show_only_failed:
            grid = self.get_components('emailsent')
            grid.delete_header('error')

        check = XferCompCheck('show_only_failed')
        check.set_value(show_only_failed)
        check.description = _('Show only failed')
        check.set_location(1, 3, 2)
        check.set_action(self.request, self.get_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(check)

        show_only_failed
        self.add_action(WrapAction(_('Close'), 'images/close.png'))


@ActionsManage.affect_show(_("Letters"), "letter.png", condition=lambda xfer: xfer.item.status == 1)
@MenuManage.describ('mailing.add_message')
class MessageLetter(XferPrintReporting):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Write message")

    def items_callback(self):
        items = []
        for current_contact in self.item.get_contacts():
            new_item = deepcopy(self.item)
            new_item.contact = current_contact
            items.append(new_item)
        return items


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_MULTI)
@MenuManage.describ('mailing.delete_message')
class MessageDel(XferDelete):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Delete message")


@MenuManage.describ('mailing.add_message')
class MessageValidRecipient(XferContainerAcknowledge):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Add recipient to message")

    def fillresponse(self, modelname='', CRITERIA=''):
        self.item.add_recipient(modelname, CRITERIA)


@ActionsManage.affect_grid(TITLE_ADD, "images/add.png", model_name='recipient_list', condition=lambda xfer, gridname: xfer.item.status == 0)
@MenuManage.describ('mailing.add_message')
class MessageAddRecipient(ContactSelection):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Add recipient to message")
    final_class = MessageValidRecipient


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_SINGLE, model_name='recipient_list', condition=lambda xfer, gridname: xfer.item.status == 0)
@MenuManage.describ('mailing.add_message')
class MessageDelRecipient(XferContainerAcknowledge):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Delete recipient")

    def fillresponse(self, recipient_list=-1):
        if self.confirme(_("Do you want to delete this recipient?")):
            self.item.del_recipient(recipient_list)


@MenuManage.describ('mailing.add_message')
class MessageValidInsertDoc(XferContainerAcknowledge):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Insert document to message")

    def fillresponse(self, document=0):
        self.item.documents.add(Document.objects.get(id=document))


@MenuManage.describ('mailing.add_message')
class MessageInsertDoc(DocumentSearch):
    caption = _("Insert document to message")
    mode_select = SELECT_SINGLE
    select_class = MessageValidInsertDoc


@MenuManage.describ('mailing.add_message')
class MessageRemoveDoc(XferContainerAcknowledge):
    caption = _("Remove document to message")
    icon = "mailing.png"
    model = Message
    field_id = 'message'

    def fillresponse(self, document=[]):
        if self.confirme(_('Do you want to remove those documents ?')):
            for doc in Document.objects.filter(id__in=document):
                self.item.documents.remove(doc)
