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
from django.utils.translation import ugettext_lazy as _
from django.db import models
from lucterios.framework.models import LucteriosModel, PrintFieldsPlugIn
from lucterios.framework.filetools import save_from_base64, get_user_path, open_image_resize, readimage_to_base64
from posix import unlink
from django.utils import six
from lucterios.framework.tools import ActionsManage

class PostalCode(LucteriosModel):
    postal_code = models.CharField(_('postal code'), max_length=10, blank=False)
    city = models.CharField(_('city'), max_length=100, blank=False)
    country = models.CharField(_('country'), max_length=100, blank=False)

    postalcode__editfields = ['postal_code', 'city', 'country']
    postalcode__searchfields = ['postal_code', 'city', 'country']

    default_fields = ['postal_code', 'city', 'country']

    def __str__(self):
        return '[%s] %s %s' % (self.country, self.postal_code, self.city)

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('postal code')
        verbose_name_plural = _('postal codes')
        default_permissions = ['add', 'change']
        ordering = ['postal_code', 'city']
        unique_together = (('postal_code', 'city', 'country'),)

class Function(LucteriosModel):
    name = models.CharField(_('name'), max_length=50, unique=True)

    def __str__(self):
        return self.name

    function__editfields = ['name']
    function__searchfields = ['name']

    default_fields = ["name"]

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('individual function')
        verbose_name_plural = _('individual functions')
        default_permissions = []

class StructureType(LucteriosModel):
    name = models.CharField(_('name'), max_length=50, unique=True)

    structuretype__editfields = ['name']
    structuretype__searchfields = ['name']

    default_fields = ["name"]

    def __str__(self):
        return self.name

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('structure type')
        verbose_name_plural = _('structure types')
        default_permissions = []

class CustomField(LucteriosModel):
    modelname = models.CharField(_('model'), max_length=100)
    name = models.CharField(_('name'), max_length=100, unique=False)
    kind = models.IntegerField(_('kind'), choices=((0, _('String')), (1, _('Integer')), (2, _('Real')), (3, _('Boolean')), (4, _('Select'))))
    args = models.CharField(_('arguments'), max_length=200, default="{}")

    customfield__showfields = ['name', 'modelname', 'kind']
    customfield__editfields = ['name', 'modelname', 'kind']
    default_fields = ['name', (_('model'), 'model_title'), 'kind']

    def model_associated(self):
        from django.apps import apps
        return apps.get_model(self.modelname)

    def get_fieldname(self):
        return "custom_%d" % self.id  # pylint: disable=no-member

    @property
    def model_title(self):
        return six.text_type(self.model_associated()._meta.verbose_name)  # pylint: disable=protected-access

    def _edit_add_args(self, xfer, obj_kind):
        args = self.get_args()
        from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompFloat, XferCompEdit, XferCompCheck
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
        from lucterios.framework.xfercomponents import XferCompSelect
        obj_model = xfer.get_components('modelname')
        obj_kind = xfer.get_components('kind')
        xfer.remove_component('modelname')
        model_current = obj_model.value
        xfer.tab = obj_model.tab
        model_list = []
        model_list.append((AbstractContact.get_long_name(), AbstractContact._meta.verbose_name.title()))  # pylint: disable=protected-access,no-member
        for sub_class in AbstractContact.__subclasses__():  # pylint: disable=no-member
            model_list.append((sub_class.get_long_name(), sub_class._meta.verbose_name.title()))  # pylint: disable=protected-access,no-member
        model_select = XferCompSelect('modelname')
        model_select.set_value(model_current)
        model_select.set_select(model_list)
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
                if arg_name != 'list':
                    args[arg_name] = float(args_val)
                else:
                    args[arg_name] = args_val
        self.args = six.text_type(args)
        LucteriosModel.saving(self, xfer)
        self.save()

    def get_args(self):
        default_args = {'min':0, 'max':0, 'prec':0, 'list':[], 'multi':False}
        try:
            args = eval(self.args)  # pylint: disable=eval-used
        except:  # pylint: disable=bare-except
            args = {}
        for name, val in default_args.items():
            if not name in args.keys():
                args[name] = val
        args['list'] = list(args['list'])
        return args

    def get_field(self):
        from django.db.models.fields import IntegerField, DecimalField, BooleanField, TextField
        from django.core.validators import MaxValueValidator, MinValueValidator
        args = self.get_args()
        if self.kind == 0:
            dbfield = TextField(self.name)
        if self.kind == 1:
            dbfield = IntegerField(self.name, validators=[MinValueValidator(float(args['min'])), MaxValueValidator(float(args['max']))])
        if self.kind == 2:
            dbfield = DecimalField(self.name, decimal_places=int(args['prec']), validators=[MinValueValidator(float(args['min'])), MaxValueValidator(float(args['max']))])
        if self.kind == 3:
            dbfield = BooleanField(self.name)
        if self.kind == 4:
            choices = []
            for item in args['list']:
                choices.append((len(choices), item))
            dbfield = IntegerField(self.name, choices=tuple(choices))
        return dbfield

    def get_comp(self, value):

        from lucterios.framework.xfercomponents import XferCompEdit, XferCompFloat, XferCompCheck, XferCompSelect, XferCompMemo
        comp = None
        args = self.get_args()
        if self.kind == 0:
            if args['multi']:
                comp = XferCompMemo(self.get_fieldname())
            else:
                comp = XferCompEdit(self.get_fieldname())
            comp.set_value(value)
        elif (self.kind == 1) or (self.kind == 2):
            comp = XferCompFloat(self.get_fieldname(), args['min'], args['max'], args['prec'])
            comp.set_value(value)
        elif self.kind == 3:
            comp = XferCompCheck(self.get_fieldname())
            comp.set_value(value)
        elif self.kind == 4:
            val_selected = value
            select_id = 0
            select_list = []
            for sel_item in args['list']:
                if sel_item == val_selected:
                    select_id = len(select_list)
                select_list.append((len(select_list), sel_item))
            comp = XferCompSelect(self.get_fieldname())
            comp.set_select(select_list)
            comp.set_value(select_id)
        return comp

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('custom field')
        verbose_name_plural = _('custom fields')
        default_permissions = []

