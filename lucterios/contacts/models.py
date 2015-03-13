# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.db import models
from lucterios.framework.models import LucteriosModel

class PostalCode(LucteriosModel):
    postal_code = models.CharField(_('postal code'), max_length=10, blank=False)
    city = models.CharField(_('city'), max_length=100, blank=False)
    country = models.CharField(_('country'), max_length=100, blank=False)

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('postal code')
        verbose_name_plural = _('postal codes')
        default_permissions = ['add', 'change']
        ordering = ['postal_code', 'city']
        unique_together = (('postal_code', 'city', 'country'),)

class Function(LucteriosModel):
    name = models.CharField(_('name'), max_length=50, unique=True)

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('individual function')
        verbose_name_plural = _('individual functions')
        default_permissions = []

class StructureType(LucteriosModel):
    name = models.CharField(_('name'), max_length=50, unique=True)

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('structure type')
        verbose_name_plural = _('structure types')
        default_permissions = []

class AbstractContact(LucteriosModel):
    address = models.TextField(_('address'), blank=False)  # '=>array('description'=>'Adresse', 'type'=>2, 'notnull'=>true, 'params'=>array('Size'=>200, 'Multi'=>true))
    postal_code = models.CharField(_('postal code'), max_length=10, blank=False)  # =>array('description'=>'Code Postal', 'type'=>2, 'notnull'=>true, 'params'=>array('Size'=>8, 'Multi'=>false))
    city = models.CharField(_('city'), max_length=100, blank=False)  # =>array('description'=>'Ville', 'type'=>2, 'notnull'=>true, 'params'=>array('Size'=>70, 'Multi'=>false))
    country = models.CharField(_('country'), max_length=100, blank=False)  # =>array('description'=>'Pays', 'type'=>2, 'notnull'=>false, 'params'=>array('Size'=>50, 'Multi'=>false))
    tel1 = models.CharField(_('tel1'), max_length=15)  # =>array('description'=>'Tel. Fixe', 'type'=>2, 'notnull'=>false, 'params'=>array('Size'=>15, 'Multi'=>false))
    tel2 = models.CharField(_('tel2'), max_length=15)  # =>array('description'=>'Tel. Portable', 'type'=>2, 'notnull'=>false, 'params'=>array('Size'=>15, 'Multi'=>false))
    email = models.EmailField(_('email'))  # '=>array('description'=>'Courriel', 'type'=>2, 'notnull'=>false, 'params'=>array('Size'=>100, 'Multi'=>false)),
    comment = models.TextField(_('comment'))  # '=>array('description'=>'Commentaire', 'type'=>7, 'notnull'=>false, 'params'=>array()),

    abstractcontact_editfields = ['address', ('postal_code', 'city'), 'country', ('tel1', 'tel2'), 'email', 'comment']

    class Meta(object):
        # pylint: disable=no-init
        default_permissions = []

class LegalEntity(AbstractContact):
    name = models.CharField(_('name'), max_length=100, blank=False)
    structure_type = models.ForeignKey('StructureType', null=True)
    identify_number = models.CharField(_('identify number'), max_length=30)

    legalentity_editfields = ['name', 'structure_type', None, 'identify_number']

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('legal entity')
        verbose_name_plural = _('legal entities')

class Individual(AbstractContact):
    genre = models.IntegerField(choices=((1, _('Man')), (2, _('Woman'))), default=1)
    firstname = models.CharField(_('firstname'), max_length=30, blank=False)
    lastname = models.CharField(_('lastname'), max_length=30, blank=False)
    user = models.ForeignKey('auth.User', null=True)
    # functions'=>array('description'=>'Fonctions', 'type'=>11, 'notnull'=>false, 'params'=>array('Function'=>'org_lucterios_contacts_FCT_personnePhysique_APAS_getFunctions', 'NbField'=>2)));

    individual_editfields = ['genre', ('firstname', 'lastname'), None, 'user']

    class Meta(object):
        # pylint: disable=no-init
        verbose_name = _('individual')
        verbose_name_plural = _('individuals')
