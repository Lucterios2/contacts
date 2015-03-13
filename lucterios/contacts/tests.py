# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals

from lucterios.framework.test import LucteriosTest
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.contacts.views import PostalCodeList, PostalCodeAdd, Configuration, CurrentStructure
from django.utils import six
from unittest.loader import TestLoader
from unittest.suite import TestSuite
from lucterios.contacts.models import LegalEntity

class PostalCodeTest(LucteriosTest):
    # pylint: disable=too-many-public-methods,too-many-statements

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        ourdetails = LegalEntity.objects.get(id=1) # pylint: disable=no-member
        ourdetails.postal_code = "97400"
        ourdetails.save()

    def test_listall(self):
        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {'filter_postal_code':''}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_xml_equal('TITLE', 'Code postal')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_count_equal('ACTIONS/ACTION', 1)
        self.assert_action_equal('ACTIONS/ACTION', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 5)
        self.assert_comp_equal('COMPONENTS/IMAGE[@name="img"]', 'contacts/images/postalCode.png', (0, 0, 1, 2))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="filtre"]', '{[b]}Filtrer par code postal{[/b]}', (1, 0, 1, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="filter_postal_code"]', None, (1, 1, 1, 1))
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="postalCode"]', (0, 2, 3, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux/ville: 333", (0, 3, 3, 1))

        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'PageMax', '13')
        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'PageNum', '0')
        self.assert_count_equal('COMPONENTS/GRID[@name="postalCode"]/HEADER', 3)
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/HEADER[@name="postal_code"]', "code postal")
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/HEADER[@name="city"]', "ville")
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/HEADER[@name="country"]', "pays")
        self.assert_count_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD', 25)
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[1]/VALUE[@name="postal_code"]', '97100')
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[25]/VALUE[@name="postal_code"]', '97131')

    def test_listdefault(self):
        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_comp_equal('COMPONENTS/EDIT[@name="filter_postal_code"]', '97400', (1, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux/ville: 6", (0, 3, 3, 1))

        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'PageMax', None)
        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'PageNum', None)
        self.assert_count_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD', 6)

    def test_filterlist(self):
        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {'filter_postal_code':'973'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux/ville: 27", (0, 3, 3, 1))
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[1]/VALUE[@name="postal_code"]', '97300')
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[25]/VALUE[@name="postal_code"]', '97370')

    def test_pagelist(self):
        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {'GRID_PAGE%postalCode':'5', 'filter_postal_code':''}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux/ville: 333", (0, 3, 3, 1))
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[1]/VALUE[@name="postal_code"]', '97417')

    def test_add(self):
        self.factory.xfer = PostalCodeAdd()
        self.call('/CORE/postalCodeAdd', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeAdd')
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal('ACTIONS/ACTION[1]', ('Ok', 'images/ok.png', 'contacts', 'postalCodeAdd', 1, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Annuler', 'images/cancel.png'))
        self.assert_count_equal('COMPONENTS/*', 7)

        self.factory.xfer = PostalCodeAdd()
        self.call('/CORE/postalCodeAdd', {'SAVE':'YES', 'postal_code':'96999', 'city':'Trifouilly', 'country':'LOIN'}, False)
        self.assert_observer('Core.Acknowledge', 'CORE', 'postalCodeAdd')
        self.assert_count_equal('CONTEXT/PARAM', 4)

        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {'filter_postal_code':''}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux/ville: 334", (0, 3, 3, 1))

        self.factory.xfer = PostalCodeAdd()
        self.call('/CORE/postalCodeAdd', {'SAVE':'YES', 'postal_code':'96999', 'city':'Trifouilly', 'country':'LOIN'}, False)
        self.assert_observer('Core.DialogBox', 'CORE', 'postalCodeAdd')
        self.assert_attrib_equal('TEXT', 'type', '3')
        self.assert_xml_equal('TEXT', six.text_type('Cet enregistrement existe déjà!'))

class ConfigurationTest(LucteriosTest):
    # pylint: disable=too-many-public-methods,too-many-statements

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        ourdetails = LegalEntity.objects.get(id=1) # pylint: disable=no-member
        ourdetails.name = "WoldCompany"
        ourdetails.address = "wall street"
        ourdetails.postal_code = "10005"
        ourdetails.city = "New-York"
        ourdetails.country = "USA - New York"
        ourdetails.tel1 = "555-123-456"
        ourdetails.email = "mr-sylvestre@worldcompany.com"
        ourdetails.save()

    def test_list(self):
        self.factory.xfer = Configuration()
        self.call('/CORE/configuration', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'configuration')
        self.assert_xml_equal('TITLE', 'Configuration des contacts')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('ACTIONS/ACTION', 1)
        self.assert_action_equal('ACTIONS/ACTION', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 13)
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="function"]', (0, 1, 2, 1, 1))
        self.assert_count_equal('COMPONENTS/GRID[@name="function"]/HEADER', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="function"]/HEADER[@name="name"]', "nom")
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="structure_type"]', (0, 1, 2, 1, 2))
        self.assert_count_equal('COMPONENTS/GRID[@name="structure_type"]/HEADER', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="structure_type"]/HEADER[@name="name"]', "nom")

    def test_ourdetails(self):

        self.factory.xfer = CurrentStructure()
        self.call('/CORE/currentStructure', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'currentStructure')
        self.assert_xml_equal('TITLE', six.text_type('Nos coordonnées'))
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal('ACTIONS/ACTION[1]', (six.text_type('Editer'), 'images/edit.png', 'contacts', 'currentStructureAddModify', 0, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 26)
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="name"]', "WoldCompany", (2, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="structure_type"]', "---", (1, 0, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="address"]', "wall street", (1, 1, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="postal_code"]', "10005", (1, 2, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="city"]', "New-York", (3, 2, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="country"]', "USA - New York", (1, 3, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="tel1"]', "555-123-456", (1, 4, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="tel2"]', None, (3, 4, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="email"]', "mr-sylvestre@worldcompany.com", (1, 5, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="comment"]', None, (1, 6, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="identify_number"]', None, (1, 7, 3, 1, 1))

def suite():
    # pylint: disable=redefined-outer-name
    suite = TestSuite()
    loader = TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(PostalCodeTest))
    suite.addTest(loader.loadTestsFromTestCase(ConfigurationTest))
    return suite
