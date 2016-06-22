# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from copy import deepcopy

from django.utils.translation import ugettext_lazy as _

from lucterios.framework.xferadvance import XferListEditor, TITLE_EDIT, TITLE_ADD, TITLE_MODIFY, TITLE_DELETE, TITLE_CLONE,\
    XferTransition
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.xferadvance import XferShowEditor
from lucterios.framework.xferadvance import XferDelete
from lucterios.framework.tools import FORMTYPE_NOMODAL, ActionsManage, MenuManage, SELECT_SINGLE, CLOSE_YES, SELECT_MULTI
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.CORE.xferprint import XferPrintReporting

from lucterios.contacts.tools import ContactSelection

from lucterios.mailing.functions import will_mail_send
from lucterios.mailing.models import Message

MenuManage.add_sub("mailing.actions", "office", "lucterios.mailing/images/mailing.png",
                   _("Mailing"), _("Create and send mailing to contacts."), 60)


@MenuManage.describ('mailing.change_message', FORMTYPE_NOMODAL, 'mailing.actions', _('Manage list of message for mailing.'))
class MessageList(XferListEditor):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Messages")


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


@ActionsManage.affect_transition("status")
@MenuManage.describ('mailing.add_message')
class MessageTransition(XferTransition):
    icon = "mailing.png"
    model = Message
    field_id = 'message'


@ActionsManage.affect_show(_("Letters"), "lucterios.mailing/images/letter.png", condition=lambda xfer: xfer.item.status == 1)
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


@ActionsManage.affect_show(_("Emails"), "lucterios.mailing/images/email.png", condition=lambda xfer: (xfer.item.status == 1) and will_mail_send())
@MenuManage.describ('mailing.add_message')
class MessageEmail(XferContainerAcknowledge):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Send message")

    def fillresponse(self):
        if self.confirme(_("Do you want to sent this message?")):
            nb_sent, nb_failed = self.item.send_email()
            self.message(
                _("Message sent to %(nbsent)d contact.{[br/]}Failure to %(nbfailed)d contacts.") % {'nbsent': nb_sent, 'nbfailed': nb_failed})


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