class ContactCustomField(LucteriosModel):
    contact = models.ForeignKey('AbstractContact', verbose_name=_('contact'), null=False, on_delete=models.CASCADE)
    field = models.ForeignKey('CustomField', verbose_name=_('field'), null=False, on_delete=models.CASCADE)
    value = models.TextField(_('value'), default="")

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('custom field value')
        verbose_name_plural = _('custom field values')
        default_permissions = []

class AbstractContact(LucteriosModel):
    address = models.TextField(_('address'), blank=False)
    postal_code = models.CharField(_('postal code'), max_length=10, blank=False)
    city = models.CharField(_('city'), max_length=100, blank=False)
    country = models.CharField(_('country'), max_length=100, blank=False)
    tel1 = models.CharField(_('tel1'), max_length=15, blank=True)
    tel2 = models.CharField(_('tel2'), max_length=15, blank=True)
    email = models.EmailField(_('email'), blank=True)
    comment = models.TextField(_('comment'), blank=True)

    abstractcontact__showfields = ['address', ('postal_code', 'city'), 'country', ('tel1', 'tel2'), 'email', 'comment']
    abstractcontact__editfields = ['address', ('postal_code', 'city'), 'country', ('tel1', 'tel2'), 'email', 'comment']
    abstractcontact__searchfields = ['address', 'postal_code', 'city', 'country', 'tel1', 'tel2', 'email', 'comment']

    def get_custom_fields(self):
        import inspect
        fields = []
        model_list = []
        for sub_class in inspect.getmro(self.__class__):
            if hasattr(sub_class, "get_long_name"):
                model_list.append(sub_class.get_long_name())
        for cf_model in CustomField.objects.filter(modelname__in=model_list):  # pylint: disable=no-member
            fields.append((cf_model.get_fieldname(), cf_model))
        return fields

    @classmethod
    def get_print_fields(cls, with_plugin=True):
        fields = super(AbstractContact, cls).get_print_fields(with_plugin)
        item = cls()
        for cf_name, cf_model in item.get_custom_fields():
            fields.append((cf_model.name, cf_name))
        return fields

    @classmethod
    def get_fieldnames_for_search(cls, is_topleve=True):
        fieldnames = super(AbstractContact, cls).get_fieldnames_for_search()
        if is_topleve:
            from django.db.models import Q
            for cf_name, cf_model in cls().get_custom_fields():
                fieldnames.append((cf_name, cf_model.get_field(), 'contactcustomfield__value', Q(contactcustomfield__field__id=cf_model.id)))
        return fieldnames

    def __getattr__(self, name):
        if name[:7] == "custom_":
            cf_id = int(name[7:])
            cf_model = CustomField.objects.get(id=cf_id)  # pylint: disable=no-member
            if self.id is None:
                ccf_value = ""
            else:
                ccf_model = ContactCustomField.objects.get_or_create(contact=self, field=cf_model)  # pylint: disable=no-member
                ccf_value = ccf_model[0].value
            if cf_model.kind == 0:
                return six.text_type(ccf_value)
            if ccf_value == '':
                ccf_value = '0'
            if cf_model.kind == 1:
                return int(ccf_value)
            if cf_model.kind == 2:
                return float(ccf_value)
            if cf_model.kind == 3:
                return (ccf_value != 'False') and (ccf_value != '0') and (ccf_value != '') and (ccf_value != 'n')
            if cf_model.kind == 4:
                num = int(ccf_value)
                args_list = cf_model.get_args()['list']
                if num < len(args_list):
                    return args_list[num]
                else:
                    return "---"
        raise AttributeError(name)

    def _change_city_select(self, xfer, list_postalcode, obj_city):
        # pylint: disable=no-self-use
        from lucterios.framework.tools import FORMTYPE_REFRESH, CLOSE_NO
        from lucterios.framework.xfercomponents import XferCompSelect
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
        city_select.set_location(obj_city.col, obj_city.row, obj_city.colspan, obj_city.rowspan)
        city_select.set_size(obj_city.vmin, obj_city.hmin)
        city_select.set_action(xfer.request, xfer, {'modal':FORMTYPE_REFRESH, 'close':CLOSE_NO})
        xfer.add_component(city_select)

    def _edit_custom_field(self, xfer, init_col):
        # pylint: disable=too-many-locals
        from lucterios.framework.xfercomponents import XferCompLabelForm
        col = init_col
        col_offset = 0
        row = xfer.get_max_row() + 5
        for cf_name, cf_model in self.get_custom_fields():
            lbl = XferCompLabelForm('lbl_' + cf_name)
            lbl.set_location(col + col_offset, row, 1, 1)
            lbl.set_value_as_name(cf_model.name)
            xfer.add_component(lbl)
            comp = cf_model.get_comp(getattr(self, cf_name))
            comp.set_location(col + col_offset + 1, row, 1, 1)
            xfer.add_component(comp)
            col_offset += 2
            if col_offset == 4:
                col_offset = 0
                row += 1

    def edit(self, xfer):
        from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompUpLoad
        from lucterios.framework.tools import FORMTYPE_REFRESH, CLOSE_NO

        obj_pstcd = xfer.get_components('postal_code')
        obj_pstcd.set_action(xfer.request, xfer, {'modal':FORMTYPE_REFRESH, 'close':CLOSE_NO})
        obj_city = xfer.get_components('city')
        postalcode_current = obj_pstcd.value
        list_postalcode = PostalCode.objects.filter(postal_code=postalcode_current)  # pylint: disable=no-member
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
        from lucterios.framework.xfercomponents import XferCompLabelForm
        col = init_col
        col_offset = 0
        row = xfer.get_max_row() + 5
        for cf_name, cf_model in self.get_custom_fields():
            lbl = XferCompLabelForm('lbl_' + cf_name)
            lbl.set_location(col + col_offset, row, 1, 1)
            lbl.set_value_as_name(cf_model.name)
            xfer.add_component(lbl)
            val = XferCompLabelForm(cf_name)
            val.set_location(col + col_offset + 1, row, 1, 1)
            val.set_value(getattr(self, cf_name))
            xfer.add_component(val)
            col_offset += 2
            if col_offset == 4:
                col_offset = 0
                row += 1

    def show(self, xfer):
        from lucterios.framework.xfercomponents import XferCompImage
        from os.path import exists
        LucteriosModel.show(self, xfer)
        obj_addr = xfer.get_components('lbl_address')
        xfer.tab = obj_addr.tab
        new_col = obj_addr.col
        xfer.move(obj_addr.tab, 1, 0)
        img_path = get_user_path("contacts", "Image_%s.jpg" % self.abstractcontact_ptr_id)  # pylint: disable=no-member
        img = XferCompImage('logoimg')
        if exists(img_path):
            img.type = 'jpg'
            img.set_value(readimage_to_base64(img_path))
        else:
            img.set_value("lucterios.contacts/images/NoImage.png")
        img.set_location(new_col, obj_addr.row, 1, 6)
        xfer.add_component(img)
        self._show_custom_field(xfer, obj_addr.col)

    def saving(self, xfer):
        uploadlogo = xfer.getparam('uploadlogo')
        if uploadlogo is not None:
            tmp_file = save_from_base64(uploadlogo)
            with open(tmp_file, "rb") as image_tmp:
                image = open_image_resize(image_tmp, 100, 100)
                img_path = get_user_path("contacts", "Image_%s.jpg" % self.abstractcontact_ptr_id)  # pylint: disable=no-member
                with open(img_path, "wb") as image_file:
                    image.save(image_file, 'JPEG', quality=90)
            unlink(tmp_file)
        LucteriosModel.saving(self, xfer)
        for cf_name, cf_model in self.get_custom_fields():
            cf_value = xfer.getparam(cf_name)
            if cf_value is not None:
                cf_id = int(cf_name[7:])
                cf_model = CustomField.objects.get(id=cf_id)  # pylint: disable=no-member
                ccf_model = ContactCustomField.objects.get_or_create(contact=self, field=cf_model)  # pylint: disable=no-member
                ccf_model[0].value = six.text_type(cf_value)
                ccf_model[0].save()

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('generic contact')
        verbose_name_plural = _('generic contacts')
        default_permissions = []

