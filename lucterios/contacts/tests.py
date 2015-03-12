# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals

from lucterios.framework.test import LucteriosTest
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.contacts.views import PostalCodeList, PostalCodeAdd, \
    PostalCodeModify

class PostalCodeTest(LucteriosTest):
    # pylint: disable=too-many-public-methods,too-many-statements

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)

    def test_list(self):
        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_xml_equal('TITLE', 'Code postal')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('ACTIONS/ACTION', 1)
        self.assert_action_equal('ACTIONS/ACTION', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 5)
        self.assert_comp_equal('COMPONENTS/IMAGE[@name="img"]', 'contacts/images/postalCode.png', (0, 0, 1, 2))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="filtre"]', '{[bold]}Filtrer par code postal{[/bold]}', (1, 0, 1, 1))
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

    def test_filterlist(self):
        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {'filter_postal_code':'973'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux/ville: 27", (0, 3, 3, 1))
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[1]/VALUE[@name="postal_code"]', '97300')
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[25]/VALUE[@name="postal_code"]', '97370')

    def test_pagelist(self):
        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {'GRID_PAGE%postalCode':'5'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux/ville: 333", (0, 3, 3, 1))
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[1]/VALUE[@name="postal_code"]', '97417')

    def test_add(self):
        self.factory.xfer = PostalCodeAdd()
        self.call('/CORE/postalCodeAdd', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeAdd')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal('ACTIONS/ACTION[1]', ('Ok', 'images/ok.png', 'contacts', 'postalCodeModify', 1, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Annuler', 'images/cancel.png'))
        self.assert_count_equal('COMPONENTS/*', 7)

        self.factory.xfer = PostalCodeModify()
        self.call('/CORE/postalCodeModify', {'postal_code':'96999', 'city':'Trifouilly', 'country':'LOIN'}, False)
        self.assert_observer('Core.Acknowledge', 'CORE', 'postalCodeModify')
        self.assert_count_equal('CONTEXT/PARAM', 3)

        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux/ville: 334", (0, 3, 3, 1))
