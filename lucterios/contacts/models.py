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
from os.path import exists, join, dirname
import logging

from django.utils import six
from django.utils.translation import ugettext_lazy as _
from django.db import models

from lucterios.framework.models import LucteriosModel, PrintFieldsPlugIn,\
    get_value_if_choices
from lucterios.framework.filetools import get_user_path, readimage_to_base64
from lucterios.framework.signal_and_lock import Signal
from lucterios.CORE.models import Parameter


class CustomField(LucteriosModel):
    modelname = models.CharField(_('model'), max_length=100)
    name = models.CharField(_('name'), max_length=200, unique=False)
    kind = models.IntegerField(_('kind'), choices=((0, _('String')), (1, _('Integer')), (2, _('Real')), (3, _('Boolean')), (4, _('Select'))))
    args = models.CharField(_('arguments'), max_length=200, default="{}")

    @classmethod
    def get_show_fields(cls):
        return ['modelname', 'name', 'kind']

    @classmethod
    def get_edit_fields(cls):
        return ['modelname', 'name', 'kind']

    @classmethod
    def get_default_fields(cls):
        return ['name', (_('model'), 'model_title'), (_('kind'), 'kind_txt')]

    def model_associated(self):
        from django.apps import apps
        return apps.get_model(self.modelname)

    def get_fieldname(self):
        return "custom_%d" % self.id

    @property
    def model_title(self):
        return six.text_type(self.model_associated()._meta.verbose_name)

    @property
    def kind_txt(self):
        dep_field = self.get_field_by_name('kind')
        args = self.get_args()
        params_txt = ""
        if self.kind == 0:
            if args['multi']:
                params_txt = "(%s)" % _('multi-line')
        elif self.kind == 1:
            params_txt = "[%d;%d]" % (int(args['min']), int(args['max']))
        elif self.kind == 2:
            prec = ".%df" % int(args['prec'])
            floatformat = "[%" + prec + ";%" + prec + "]"
            params_txt = floatformat % (float(args['min']), float(args['max']))
        elif self.kind == 4:
            params_txt = "(%s)" % ",".join(args['list'])
        value = "%s %s" % (get_value_if_choices(self.kind, dep_field), params_txt)
        return value.strip()

    def get_args(self):
        default_args = {'min': 0, 'max': 0, 'prec': 0, 'list': [], 'multi': False}
        try:
            args = eval(self.args)
        except:
            args = {}
        for name, val in default_args.items():
            if name not in args.keys():
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

    @classmethod
    def get_filter(cls, model):
        model_list = []
        for sub_class in model.get_select_contact_type():
            model_list.append(sub_class[0])
        return cls.objects.filter(modelname__in=model_list)

    @classmethod
    def get_fields(cls, model):
        fields = []
        import inspect
        model_list = []
        for sub_class in inspect.getmro(model):
            if hasattr(sub_class, "get_long_name"):
                model_list.append(sub_class.get_long_name())
        for cf_model in cls.objects.filter(modelname__in=model_list):
            fields.append((cf_model.get_fieldname(), cf_model))
        return fields

    @classmethod
    def edit_fields(cls, xfer, init_col):
        col = init_col
        col_offset = 0
        colspan = 1
        row = xfer.get_max_row() + 5
        for cf_name, cf_model in cls.get_fields(xfer.item.__class__):
            comp = cf_model.editor.get_comp(getattr(xfer.item, cf_name))
            comp.set_location(col + col_offset, row, colspan, 1)
            comp.description = cf_model.name
            xfer.add_component(comp)
            col_offset += 1
            if col_offset == 2:
                col_offset = 0
                colspan = 1
                row += 1
            else:
                colspan = 2

    class Meta(object):
        verbose_name = _('custom field')
        verbose_name_plural = _('custom fields')
        default_permissions = []


