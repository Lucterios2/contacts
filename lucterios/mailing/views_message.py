# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from lucterios.mailing.models import Message

from lucterios.framework.xferadvance import XferListEditor
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.xferadvance import XferShowEditor
from lucterios.framework.xferadvance import XferDelete
from lucterios.framework.tools import FORMTYPE_NOMODAL, ActionsManage, MenuManage, CLOSE_NO,\
    SELECT_SINGLE, FORMTYPE_MODAL
from lucterios.contacts.tools import ContactSelection
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.mailing.functions import will_mail_send
from lucterios.CORE.xferprint import XferPrintReporting
from copy import deepcopy

MenuManage.add_sub("mailing.actions", "office", "lucterios.mailing/images/mailing.png",
                   _("Mailing"), _("Create and send mailing to contacts."), 60)


@ActionsManage.affect('Message', 'list')
@MenuManage.describ('mailing.change_message', FORMTYPE_NOMODAL, 'mailing.actions', _('Manage list of message for mailing.'))
class MessageList(XferListEditor):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Messages")

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        grid = self.get_components(self.field_id)
        grid.add_action(self.request, MessageClone.get_action(_("clone"), "images/clone.png"),
                        {'modal': FORMTYPE_MODAL, 'close': CLOSE_NO, 'unique': SELECT_SINGLE})


@ActionsManage.affect('Message', 'modify', 'add')
@MenuManage.describ('mailing.add_message')
class MessageAddModify(XferAddEditor):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption_add = _("Add message")
    caption_modify = _("Modify message")


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
        self.redirect_action(ActionsManage.get_act_changed(
            self.model.__name__, 'show', '', ''), {'params': {self.field_id: self.item.id}})


@ActionsManage.affect('Message', 'show')
@MenuManage.describ('mailing.change_message')
class MessageShow(XferShowEditor):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Show message")

    def fillresponse(self):
        if (self.item.status == 0) and (self.item.recipients != ''):
            self.action_list.insert(
                0, (('valid', _("Valid"), "images/ok.png", CLOSE_NO)))
        if self.item.status == 1:
            self.action_list = []
            self.action_list.append(
                ('letter', _("Letters"), "lucterios.mailing/images/letter.png", CLOSE_NO))
            if will_mail_send():
                self.action_list.append(
                    ('email', _("Emails"), "lucterios.mailing/images/email.png", CLOSE_NO))
        XferShowEditor.fillresponse(self)


@ActionsManage.affect('Message', 'valid')
@MenuManage.describ('mailing.add_message')
class MessageValid(XferContainerAcknowledge):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Valid message")

    def fillresponse(self):
        if self.confirme(_("Do you want to close this message?")):
            self.item.valid()


@ActionsManage.affect('Message', 'letter')
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


@ActionsManage.affect('Message', 'email')
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


@ActionsManage.affect('Message', 'delete')
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


@ActionsManage.affect('Message', 'add_recipients')
@MenuManage.describ('mailing.add_message')
class MessageAddRecipient(ContactSelection):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Add recipient to message")
    final_class = MessageValidRecipient


@ActionsManage.affect('Message', 'del_recipients')
@MenuManage.describ('mailing.add_message')
class MessageDelRecipient(XferContainerAcknowledge):
    icon = "mailing.png"
    model = Message
    field_id = 'message'
    caption = _("Delete recipient")

    def fillresponse(self, recipient_list=-1):
        if self.confirme(_("Do you want to delete this recipient?")):
            self.item.del_recipient(recipient_list)
