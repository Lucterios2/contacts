# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.db import models
from lucterios.framework.models import LucteriosModel
from lucterios.framework.filetools import save_from_base64, get_user_path, open_image_resize, readimage_to_base64
from posix import unlink

class PostalCode(LucteriosModel):
    postal_code = models.CharField(_('postal code'), max_length=10, blank=False)
    city = models.CharField(_('city'), max_length=100, blank=False)
    country = models.CharField(_('country'), max_length=100, blank=False)

    postalcode__editfields = ['postal_code', 'city', 'country']

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

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('individual function')
        verbose_name_plural = _('individual functions')
        default_permissions = []

class StructureType(LucteriosModel):
    name = models.CharField(_('name'), max_length=50, unique=True)

    structuretype__editfields = ['name']

    def __str__(self):
        return self.name

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('structure type')
        verbose_name_plural = _('structure types')
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
        lbl = XferCompLabelForm('lbl_uploadlogo')
        lbl.set_value_as_name(_('image'))
        lbl.set_location(obj_cmt.col - 1, obj_cmt.row + 10, 1, 1)
        xfer.add_component(lbl)
        upload = XferCompUpLoad('uploadlogo')
        upload.set_value('')
        upload.add_filter('.jpg')
        upload.add_filter('.gif')
        upload.add_filter('.png')
        upload.add_filter('.bmp')
        upload.set_location(obj_cmt.col, obj_cmt.row + 10, obj_cmt.colspan, 1)
        xfer.add_component(upload)
        return

    def show(self, xfer):
        from lucterios.framework.xfercomponents import XferCompImage
        from os.path import exists
        LucteriosModel.show(self, xfer)
        obj_addr = xfer.get_components('lbl_address')
        xfer.tab = obj_addr.tab
        new_col = obj_addr.col
        xfer.move(obj_addr.tab, 1, 0)
        img_path = get_user_path("contacts", "Image_%s.jpg" % self.abstractcontact_ptr_id) # pylint: disable=no-member
        img = XferCompImage('logoimg')
        if exists(img_path):
            img.type = 'jpg'
            img.set_value(readimage_to_base64(img_path))
        else:
            img.set_value("contacts/images/NoImage.png")
        img.set_location(new_col, obj_addr.row, 1, 6)
        xfer.add_component(img)

    def saving(self, xfer):
        uploadlogo = xfer.getparam('uploadlogo')
        if uploadlogo is not None:
            tmp_file = save_from_base64(uploadlogo)
            with open(tmp_file, "rb") as image_tmp:
                image = open_image_resize(image_tmp, 100, 100)
                img_path = get_user_path("contacts", "Image_%s.jpg" % self.abstractcontact_ptr_id) # pylint: disable=no-member
                with open(img_path, "wb") as image_file:
                    image.save(image_file, 'JPEG', quality=90)
            unlink(tmp_file)
        LucteriosModel.saving(self, xfer)

    class Meta(object):
        # pylint: disable=no-init
        default_permissions = []

class LegalEntity(AbstractContact):
    name = models.CharField(_('name'), max_length=100, blank=False)
    structure_type = models.ForeignKey('StructureType', null=True)
    identify_number = models.CharField(_('identify number'), max_length=100, blank=True)
    legalentity__showfields = {_('001@Identity'):['name', 'structure_type', None, 'identify_number'], _('002@Management'):[]}
    legalentity__editfields = ['name', 'structure_type', None, 'identify_number']

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

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('legal entity')
        verbose_name_plural = _('legal entities')

class Individual(AbstractContact):
    genre = models.IntegerField(choices=((1, _('Man')), (2, _('Woman'))), default=1, null=False)
    firstname = models.CharField(_('firstname'), max_length=50, blank=False)
    lastname = models.CharField(_('lastname'), max_length=50, blank=False)
    user = models.ForeignKey('auth.User', null=True)
    # 'functions'=>array('description'=>'Fonctions', 'type'=>11, 'notnull'=>false, 'params'=>array('Function'=>'org_lucterios_contacts_FCT_personnePhysique_APAS_getFunctions', 'NbField'=>2)));

    individual__showfields = ['genre', ('firstname', 'lastname'), None, 'user']
    individual__editfields = ['genre', ('firstname', 'lastname'), None, 'user']

    def __str__(self):
        return '%s %s' % (self.firstname, self.lastname)

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('individual')
        verbose_name_plural = _('individuals')