class CustomizeObject(object):

    CustomFieldClass = None
    FieldName = ''

    @classmethod
    def get_fields_to_show(cls):
        fields_desc = []
        cust_fields = CustomField.get_fields(cls)
        if len(cust_fields) > 0:
            cust_item = []
            for cf_name, cf_model in cust_fields:
                cust_item.append((cf_model.name, cf_name))
                if len(cust_item) == 2:
                    fields_desc.append(tuple(cust_item))
                    cust_item = []
            if len(cust_item) != 0:
                fields_desc.append(tuple(cust_item))
        return fields_desc

    def set_custom_values(self, params):
        for cf_name, cf_model in CustomField.get_fields(self.__class__):
            if cf_name in params.keys():
                cf_value = params[cf_name]
                cf_id = int(cf_name[7:])
                cf_model = CustomField.objects.get(id=cf_id)
                try:
                    if cf_model.kind == 1:
                        cf_value = int(cf_value)
                    if cf_model.kind == 2:
                        cf_value = float(cf_value)
                    if cf_model.kind == 3:
                        cf_value = (cf_value != 'False') and (cf_value != '0') and (cf_value != '') and (cf_value != 'n')
                    if cf_model.kind == 4:
                        args_list = cf_model.get_args()['list']
                        if args_list.count(cf_value) > 0:
                            cf_value = args_list.index(cf_value)
                        else:
                            cf_value = int(cf_value)
                except:
                    cf_value = ""
                args = {self.FieldName: self, 'field': cf_model}
                ccf_model = self.CustomFieldClass.objects.get_or_create(**args)
                ccf_model[0].value = six.text_type(cf_value)
                ccf_model[0].save()

    def get_custom_by_name(self, custom_name):
        fields = CustomField.objects.filter(modelname=self.__class__.get_long_name(), name=custom_name)
        if len(fields) == 1:
            return getattr(self, fields[0].get_fieldname())
        else:
            return None

    def __getattr__(self, name):
        if name == "str":
            return six.text_type(self.get_final_child())
        elif name[:7] == "custom_":
            cf_id = int(name[7:])
            cf_model = CustomField.objects.get(
                id=cf_id)
            if self.id is None:
                ccf_value = ""
            else:
                args = {self.FieldName: self, 'field': cf_model}
                ccf_models = self.CustomFieldClass.objects.filter(**args)
                if len(ccf_models) == 0:
                    ccf_model = self.CustomFieldClass.objects.create(**args)
                elif len(ccf_models) == 1:
                    ccf_model = ccf_models[0]
                else:
                    ccf_model = ccf_models[0]
                    for old_model in ccf_models[1:]:
                        old_model.delete()
                ccf_value = ccf_model.value
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


class PostalCode(LucteriosModel):
    postal_code = models.CharField(_('postal code'), max_length=10, blank=False)
    city = models.CharField(_('city'), max_length=100, blank=False)
    country = models.CharField(_('country'), max_length=100, blank=False)

    postalcode__editfields = ['postal_code', 'city', 'country']
    postalcode__searchfields = ['postal_code', 'city', 'country']

    @classmethod
    def get_default_fields(cls):
        return ['postal_code', 'city', 'country']

    def __str__(self):
        return '[%s] %s %s' % (self.country, self.postal_code, self.city)

    class Meta(object):

        verbose_name = _('postal code')
        verbose_name_plural = _('postal codes')
        default_permissions = ['add', 'change']
        ordering = ['postal_code', 'city']
        unique_together = (('postal_code', 'city', 'country'),)


class Function(LucteriosModel):
    name = models.CharField(_('name'), max_length=50, unique=True)

    def __str__(self):
        return self.name

    @classmethod
    def get_default_fields(cls):
        return ["name"]

    class Meta(object):

        verbose_name = _('individual function')
        verbose_name_plural = _('individual functions')
        default_permissions = []


class StructureType(LucteriosModel):
    name = models.CharField(_('name'), max_length=50, unique=True)

    @classmethod
    def get_default_fields(cls):
        return ["name"]

    def __str__(self):
        return self.name

    class Meta(object):

        verbose_name = _('structure type')
        verbose_name_plural = _('structure types')
        default_permissions = []


class ContactCustomField(LucteriosModel):
    contact = models.ForeignKey('AbstractContact', verbose_name=_('contact'), null=False, on_delete=models.CASCADE)
    field = models.ForeignKey('CustomField', verbose_name=_('field'), null=False, on_delete=models.CASCADE)
    value = models.TextField(_('value'), default="")

    class Meta(object):
        verbose_name = _('custom field value')
        verbose_name_plural = _('custom field values')
        default_permissions = []


