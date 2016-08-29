# -*- coding: utf-8 -*-
'''
Describe database model for Django

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
from os import unlink
from os.path import exists

from django.utils import six
from django.utils.translation import ugettext_lazy as _

from lucterios.framework.filetools import save_from_base64, get_user_path, open_image_resize, readimage_to_base64
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompEdit, XferCompFloat, XferCompCheck, XferCompSelect, \
    XferCompMemo, XferCompUpLoad, XferCompImage, XferCompButton, XferCompLinkLabel
from lucterios.framework.tools import FORMTYPE_REFRESH, FORMTYPE_MODAL, CLOSE_NO, CLOSE_YES, get_icon_path, WrapAction
from lucterios.framework.tools import ActionsManage
from lucterios.framework.editors import LucteriosEditor

from lucterios.contacts.models import AbstractContact, PostalCode
from lucterios.CORE.parameters import Params
from lucterios.framework.models import get_value_converted
from lucterios.framework import signal_and_lock
from lucterios.CORE.views import ObjectPromote


class CustomFieldEditor(LucteriosEditor):

    def _edit_add_args(self, xfer, obj_kind):
        args = self.item.get_args()
        lbl = XferCompLabelForm('lbl_args_multi')
        lbl.set_value_as_name(_('multi-line'))
        lbl.set_location(obj_kind.col - 1, obj_kind.row + 1, 1, 1)
        xfer.add_component(lbl)
        arg = XferCompCheck('args_multi')
        arg.set_value(args['multi'])
        arg.set_location(obj_kind.col, obj_kind.row + 1, obj_kind.colspan, 1)
        xfer.add_component(arg)
        lbl = XferCompLabelForm('lbl_args_min')
        lbl.set_value_as_name(_('min'))
        lbl.set_location(obj_kind.col - 1, obj_kind.row + 2, 1, 1)
        xfer.add_component(lbl)
        arg = XferCompFloat('args_min', -10000, -10000, 0)
        arg.set_value(args['min'])
        arg.set_location(obj_kind.col, obj_kind.row + 2, obj_kind.colspan, 1)
        xfer.add_component(arg)
        lbl = XferCompLabelForm('lbl_args_max')
        lbl.set_value_as_name(_('max'))
        lbl.set_location(obj_kind.col - 1, obj_kind.row + 3, 1, 1)
        xfer.add_component(lbl)
        arg = XferCompFloat('args_max', -10000, -10000, 0)
        arg.set_value(args['max'])
        arg.set_location(obj_kind.col, obj_kind.row + 3, obj_kind.colspan, 1)
        xfer.add_component(arg)
        lbl = XferCompLabelForm('lbl_args_prec')
        lbl.set_value_as_name(_('precision'))
        lbl.set_location(obj_kind.col - 1, obj_kind.row + 4, 1, 1)
        xfer.add_component(lbl)
        arg = XferCompFloat('args_prec', 0, 10, 0)
        arg.set_value(args['prec'])
        arg.set_location(obj_kind.col, obj_kind.row + 4, obj_kind.colspan, 1)
        xfer.add_component(arg)
        lbl = XferCompLabelForm('lbl_args_list')
        lbl.set_value_as_name(_('list'))
        lbl.set_location(obj_kind.col - 1, obj_kind.row + 5, 1, 1)
        xfer.add_component(lbl)
        arg = XferCompEdit('args_list')
        arg.set_value(','.join(args['list']))
        arg.set_location(obj_kind.col, obj_kind.row + 5, obj_kind.colspan, 1)
        xfer.add_component(arg)

    def edit(self, xfer):
        obj_model = xfer.get_components('modelname')
        obj_kind = xfer.get_components('kind')
        xfer.remove_component('modelname')
        model_current = obj_model.value
        xfer.tab = obj_model.tab
        model_select = XferCompSelect('modelname')
        model_select.set_value(model_current)
        model_select.set_select(AbstractContact.get_select_contact_type())
        model_select.set_location(obj_model.col, obj_model.row, obj_model.colspan, obj_model.rowspan)
        model_select.set_size(obj_model.vmin, obj_model.hmin)
        xfer.add_component(model_select)
        self._edit_add_args(xfer, obj_kind)
        obj_kind.java_script = """
var type=current.getValue();
parent.get('lbl_args_multi').setVisible(type==0);
parent.get('lbl_args_min').setVisible(type==1 || type==2);
parent.get('lbl_args_max').setVisible(type==1 || type==2);
parent.get('lbl_args_prec').setVisible(type==2);
parent.get('lbl_args_list').setVisible(type==4);
parent.get('args_multi').setVisible(type==0);
parent.get('args_min').setVisible(type==1 || type==2);
parent.get('args_max').setVisible(type==1 || type==2);
parent.get('args_prec').setVisible(type==2);
parent.get('args_list').setVisible(type==4);
"""

    def saving(self, xfer):
        args = {}
        for arg_name in ['min', 'max', 'prec', 'list', 'multi']:
            args_val = xfer.getparam('args_' + arg_name)
            if args_val is not None:
                if arg_name == 'list':
                    args[arg_name] = args_val
                elif arg_name == 'multi':
                    args[arg_name] = (args_val != 'False') and (
                        args_val != '0') and (args_val != '') and (args_val != 'n')
                else:
                    args[arg_name] = float(args_val)
        self.item.args = six.text_type(args)
        LucteriosEditor.saving(self, xfer)
        self.item.save()

    def get_comp(self, value):
        comp = None
        args = self.item.get_args()
        if self.item.kind == 0:
            if args['multi']:
                comp = XferCompMemo(self.item.get_fieldname())
            else:
                comp = XferCompEdit(self.item.get_fieldname())
            comp.set_value(value)
        elif (self.item.kind == 1) or (self.item.kind == 2):
            comp = XferCompFloat(
                self.item.get_fieldname(), args['min'], args['max'], args['prec'])
            comp.set_value(value)
        elif self.item.kind == 3:
            comp = XferCompCheck(self.item.get_fieldname())
            comp.set_value(value)
        elif self.item.kind == 4:
            val_selected = value
            select_id = 0
            select_list = []
            for sel_item in args['list']:
                if sel_item == val_selected:
                    select_id = len(select_list)
                select_list.append((len(select_list), sel_item))
            comp = XferCompSelect(self.item.get_fieldname())
            comp.set_select(select_list)
            comp.set_value(select_id)
        return comp


class AbstractContactEditor(LucteriosEditor):

    def _change_city_select(self, xfer, list_postalcode, obj_city):

        obj_country = xfer.get_components('country')
        city_current = obj_city.value
        city_list = {}
        obj_country.value = ""
        for item_postalcode in list_postalcode:
            city_list[item_postalcode.city] = item_postalcode.city
            if item_postalcode.city == city_current:
                obj_country.value = item_postalcode.country
        if obj_country.value == "":
            obj_country.value = list_postalcode[0].country
            city_current = list_postalcode[0].city
        xfer.remove_component('city')
        xfer.tab = obj_city.tab
        city_select = XferCompSelect('city')
        city_select.set_value(city_current)
        city_select.set_select(city_list)
        city_select.set_location(
            obj_city.col, obj_city.row, obj_city.colspan, obj_city.rowspan)
        city_select.set_size(obj_city.vmin, obj_city.hmin)
        city_select.set_action(xfer.request, xfer.get_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        xfer.add_component(city_select)

    def _edit_custom_field(self, xfer, init_col):

        col = init_col
        col_offset = 0
        row = xfer.get_max_row() + 5
        for cf_name, cf_model in self.item.get_custom_fields():
            lbl = XferCompLabelForm('lbl_' + cf_name)
            lbl.set_location(col + col_offset, row, 1, 1)
            lbl.set_value_as_name(cf_model.name)
            xfer.add_component(lbl)
            comp = cf_model.editor.get_comp(getattr(self.item, cf_name))
            comp.set_location(col + col_offset + 1, row, 1, 1)
            xfer.add_component(comp)
            col_offset += 2
            if col_offset == 4:
                col_offset = 0
                row += 1

    def edit(self, xfer):
        obj_pstcd = xfer.get_components('postal_code')
        obj_pstcd.set_action(xfer.request, xfer.get_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        obj_city = xfer.get_components('city')
        postalcode_current = obj_pstcd.value
        list_postalcode = PostalCode.objects.filter(
            postal_code=postalcode_current)
        if len(list_postalcode) > 0:
            self._change_city_select(xfer, list_postalcode, obj_city)
        obj_cmt = xfer.get_components('comment')
        xfer.tab = obj_cmt.tab
        self._edit_custom_field(xfer, obj_cmt.col - 1)
        row = xfer.get_max_row()
        lbl = XferCompLabelForm('lbl_uploadlogo')
        lbl.set_value_as_name(_('image'))
        lbl.set_location(obj_cmt.col - 1, row + 10, 1, 1)
        xfer.add_component(lbl)
        upload = XferCompUpLoad('uploadlogo')
        upload.set_value('')
        upload.add_filter('.jpg')
        upload.add_filter('.gif')
        upload.add_filter('.png')
        upload.add_filter('.bmp')
        upload.set_location(obj_cmt.col, row + 10, obj_cmt.colspan, 1)
        xfer.add_component(upload)
        return

    def _show_custom_field(self, xfer, init_col):
        col = init_col
        col_offset = 0
        row = xfer.get_max_row() + 5
        for cf_name, cf_model in self.item.get_custom_fields():
            lbl = XferCompLabelForm('lbl_' + cf_name)
            lbl.set_location(col + col_offset, row, 1, 1)
            lbl.set_value_as_name(cf_model.name)
            xfer.add_component(lbl)
            val = XferCompLabelForm(cf_name)
            val.set_location(col + col_offset + 1, row, 1, 1)
            val.set_value(
                get_value_converted(getattr(self.item, cf_name), True))
            xfer.add_component(val)
            col_offset += 2
            if col_offset == 4:
                col_offset = 0
                row += 1

    def show(self, xfer):
        LucteriosEditor.show(self, xfer)
        obj_addr = xfer.get_components('lbl_address')
        xfer.tab = obj_addr.tab
        new_col = obj_addr.col
        xfer.move(obj_addr.tab, 1, 0)
        img_path = get_user_path(
            "contacts", "Image_%s.jpg" % self.item.abstractcontact_ptr_id)
        img = XferCompImage('logoimg')
        if exists(img_path):
            img.type = 'jpg'
            img.set_value(readimage_to_base64(img_path))
        else:
            img.set_value(get_icon_path("lucterios.contacts/images/NoImage.png"))
        img.set_location(new_col, obj_addr.row, 1, 6)
        xfer.add_component(img)
        self._show_custom_field(xfer, obj_addr.col)
        if WrapAction.is_permission(xfer.request, 'contacts.add_abstractcontact'):
            if (len(self.item.__class__.get_select_contact_type(False)) > 0):
                btn = XferCompButton('btn_promote')
                btn.set_location(new_col + 1, xfer.get_max_row() + 1, 4)
                btn.set_action(xfer.request, ObjectPromote.get_action(_('Promote'), "images/config.png"), modal=FORMTYPE_MODAL,
                               close=CLOSE_YES, params={'modelname': xfer.model.get_long_name(), 'field_id': xfer.field_id})
                xfer.add_component(btn)
        signal_and_lock.Signal.call_signal("show_contact", self.item, xfer)

    def saving(self, xfer):
        uploadlogo = xfer.getparam('uploadlogo')
        if uploadlogo is not None:
            tmp_file = save_from_base64(uploadlogo)
            with open(tmp_file, "rb") as image_tmp:
                image = open_image_resize(image_tmp, 100, 100)
                img_path = get_user_path(
                    "contacts", "Image_%s.jpg" % self.item.abstractcontact_ptr_id)
                with open(img_path, "wb") as image_file:
                    image.save(image_file, 'JPEG', quality=90)
            unlink(tmp_file)
        LucteriosEditor.saving(self, xfer)
        self.item.set_custom_values(xfer.params)

    def add_email_selector(self, xfer, col, row, colspan):
        contacts_list = xfer.items.exclude(email__isnull=True).exclude(email__exact='')
        if len(contacts_list) < 100:
            mailto_type = Params.getvalue("contacts-mailtoconfig")
            email_list = []
            for item in contacts_list:
                email_list.append(six.text_type(item.email))
            if len(email_list) > 0:
                link = XferCompLinkLabel('emailAll')
                link.set_value_center(_('Write to all'))
                if mailto_type == 1:  # CC
                    mailto_prefix = 'mailto:?cc='
                elif mailto_type == 2:  # BCC
                    mailto_prefix = 'mailto:?bcc='
                else:  # TO
                    mailto_prefix = 'mailto:'
                link.set_link(mailto_prefix + ','.join(email_list))
                link.set_location(col, row, colspan)
                xfer.add_component(link)


class LegalEntityEditor(AbstractContactEditor):

    def edit(self, xfer):
        if self.item.id == 1:
            xfer.remove_component('lbl_structure_type')
            xfer.remove_component('structure_type')
        return AbstractContactEditor.edit(self, xfer)

    def show(self, xfer):
        if self.item.id == 1:
            xfer.remove_component('lbl_structure_type')
            xfer.remove_component('structure_type')
        AbstractContactEditor.show(self, xfer)


class IndividualEditor(AbstractContactEditor):

    def show(self, xfer):
        AbstractContactEditor.show(self, xfer)
        obj_user = xfer.get_components('user')
        obj_user.colspan = 2
        xfer.tab = obj_user.tab
        btn = XferCompButton('userbtn')
        btn.is_mini = True
        btn.set_location(obj_user.col + 2, obj_user.row, 1, 1)
        if self.item.user is None:
            act = ActionsManage.get_action_url('CORE.LucteriosUser', 'UserAdd', xfer)
            act.set_value("", "images/add.png")
            btn.set_action(xfer.request, act, modal=FORMTYPE_MODAL, close=CLOSE_NO)
        else:
            act = ActionsManage.get_action_url('CORE.LucteriosUser', 'Edit', xfer)
            act.set_value("", "images/edit.png")
            btn.set_action(xfer.request, act, modal=FORMTYPE_MODAL, close=CLOSE_NO,
                           params={'user_actif': six.text_type(self.item.user.id), 'IDENT_READ': 'YES'})
        xfer.add_component(btn)

    def saving(self, xfer):
        AbstractContactEditor.saving(self, xfer)
        if self.item.user is not None:
            self.item.user.first_name = self.item.firstname
            self.item.user.last_name = self.item.lastname
            self.item.user.email = self.item.email
            self.item.user.save()


class ResponsabilityEditor(LucteriosEditor):

    def edit(self, xfer):
        xfer.change_to_readonly('legal_entity')
        xfer.change_to_readonly('individual')
