# -*- coding: utf-8 -*-
'''
Unit tests for configuration viewer

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
from base64 import b64decode
from shutil import rmtree
from os.path import join, dirname, exists

from django.utils import six

from lucterios.framework.test import LucteriosTest, add_empty_user
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework.filetools import get_user_dir, readimage_to_base64, \
    get_user_path
from lucterios.CORE.models import LucteriosUser

from lucterios.contacts.views import PostalCodeList, PostalCodeAdd, Configuration, CurrentStructure, \
    CurrentStructureAddModify, Account, AccountAddModify, CurrentStructurePrint
from lucterios.contacts.models import LegalEntity
from lucterios.contacts.tests_contacts import change_ourdetail, create_jack


class PostalCodeTest(LucteriosTest):

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        ourdetails = LegalEntity.objects.get(id=1)
        ourdetails.postal_code = "97400"
        ourdetails.save()

    def test_listall(self):
        self.factory.xfer = PostalCodeList()
        self.call('/lucterios.contacts/postalCodeList',
                  {'filter_postal_code': ''}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeList')
        self.assert_xml_equal('TITLE', 'Code postal')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_count_equal('ACTIONS/ACTION', 1)
        self.assert_action_equal('ACTIONS/ACTION', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 4)
        self.assert_comp_equal('COMPONENTS/IMAGE[@name="img"]', '/static/lucterios.contacts/images/postalCode.png', (0, 0, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="filtre"]', '{[b]}Filtrer par code postal{[/b]}', (1, 0, 1, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="filter_postal_code"]', None, (1, 1, 1, 1))
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="postalCode"]', (0, 2, 2, 1))
        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'nb_lines', '333')

        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'PageMax', '14')
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
        self.call('/lucterios.contacts/postalCodeList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeList')
        self.assert_comp_equal('COMPONENTS/EDIT[@name="filter_postal_code"]', '97400', (1, 1, 1, 1))
        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'nb_lines', '6')

        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'PageMax', None)
        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'PageNum', None)
        self.assert_count_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD', 6)

    def test_filterlist(self):
        self.factory.xfer = PostalCodeList()
        self.call('/lucterios.contacts/postalCodeList',
                  {'filter_postal_code': '973'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeList')
        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'nb_lines', '27')
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[1]/VALUE[@name="postal_code"]', '97300')
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[25]/VALUE[@name="postal_code"]', '97370')

    def test_pagelist(self):
        self.factory.xfer = PostalCodeList()
        self.call('/lucterios.contacts/postalCodeList',
                  {'GRID_PAGE%postalCode': '5', 'filter_postal_code': ''}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeList')
        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'nb_lines', '333')
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[1]/VALUE[@name="postal_code"]', '97416')

    def test_add(self):
        self.factory.xfer = PostalCodeAdd()
        self.call('/lucterios.contacts/postalCodeAdd', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeAdd')
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal('ACTIONS/ACTION[1]', ('Ok', 'images/ok.png', 'lucterios.contacts', 'postalCodeAdd', 1, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Annuler', 'images/cancel.png'))
        self.assert_count_equal('COMPONENTS/*', 4)

        self.factory.xfer = PostalCodeAdd()
        self.call('/lucterios.contacts/postalCodeAdd', {'SAVE': 'YES', 'postal_code': '96999', 'city': 'Trifouilly', 'country': 'LOIN'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'postalCodeAdd')
        self.assert_count_equal('CONTEXT/PARAM', 3)

        self.factory.xfer = PostalCodeList()
        self.call('/lucterios.contacts/postalCodeList', {'filter_postal_code': ''}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeList')
        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'nb_lines', '334')

        self.factory.xfer = PostalCodeAdd()
        self.call('/lucterios.contacts/postalCodeAdd',
                  {'SAVE': 'YES', 'postal_code': '96999', 'city': 'Trifouilly', 'country': 'LOIN'}, False)
        self.assert_observer('core.dialogbox', 'lucterios.contacts', 'postalCodeAdd')
        self.assert_attrib_equal('TEXT', 'type', '3')
        self.assert_xml_equal('TEXT', six.text_type('Cet enregistrement existe déjà!'))


class ConfigurationTest(LucteriosTest):

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        change_ourdetail()
        create_jack(add_empty_user())
        rmtree(get_user_dir(), True)

    def test_config(self):
        self.factory.xfer = Configuration()
        self.call('/lucterios.contacts/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'configuration')
        self.assert_xml_equal('TITLE', 'Configuration des contacts')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('ACTIONS/ACTION', 1)
        self.assert_action_equal('ACTIONS/ACTION', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 12)
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="function"]', (0, 1, 2, 1, 1))
        self.assert_count_equal('COMPONENTS/GRID[@name="function"]/HEADER', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="function"]/HEADER[@name="name"]', "nom")
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="structure_type"]', (0, 1, 2, 1, 2))
        self.assert_count_equal('COMPONENTS/GRID[@name="structure_type"]/HEADER', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="structure_type"]/HEADER[@name="name"]', "nom")
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="custom_field"]', (0, 1, 2, 1, 3))
        self.assert_count_equal('COMPONENTS/GRID[@name="custom_field"]/HEADER', 3)
        self.assert_xml_equal('COMPONENTS/GRID[@name="custom_field"]/HEADER[@name="name"]', "nom")
        self.assert_xml_equal('COMPONENTS/GRID[@name="custom_field"]/HEADER[@name="model_title"]', "modèle")
        self.assert_xml_equal('COMPONENTS/GRID[@name="custom_field"]/HEADER[@name="kind_txt"]', "type")

    def test_ourdetails(self):
        self.factory.xfer = CurrentStructure()
        self.call('/lucterios.contacts/currentStructure', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'currentStructure')
        self.assert_xml_equal('TITLE', six.text_type('Nos coordonnées'))
        self.assert_count_equal('ACTIONS/ACTION', 3)
        self.assert_action_equal('ACTIONS/ACTION[1]', (six.text_type('Editer'), 'images/edit.png', 'lucterios.contacts', 'currentStructureAddModify', 0, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Imprimer', 'images/print.png', 'lucterios.contacts', 'currentStructurePrint', 0, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[3]', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 16)
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="name"]', "WoldCompany", (1, 0, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="address"]', "Place des cocotiers", (1, 2, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="postal_code"]', "97200", (1, 3, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="city"]', "FORT DE FRANCE", (2, 3, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="country"]', "MARTINIQUE", (1, 4, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="tel1"]', "01-23-45-67-89", (1, 5, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="tel2"]', None, (2, 5, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LINK[@name="email"]', "mr-sylvestre@worldcompany.com", (1, 6, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="comment"]', None, (1, 7, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="identify_number"]', None, (1, 8, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/IMAGE[@name="logoimg"]', "/static/lucterios.contacts/images/NoImage.png", (0, 2, 1, 6, 1))
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="responsability"]', (0, 0, 1, 1, 2))

    def test_changedetails(self):
        self.factory.xfer = CurrentStructureAddModify()
        self.call('/lucterios.contacts/currentAddModify', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'currentAddModify')
        self.assert_xml_equal('TITLE', six.text_type('Nos coordonnées'))
        self.assert_count_equal('COMPONENTS/*', 12)
        self.assert_comp_equal('COMPONENTS/EDIT[@name="name"]', "WoldCompany", (1, 0, 2, 1))
        self.assert_comp_equal('COMPONENTS/MEMO[@name="address"]', "Place des cocotiers", (1, 2, 2, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="postal_code"]', "97200", (1, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/SELECT[@name="city"]', "FORT DE FRANCE", (2, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="country"]', "MARTINIQUE", (1, 4, 2, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="tel1"]', "01-23-45-67-89", (1, 5, 1, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="tel2"]', None, (2, 5, 1, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="email"]', "mr-sylvestre@worldcompany.com", (1, 6, 2, 1))
        self.assert_comp_equal('COMPONENTS/MEMO[@name="comment"]', None, (1, 7, 2, 1))
        self.assert_comp_equal('COMPONENTS/MEMO[@name="identify_number"]', None, (1, 8, 2, 1))
        self.assert_coordcomp_equal('COMPONENTS/UPLOAD[@name="uploadlogo"]', (1, 18, 2, 1))

        self.factory.xfer = CurrentStructureAddModify()
        self.call('/lucterios.contacts/currentAddModify', {"address": 'Rue de la liberté{[newline]}BP 123',
                                                           "comment": 'Big boss: Mr Sylvestre{[newline]}Beuaaaaa....', "name": 'WorldCompany',
                                                           "city": 'ST PIERRE', "country": 'MARTINIQUE', "tel2": '06-01-02-03-04', "SAVE": 'YES',
                                                           "tel1": '09-87-65-43-21', "postal_code": '97250', "email": 'jack@worldcompany.com',
                                                           "identify_number": 'AZERTY123DDSQ'}, False)
        self.assert_observer(
            'core.acknowledge', 'lucterios.contacts', 'currentAddModify')
        self.assert_count_equal('CONTEXT/PARAM', 10)

        self.factory.xfer = CurrentStructure()
        self.call('/lucterios.contacts/currentStructure', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'currentStructure')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="name"]', "WorldCompany")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="address"]', "Rue de la liberté{[newline]}BP 123")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="postal_code"]', "97250")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="city"]', "ST PIERRE")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="country"]', "MARTINIQUE")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="tel1"]', "09-87-65-43-21")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="tel2"]', '06-01-02-03-04')
        self.assert_xml_equal('COMPONENTS/LINK[@name="email"]', "jack@worldcompany.com")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="comment"]', 'Big boss: Mr Sylvestre{[newline]}Beuaaaaa....')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="identify_number"]', "AZERTY123DDSQ")

    def test_printdetails(self):
        self.factory.xfer = CurrentStructurePrint()
        self.call('/lucterios.contacts/currentStructurePrint', {}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'currentStructurePrint')
        self.assert_xml_equal('TITLE', six.text_type('Nos coordonnées'))
        self.assert_xml_equal('PRINT/TITLE', six.text_type('Nos coordonnées'))
        self.assert_attrib_equal('PRINT', 'mode', '3')
        pdf_value = b64decode(six.text_type(self.get_first_xpath('PRINT').text))
        self.assertEqual(pdf_value[:4], "%PDF".encode('ascii', 'ignore'))

    def test_logo(self):
        self.assertFalse(exists(get_user_path('contacts', 'Image_1.jpg')))
        logo_path = join(dirname(__file__), "static", 'lucterios.contacts', 'images', 'ourDetails.png')
        logo_stream = "image.jpg;" + \
            readimage_to_base64(logo_path, False).decode("utf-8")

        self.factory.xfer = CurrentStructureAddModify()
        self.call('/lucterios.contacts/currentAddModify',
                  {"SAVE": 'YES', "uploadlogo": logo_stream}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'currentAddModify')
        self.assertTrue(exists(get_user_path('contacts', 'Image_1.jpg')))

        self.factory.xfer = CurrentStructure()
        self.call('/lucterios.contacts/currentStructure', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'currentStructure')
        self.assert_xml_equal('COMPONENTS/IMAGE[@name="logoimg"]', "data:image/*;base64,/9j/4AAQSkZJRg", True)

        self.factory.xfer = CurrentStructurePrint()
        self.call('/lucterios.contacts/currentStructurePrint', {}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'currentStructurePrint')
        pdf_value = b64decode(six.text_type(self.get_first_xpath('PRINT').text))
        self.assertEqual(pdf_value[:4], "%PDF".encode('ascii', 'ignore'))

    def test_account(self):
        self.factory.user = LucteriosUser.objects.get(username='empty')
        self.factory.xfer = Account()
        self.call('/lucterios.contacts/account', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'account')
        self.assert_xml_equal('TITLE', six.text_type('Votre compte'))
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal('ACTIONS/ACTION[1]', (six.text_type('Editer'), 'images/edit.png', 'lucterios.contacts', 'accountAddModify', 0, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 17)
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="genre"]', "Homme", (1, 0, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="firstname"]', "jack", (1, 1, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="lastname"]', "MISTER", (2, 1, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="address"]', "rue de la liberté", (1, 2, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="postal_code"]', "97250", (1, 3, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="city"]', "LE PRECHEUR", (2, 3, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="country"]', "MARTINIQUE", (1, 4, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="tel1"]', None, (1, 5, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="tel2"]', '02-78-45-12-95', (2, 5, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LINK[@name="email"]', "jack@worldcompany.com", (1, 6, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="comment"]', None, (1, 7, 2, 1, 1))
        self.assert_comp_equal('COMPONENTS/IMAGE[@name="logoimg"]', "/static/lucterios.contacts/images/NoImage.png", (0, 2, 1, 6, 1))

    def test_accountmodify(self):
        self.factory.xfer = AccountAddModify()
        self.call(
            '/lucterios.contacts/accountAddModify', {'individual': '2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'accountAddModify')
        self.assert_xml_equal('TITLE', six.text_type('Mon compte'))
        self.assert_count_equal('COMPONENTS/*', 13)
        self.assert_comp_equal('COMPONENTS/SELECT[@name="genre"]', "1", (1, 0, 2, 1))
        self.assert_count_equal('COMPONENTS/SELECT[@name="genre"]/CASE', 2)
        self.assert_xml_equal('COMPONENTS/SELECT[@name="genre"]/CASE[@id="1"]', 'Homme')
        self.assert_xml_equal('COMPONENTS/SELECT[@name="genre"]/CASE[@id="2"]', 'Femme')

    def test_noaccount(self):
        self.factory.user = LucteriosUser.objects.get(
            username='admin')
        self.factory.xfer = Account()
        self.call('/lucterios.contacts/account', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'account')
        self.assert_xml_equal('TITLE', six.text_type('Votre compte'))
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal('ACTIONS/ACTION[1]', (six.text_type('Editer'), 'images/edit.png', 'CORE', 'usersEdit', 0, 1, 1, {'user_actif': '1'}))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Fermer', 'images/close.png'))
