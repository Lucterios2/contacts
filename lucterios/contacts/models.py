# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from django.db import models

class PostalCode(models.Model):

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