class LegalEntity(AbstractContact):
    name = models.CharField(_('name'), max_length=100, blank=False)
    structure_type = models.ForeignKey('StructureType', verbose_name=_('structure type'), null=True, on_delete=models.SET_NULL)
    identify_number = models.CharField(_('identify number'), max_length=100, blank=True)

    legalentity__showfields = {_('001@Identity'):['name', 'structure_type', None, 'identify_number'], _('002@Management'):['responsability_set']}
    legalentity__editfields = ['name', 'structure_type', None, 'identify_number']
    legalentity__searchfields = ['name', 'structure_type', None, 'identify_number', \
            'responsability_set.individual.firstname', 'responsability_set.individual.lastname', 'responsability_set.functions']
    default_fields = ["name", 'tel1', 'tel2', 'email']
    print_fields = ["name", 'structure_type', 'address', 'postal_code', 'city', 'country', 'tel1', 'tel2', \
                    'email', 'comment', 'identify_number', 'OUR_DETAIL']

    def __str__(self):
        return self.name

    def edit(self, xfer):
        if self.id == 1:  # pylint: disable=no-member
            xfer.remove_component('lbl_structure_type')
            xfer.remove_component('structure_type')
        return AbstractContact.edit(self, xfer)

    def show(self, xfer):
        if self.id == 1:  # pylint: disable=no-member
            xfer.remove_component('lbl_structure_type')
            xfer.remove_component('structure_type')
        return AbstractContact.show(self, xfer)

    def can_delete(self):
        msg = AbstractContact.can_delete(self)
        if msg == '':
            if self.id == 1:  # pylint: disable=no-member
                msg = _("You cannot delete this legal entity!")
        return msg

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('legal entity')
        verbose_name_plural = _('legal entities')