class AbstractContact(LucteriosModel, CustomizeObject):
    CustomFieldClass = ContactCustomField
    FieldName = 'contact'

    address = models.TextField(_('address'), blank=False)
    postal_code = models.CharField(_('postal code'), max_length=10, blank=False)
    city = models.CharField(_('city'), max_length=100, blank=False)
    country = models.CharField(_('country'), max_length=100, blank=True)
    tel1 = models.CharField(_('tel1'), max_length=20, blank=True)
    tel2 = models.CharField(_('tel2'), max_length=20, blank=True)
    email = models.EmailField(_('email'), blank=True)
    comment = models.TextField(_('comment'), blank=True)

    @classmethod
    def get_default_fields(cls):
        return [(_('contact'), 'str'), 'tel1', 'tel2', 'email']

    @classmethod
    def get_show_fields(cls):
        fields_desc = ['address', ('postal_code', 'city'), 'country', ('tel1', 'tel2'), 'email', 'comment']
        fields_desc.extend(cls.get_fields_to_show())
        return fields_desc

    @classmethod
    def get_edit_fields(cls):
        return ['address', ('postal_code', 'city'), 'country', ('tel1', 'tel2'), 'email', 'comment']

    @classmethod
    def get_search_fields(cls):
        fieldnames = ['address', 'postal_code', 'city', 'country', 'tel1', 'tel2', 'email', 'comment']
        from django.db.models import Q
        for cf_name, cf_model in CustomField.get_fields(cls):
            fieldnames.append((cf_name, cf_model.get_field(), 'contactcustomfield__value', Q(
                contactcustomfield__field__id=cf_model.id)))
        return fieldnames

    @classmethod
    def get_print_fields(cls):
        return [(_('contact'), 'str'), 'address', 'postal_code', 'city', 'country', 'tel1', 'tel2', 'email']

    @classmethod
    def get_import_fields(cls):
        fields = super(AbstractContact, cls).get_import_fields()
        for field in CustomField.get_fields(cls):
            fields.append((field[0], field[1].name))
        return fields

    @classmethod
    def import_data(cls, rowdata, dateformat):
        try:
            new_item = super(AbstractContact, cls).import_data(rowdata, dateformat)
            if new_item is not None:
                new_item.set_custom_values(rowdata)
            return new_item
        except Exception:
            logging.getLogger('lucterios.contacts').exception("import_data")
            return None

    def get_presentation(self):
        return ""

    @classmethod
    def get_all_print_fields(cls, with_plugin=True):
        fields = super(AbstractContact, cls).get_all_print_fields(with_plugin)
        for cf_name, cf_model in CustomField.get_fields(cls):
            fields.append((cf_model.name, cf_name))
        return fields

    @property
    def image(self):
        img_path = get_user_path("contacts", "Image_%s.jpg" % self.abstractcontact_ptr_id)
        if exists(img_path):
            img = readimage_to_base64(img_path)
        else:
            img = readimage_to_base64(join(dirname(__file__), "static", 'lucterios.contacts', "images", "NoImage.png"))
        return img.decode('ascii')

    def get_ref_contact(self):
        return self

    class Meta(object):
        verbose_name = _('generic contact')
        verbose_name_plural = _('generic contacts')


class LegalEntity(AbstractContact):
    name = models.CharField(_('name'), max_length=100, blank=False)
    structure_type = models.ForeignKey('StructureType', verbose_name=_('structure type'), null=True, on_delete=models.SET_NULL)
    identify_number = models.TextField(_('identify number'), blank=True)

    @classmethod
    def get_show_fields(cls):
        ident_field = ['name', 'structure_type']
        ident_field.extend(super(LegalEntity, cls).get_show_fields())
        ident_field.append('identify_number')
        res_fields = {_('001@Identity'): ident_field, _('002@Members'): ['responsability_set']}
        return res_fields

    @classmethod
    def get_edit_fields(cls):
        res_fields = ['name', 'structure_type']
        res_fields.extend(super(LegalEntity, cls).get_edit_fields())
        res_fields.append('identify_number')
        return res_fields

    @classmethod
    def get_search_fields(cls):
        res_fields = ['name', 'structure_type']
        res_fields.extend(super(LegalEntity, cls).get_search_fields())
        res_fields.extend(['identify_number', 'responsability_set.individual.firstname',
                           'responsability_set.individual.lastname', 'responsability_set.functions'])
        return res_fields

    @classmethod
    def get_default_fields(cls):
        return ["name", 'tel1', 'tel2', 'email']

    @classmethod
    def get_print_fields(cls):
        return ["image", "name", 'structure_type', 'address', 'postal_code', 'city', 'country', 'tel1', 'tel2',
                'email', 'comment', 'identify_number', 'OUR_DETAIL']

    def __str__(self):
        return self.name

    def get_presentation(self):
        sub_contact = []
        for indiv in Individual.objects.filter(responsability__legal_entity=self):
            sub_contact.append(indiv.get_presentation())
        if len(sub_contact) == 0:
            return self.name
        else:
            return "%s (%s)" % (", ".join(sub_contact), self.name)

    def can_delete(self):
        msg = AbstractContact.can_delete(self)
        if msg == '':
            if self.id == 1:
                msg = _("You cannot delete this legal entity!")
        return msg

    class Meta(object):
        verbose_name = _('legal entity')
        verbose_name_plural = _('legal entities')
        default_permissions = []
        ordering = ['name']