class Individual(AbstractContact):
    genre = models.IntegerField(choices=((1, _('Man')), (2, _('Woman'))), default=1, null=False)
    firstname = models.CharField(_('firstname'), max_length=50, blank=False)
    lastname = models.CharField(_('lastname'), max_length=50, blank=False)
    user = models.ForeignKey('CORE.LucteriosUser', verbose_name=_('user'), null=True, on_delete=models.SET_NULL)
    # 'functions'=>array('description'=>'Fonctions', 'type'=>11, 'notnull'=>false, 'params'=>array('Function'=>'org_lucterios_contacts_FCT_personnePhysique_APAS_getFunctions', 'NbField'=>2)));

    individual__showfields = {_('001@Identity'):['genre', ('firstname', 'lastname'), None, 'user']}
    individual__editfields = ['genre', ('firstname', 'lastname'), None]
    individual__searchfields = ['genre', 'firstname', 'lastname', None, 'user.username', \
                                'responsability_set.legal_entity.name', 'responsability_set.functions']
    default_fields = ["firstname", "lastname", 'tel1', 'tel2', 'email']
    print_fields = ["firstname", "lastname", 'address', 'postal_code', 'city', 'country', 'tel1', 'tel2', \
                    'email', 'comment', 'user', 'responsability_set', 'OUR_DETAIL']

    def __str__(self):
        return '%s %s' % (self.firstname, self.lastname)

    def show(self, xfer):
        from lucterios.framework.xfercomponents import XferCompButton
        from lucterios.framework.tools import FORMTYPE_MODAL, CLOSE_NO
        AbstractContact.show(self, xfer)
        obj_user = xfer.get_components('user')
        obj_user.colspan = 2
        btn = XferCompButton('userbtn')
        btn.is_mini = True
        btn.set_location(obj_user.col + 2, obj_user.row, 1, 1)
        if self.user is None:
            btn.set_action(xfer.request, ActionsManage.get_act_changed('Individual', 'useradd', "", 'images/add.png'), \
                    {'modal':FORMTYPE_MODAL, 'close':CLOSE_NO})
        else:
            btn.set_action(xfer.request, ActionsManage.get_act_changed('LucteriosUser', 'edit', '', 'images/edit.png'), \
                    {'modal':FORMTYPE_MODAL, 'close':CLOSE_NO, 'params':{'user_actif':six.text_type(self.user.id), 'IDENT_READ':'YES'}})  # pylint: disable=no-member
        xfer.add_component(btn)

    def saving(self, xfer):
        AbstractContact.saving(self, xfer)
        if self.user is not None:
            self.user.first_name = self.firstname
            self.user.last_name = self.lastname
            self.user.email = self.email
            self.user.save()  # pylint: disable=no-member

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('individual')
        verbose_name_plural = _('individuals')

class Responsability(LucteriosModel):
    individual = models.ForeignKey(Individual, verbose_name=_('individual'), null=False)
    legal_entity = models.ForeignKey(LegalEntity, verbose_name=_('legal entity'), null=False)
    functions = models.ManyToManyField(Function, verbose_name=_('functions'), blank=True)
    functions__titles = [_("Available functions"), _("Chosen functions")]

    responsability__editfields = ["legal_entity", "individual", "functions"]
    responsability__searchfields = ["legal_entity", "individual", "functions"]
    default_fields = ["individual", "functions"]
    print_fields = ["legal_entity", "functions"]

    def edit(self, xfer):
        xfer.change_to_readonly('legal_entity')
        xfer.change_to_readonly('individual')

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('responsability')
        verbose_name_plural = _('responsabilities')

class OurDetailPrintPlugin(PrintFieldsPlugIn):

    name = "OUR_DETAIL"
    title = _('our detail')

    def get_print_fields(self):
        fields = []
        for title, name in LegalEntity.get_print_fields(False):
            if (name[:14] != 'structure_type') and (name[:len(self.name)] != self.name):
                fields.append(("%s > %s" % (self.title, title), "%s.%s" % (self.name, name)))
        return fields

    def evaluate(self, text_to_evaluate):
        our_details = LegalEntity.objects.get(id=1)  # pylint: disable=no-member
        return our_details.evaluate(text_to_evaluate)

PrintFieldsPlugIn.add_plugin(OurDetailPrintPlugin)