class Individual(AbstractContact):
    genre = models.IntegerField(choices=((1, _('Man')), (2, _('Woman'))), default=1, null=False)
    firstname = models.CharField(_('firstname'), max_length=100, blank=False)
    lastname = models.CharField(_('lastname'), max_length=100, blank=False)
    user = models.ForeignKey('CORE.LucteriosUser', verbose_name=_('user'), null=True, on_delete=models.SET_NULL)

    @classmethod
    def get_show_fields(cls):
        ident_field = ['genre', ('firstname', 'lastname')]
        ident_field.extend(super(Individual, cls).get_show_fields())
        ident_field.append('user')
        res_fields = {_('001@Identity'): ident_field}
        return res_fields

    @classmethod
    def get_edit_fields(cls):
        ident_field = ['genre', ('firstname', 'lastname')]
        ident_field.extend(super(Individual, cls).get_edit_fields())
        return ident_field

    @classmethod
    def get_search_fields(cls):
        ident_field = ['lastname', 'firstname', 'genre']
        ident_field.extend(super(Individual, cls).get_search_fields())
        ident_field.extend(['user.username', 'responsability_set.legal_entity.name', 'responsability_set.functions'])
        return ident_field

    @classmethod
    def get_default_fields(cls):
        return ["firstname", "lastname", 'tel1', 'tel2', 'email']

    @classmethod
    def get_print_fields(cls):
        return ["image", "firstname", "lastname", 'address', 'postal_code', 'city', 'country', 'tel1', 'tel2',
                'email', 'comment', 'user', 'responsability_set', 'OUR_DETAIL']

    def __str__(self):
        return '%s %s' % (self.lastname, self.firstname)

    def get_presentation(self):
        return '%s %s' % (self.firstname, self.lastname)

    class Meta(object):
        verbose_name = _('individual')
        verbose_name_plural = _('individuals')
        default_permissions = []
        ordering = ['lastname', 'firstname']


class Responsability(LucteriosModel):
    individual = models.ForeignKey(Individual, verbose_name=_('individual'), null=False, on_delete=models.CASCADE)
    legal_entity = models.ForeignKey(LegalEntity, verbose_name=_('legal entity'), null=False, on_delete=models.CASCADE)
    functions = models.ManyToManyField(Function, verbose_name=_('functions'), blank=True)
    functions__titles = [_("Available functions"), _("Chosen functions")]

    @classmethod
    def get_edit_fields(cls):
        return ["legal_entity", "individual", "functions"]

    @classmethod
    def get_search_fields(cls):
        return ["legal_entity", "individual", "functions"]

    @classmethod
    def get_default_fields(cls):
        return ["individual", "functions"]

    @classmethod
    def get_print_fields(cls):
        return ["legal_entity", "functions"]

    class Meta(object):
        verbose_name = _('associate')
        verbose_name_plural = _('associates')


class OurDetailPrintPlugin(PrintFieldsPlugIn):

    name = "OUR_DETAIL"
    title = _('our detail')

    def get_all_print_fields(self):
        fields = []
        for title, name in LegalEntity.get_all_print_fields(False):
            if (name[:14] != 'structure_type') and (name[:len(self.name)] != self.name):
                fields.append(("%s > %s" % (self.title, title), "%s.%s" % (self.name, name)))
        return fields

    def evaluate(self, text_to_evaluate):
        our_details = LegalEntity.objects.get(id=1)
        return our_details.evaluate(text_to_evaluate)


PrintFieldsPlugIn.add_plugin(OurDetailPrintPlugin)


@Signal.decorate('checkparam')
def contacts_checkparam():
    Parameter.check_and_create(name='contacts-mailtoconfig', typeparam=4, title=_("contacts-mailtoconfig"), args="{'Enum':3}", value='0',
                               param_titles=(_("contacts-mailtoconfig.0"), _("contacts-mailtoconfig.1"), _("contacts-mailtoconfig.2")))
    Parameter.check_and_create(name='contacts-createaccount', typeparam=4, title=_("contacts-createaccount"), args="{'Enum':3}", value='0',
                               param_titles=(_("contacts-createaccount.0"), _("contacts-createaccount.1"), _("contacts-createaccount.2")))
