# -*- coding: utf-8 -*-
'''
Created on march 2015

@author: sd-libre
'''

from __future__ import unicode_literals

from lucterios.framework.test import LucteriosTest, add_empty_user
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.contacts.views import PostalCodeList, PostalCodeAdd, Configuration, CurrentStructure, \
    CurrentStructureAddModify, Account, AccountAddModify
from django.utils import six
from unittest.loader import TestLoader
from unittest.suite import TestSuite
from lucterios.contacts.models import LegalEntity, Individual, StructureType, \
    Function
from shutil import rmtree
from lucterios.framework.filetools import get_user_dir, readimage_to_base64, \
    get_user_path
from os.path import join, dirname, exists
from lucterios.CORE.models import LucteriosUser
from lucterios.contacts.views_contacts import IndividualList, LegalEntityList, \
    LegalEntityAddModify, IndividualAddModify, IndividualShow, IndividualUserAdd, \
    IndividualUserValid, LegalEntityDel, LegalEntityShow, ResponsabilityAdd, \
    ResponsabilityModify, LegalEntitySearch, IndividualSearch
from lucterios.CORE.views_usergroup import UsersEdit

def change_ourdetail():
    ourdetails = LegalEntity.objects.get(id=1)  # pylint: disable=no-member
    ourdetails.name = "WoldCompany"
    ourdetails.address = "Place des cocotiers"
    ourdetails.postal_code = "97200"
    ourdetails.city = "FORT DE FRANCE"
    ourdetails.country = "MARTINIQUE"
    ourdetails.tel1 = "01-23-45-67-89"
    ourdetails.email = "mr-sylvestre@worldcompany.com"
    ourdetails.save()

def create_jack(empty_user=None):
    empty_contact = Individual()
    empty_contact.firstname = "jack"
    empty_contact.lastname = "MISTER"
    empty_contact.address = "rue de la liberté"
    empty_contact.postal_code = "97250"
    empty_contact.city = "LE PRECHEUR"
    empty_contact.country = "MARTINIQUE"
    empty_contact.tel2 = "02-78-45-12-95"
    empty_contact.email = "jack@worldcompany.com"
    empty_contact.user = empty_user
    empty_contact.save()
    return empty_contact

class PostalCodeTest(LucteriosTest):
    # pylint: disable=too-many-public-methods,too-many-statements

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        ourdetails = LegalEntity.objects.get(id=1)  # pylint: disable=no-member
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
        self.assert_comp_equal('COMPONENTS/IMAGE[@name="img"]', 'contacts/images/postalCode.png', (0, 0, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="filtre"]', '{[b]}Filtrer par code postal{[/b]}', (1, 0, 1, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="filter_postal_code"]', None, (1, 1, 1, 1))
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="postalCode"]', (0, 2, 2, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux: 333", (0, 3, 2, 1))

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
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux: 6", (0, 3, 2, 1))

        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'PageMax', None)
        self.assert_attrib_equal('COMPONENTS/GRID[@name="postalCode"]', 'PageNum', None)
        self.assert_count_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD', 6)

    def test_filterlist(self):
        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {'filter_postal_code':'973'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux: 27", (0, 3, 2, 1))
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[1]/VALUE[@name="postal_code"]', '97300')
        self.assert_xml_equal('COMPONENTS/GRID[@name="postalCode"]/RECORD[25]/VALUE[@name="postal_code"]', '97370')

    def test_pagelist(self):
        self.factory.xfer = PostalCodeList()
        self.call('/CORE/postalCodeList', {'GRID_PAGE%postalCode':'5', 'filter_postal_code':''}, False)
        self.assert_observer('Core.Custom', 'CORE', 'postalCodeList')
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux: 333", (0, 3, 2, 1))
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
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="nb"]', "Nombre total de code postaux: 334", (0, 3, 2, 1))

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
        change_ourdetail()
        create_jack(add_empty_user())
        rmtree(get_user_dir(), True)

    def test_config(self):
        self.factory.xfer = Configuration()
        self.call('/CORE/configuration', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'configuration')
        self.assert_xml_equal('TITLE', 'Configuration des contacts')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('ACTIONS/ACTION', 1)
        self.assert_action_equal('ACTIONS/ACTION', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 10)
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
        self.assert_count_equal('COMPONENTS/*', 27)
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="name"]', "WoldCompany", (2, 0, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="address"]', "Place des cocotiers", (2, 2, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="postal_code"]', "97200", (2, 3, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="city"]', "FORT DE FRANCE", (4, 3, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="country"]', "MARTINIQUE", (2, 4, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="tel1"]', "01-23-45-67-89", (2, 5, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="tel2"]', None, (4, 5, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LINK[@name="email"]', "mr-sylvestre@worldcompany.com", (2, 6, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="comment"]', None, (2, 7, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="identify_number"]', None, (2, 8, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/IMAGE[@name="logoimg"]', "contacts/images/NoImage.png", (0, 2, 1, 6, 1))
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="responsability_set"]', (1, 0, 1, 1, 2))

    def test_changedetails(self):
        self.factory.xfer = CurrentStructureAddModify()
        self.call('/CORE/currentAddModify', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'currentAddModify')
        self.assert_xml_equal('TITLE', six.text_type('Nos coordonnées'))
        self.assert_count_equal('COMPONENTS/*', 23)
        self.assert_comp_equal('COMPONENTS/EDIT[@name="name"]', "WoldCompany", (2, 0, 3, 1))
        self.assert_comp_equal('COMPONENTS/MEMO[@name="address"]', "Place des cocotiers", (2, 2, 3, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="postal_code"]', "97200", (2, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/SELECT[@name="city"]', "FORT DE FRANCE", (4, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="country"]', "MARTINIQUE", (2, 4, 3, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="tel1"]', "01-23-45-67-89", (2, 5, 1, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="tel2"]', None, (4, 5, 1, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="email"]', "mr-sylvestre@worldcompany.com", (2, 6, 3, 1))
        self.assert_comp_equal('COMPONENTS/MEMO[@name="comment"]', None, (2, 7, 3, 1))
        self.assert_comp_equal('COMPONENTS/EDIT[@name="identify_number"]', None, (2, 8, 3, 1))
        self.assert_coordcomp_equal('COMPONENTS/UPLOAD[@name="uploadlogo"]', (2, 17, 3, 1))

        self.factory.xfer = CurrentStructureAddModify()
        self.call('/CORE/currentAddModify', {"address":'Rue de la liberté{[newline]}BP 123', \
                        "comment":'Big boss: Mr Sylvestre{[newline]}Beuaaaaa....', "name":'WorldCompany', \
                        "city":'ST PIERRE', "country":'MARTINIQUE', "tel2":'06-01-02-03-04', "SAVE":'YES', \
                        "tel1":'09-87-65-43-21', "postal_code":'97250', "email":'jack@worldcompany.com', \
                        "identify_number":'AZERTY123DDSQ'}, False)
        self.assert_observer('Core.Acknowledge', 'CORE', 'currentAddModify')
        self.assert_count_equal('CONTEXT/PARAM', 11)

        self.factory.xfer = CurrentStructure()
        self.call('/CORE/currentStructure', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'currentStructure')
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

    def test_logo(self):
        self.assertFalse(exists(get_user_path('contacts', 'Image_1.jpg')))
        logo_path = join(dirname(__file__), 'images', 'ourDetails.png')
        logo_stream = "image.jpg;" + readimage_to_base64(logo_path, False).decode("utf-8")

        self.factory.xfer = CurrentStructureAddModify()
        self.call('/CORE/currentAddModify', {"SAVE":'YES', "uploadlogo":logo_stream}, False)
        self.assert_observer('Core.Acknowledge', 'CORE', 'currentAddModify')
        self.assertTrue(exists(get_user_path('contacts', 'Image_1.jpg')))

        self.factory.xfer = CurrentStructure()
        self.call('/CORE/currentStructure', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'currentStructure')
        self.assert_xml_equal('COMPONENTS/IMAGE[@name="logoimg"]', "data:image/*;base64,/9j/4AAQSkZJRg", True)

    def test_account(self):
        self.factory.user = LucteriosUser.objects.get(username='empty')  # pylint: disable=no-member
        self.factory.xfer = Account()
        self.call('/CORE/account', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'account')
        self.assert_xml_equal('TITLE', six.text_type('Mon compte'))
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal('ACTIONS/ACTION[1]', (six.text_type('Editer'), 'images/edit.png', 'contacts', 'accountAddModify', 0, 1, 1, {'individual':'2'}))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 29)
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="genre"]', "Homme", (2, 0, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="firstname"]', "jack", (2, 1, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="lastname"]', "MISTER", (4, 1, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="address"]', "rue de la liberté", (2, 2, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="postal_code"]', "97250", (2, 3, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="city"]', "LE PRECHEUR", (4, 3, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="country"]', "MARTINIQUE", (2, 4, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="tel1"]', None, (2, 5, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="tel2"]', '02-78-45-12-95', (4, 5, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/LINK[@name="email"]', "jack@worldcompany.com", (2, 6, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="comment"]', None, (2, 7, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/IMAGE[@name="logoimg"]', "contacts/images/NoImage.png", (0, 2, 1, 6, 1))

    def test_accountmodify(self):
        self.factory.xfer = AccountAddModify()
        self.call('/CORE/accountAddModify', {'individual':'2'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'accountAddModify')
        self.assert_xml_equal('TITLE', six.text_type('Mon compte'))
        self.assert_count_equal('COMPONENTS/*', 25)
        self.assert_comp_equal('COMPONENTS/SELECT[@name="genre"]', "1", (2, 0, 3, 1))
        self.assert_count_equal('COMPONENTS/SELECT[@name="genre"]/CASE', 2)
        self.assert_xml_equal('COMPONENTS/SELECT[@name="genre"]/CASE[@id="1"]', 'Homme')
        self.assert_xml_equal('COMPONENTS/SELECT[@name="genre"]/CASE[@id="2"]', 'Femme')

    def test_noaccount(self):
        self.factory.user = LucteriosUser.objects.get(username='admin')  # pylint: disable=no-member
        self.factory.xfer = Account()
        self.call('/CORE/account', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'account')
        self.assert_xml_equal('TITLE', six.text_type('Mon compte'))
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal('ACTIONS/ACTION[1]', (six.text_type('Editer'), 'images/edit.png', 'CORE', 'usersEdit', 0, 1, 1, {'user_actif':'1'}))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Fermer', 'images/close.png'))

class ContactsTest(LucteriosTest):
    # pylint: disable=too-many-public-methods,too-many-statements

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        change_ourdetail()
        rmtree(get_user_dir(), True)
        StructureType.objects.create(name="Type A")  # pylint: disable=no-member
        StructureType.objects.create(name="Type B")  # pylint: disable=no-member
        StructureType.objects.create(name="Type C")  # pylint: disable=no-member
        Function.objects.create(name="President")  # pylint: disable=no-member
        Function.objects.create(name="Secretaire")  # pylint: disable=no-member
        Function.objects.create(name="Tresorier")  # pylint: disable=no-member
        Function.objects.create(name="Troufion")  # pylint: disable=no-member
        create_jack()

    def test_individual(self):
        self.factory.xfer = IndividualList()
        self.call('/CORE/individualList', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'individualList')
        self.assert_comp_equal('COMPONENTS/EDIT[@name="filter"]', None, (1, 2, 1, 1))
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="individual"]', (0, 3, 2, 1))
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 1)

        self.factory.xfer = IndividualAddModify()
        self.call('/CORE/individualAddModify', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'individualAddModify')
        self.assert_count_equal('COMPONENTS/*', 25)

        self.factory.xfer = IndividualAddModify()
        self.call('/CORE/individualAddModify', {"address":'Avenue de la Paix{[newline]}BP 987', \
                        "comment":'no comment', "firstname":'Marie', "lastname":'DUPOND', \
                        "city":'ST PIERRE', "country":'MARTINIQUE', "tel2":'06-54-87-19-34', "SAVE":'YES', \
                        "tel1":'09-96-75-15-00', "postal_code":'97250', "email":'marie.dupond@worldcompany.com', \
                        "genre":"2"}, False)

        self.factory.xfer = IndividualList()
        self.call('/CORE/individualList', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'individualList')
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 2)

        self.factory.xfer = IndividualList()
        self.call('/CORE/individualList', {'filter':'e'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'individualList')
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 2)

        self.factory.xfer = IndividualList()
        self.call('/CORE/individualList', {'filter':'marie'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'individualList')
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 1)

        self.factory.xfer = IndividualList()
        self.call('/CORE/individualList', {'filter':'dupon'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'individualList')
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 1)

        self.factory.xfer = IndividualList()
        self.call('/CORE/individualList', {'filter':'jack'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'individualList')
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 1)

        self.factory.xfer = IndividualList()
        self.call('/CORE/individualList', {'filter':'truc'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'individualList')
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 0)

    def test_individual_image(self):
        self.assertFalse(exists(get_user_path('contacts', 'Image_2.jpg')))
        logo_path = join(dirname(__file__), 'help', 'EditIndividual.jpg')
        logo_stream = "image.jpg;" + readimage_to_base64(logo_path, False).decode("utf-8")

        self.factory.xfer = IndividualShow()
        self.call('/contacts/individualShow', {'individual':'2'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'individualShow')
        self.assert_xml_equal('COMPONENTS/IMAGE[@name="logoimg"]', "contacts/images/NoImage.png")

        self.factory.xfer = IndividualAddModify()
        self.call('/contacts/individualAddModify', {"SAVE":'YES', 'individual':'2', "uploadlogo":logo_stream}, False)
        self.assert_observer('Core.Acknowledge', 'contacts', 'individualAddModify')
        self.assertTrue(exists(get_user_path('contacts', 'Image_2.jpg')))

        self.factory.xfer = IndividualShow()
        self.call('/contacts/individualShow', {'individual':'2'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'individualShow')
        self.assert_xml_equal('COMPONENTS/IMAGE[@name="logoimg"]', "data:image/*;base64,", True)

    def test_individual_user(self):
        self.factory.xfer = IndividualShow()
        self.call('/contacts/individualShow', {'individual':'2'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'individualShow')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="genre"]', "Homme")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="firstname"]', "jack")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="lastname"]', "MISTER")
        self.assert_xml_equal('COMPONENTS/LINK[@name="email"]', "jack@worldcompany.com")

        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="user"]', "---", (2, 8, 2, 1, 1))
        self.assert_coordcomp_equal('COMPONENTS/BUTTON[@name="userbtn"]', (4, 8, 1, 1, 1))
        self.assert_action_equal('COMPONENTS/BUTTON[@name="userbtn"]/ACTIONS/ACTION', (None, 'images/add.png', 'contacts', 'individualUserAdd', 0, 1, 1))

        self.factory.xfer = IndividualUserAdd()
        self.call('/contacts/individualUserAdd', {'individual':'2'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'individualUserAdd')
        self.assert_count_equal('COMPONENTS/*', 3)
        self.assert_comp_equal('COMPONENTS/EDIT[@name="username"]', None, (2, 0, 1, 1))
        self.assert_count_equal('ACTIONS/ACTION', 2)
        self.assert_action_equal('ACTIONS/ACTION[1]', ('Ok', 'images/ok.png', 'contacts', 'individualUserValid', 1, 1, 1))
        self.assert_action_equal('ACTIONS/ACTION[2]', ('Annuler', 'images/cancel.png'))

        self.factory.xfer = IndividualUserValid()
        self.call('/contacts/individualUserValid', {'individual':'2', 'username':'jacko'}, False)
        self.assert_observer('Core.Acknowledge', 'contacts', 'individualUserValid')
        self.assert_count_equal('CONTEXT/PARAM', 4)
        self.assert_xml_equal('CONTEXT/PARAM[@name="individual"]', "2")
        self.assert_xml_equal('CONTEXT/PARAM[@name="username"]', "jacko")
        self.assert_xml_equal('CONTEXT/PARAM[@name="user_actif"]', "2")
        self.assert_xml_equal('CONTEXT/PARAM[@name="IDENT_READ"]', "YES")
        self.assert_count_equal('ACTION', 1)
        self.assert_action_equal('ACTION', (None, None, "CORE", "usersEdit", 1, 1, 1))

        self.factory.xfer = UsersEdit()
        self.call('/CORE/usersEdit', {'individual':'2', 'username':'jacko', 'user_actif':'2', 'IDENT_READ':'YES'}, False)
        self.assert_observer('Core.Custom', 'CORE', 'usersEdit')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="username"]', "jacko")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="first_name"]', "jack")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="last_name"]', "MISTER")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="email"]', "jack@worldcompany.com")

        self.factory.xfer = IndividualShow()
        self.call('/contacts/individualShow', {'individual':'2'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'individualShow')
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="user"]', "jacko", (2, 8, 2, 1, 1))
        self.assert_action_equal('COMPONENTS/BUTTON[@name="userbtn"]/ACTIONS/ACTION', (None, 'images/edit.png', 'CORE', 'usersEdit', 0, 1, 1))

    def test_individual_search(self):
        self.factory.xfer = IndividualAddModify()
        self.call('/CORE/individualAddModify', {"address":'Avenue de la Paix{[newline]}BP 987', \
                        "comment":'no comment', "firstname":'Marie', "lastname":'DUPOND', \
                        "city":'ST PIERRE', "country":'MARTINIQUE', "tel2":'06-54-87-19-34', "SAVE":'YES', \
                        "tel1":'09-96-75-15-00', "postal_code":'97250', "email":'marie.dupond@worldcompany.com', \
                        "genre":"2"}, False)

        self.factory.xfer = IndividualSearch()
        self.call('/contacts/individualSearch', {}, False)
        self.assert_observer('Core.Custom', 'contacts', 'individualSearch')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_xml_equal('CONTEXT/PARAM[@name="CRITERIA"]', None)
        self.assert_count_equal('COMPONENTS/*', 16)
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 2)

        self.factory.xfer = IndividualSearch()
        self.call('/contacts/individualSearch', {'CRITERIA':'genre||8||1;2'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'individualSearch')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_xml_equal('CONTEXT/PARAM[@name="CRITERIA"]', 'genre||8||1;2')
        self.assert_count_equal('COMPONENTS/*', 18)
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 2)

        self.factory.xfer = IndividualSearch()
        self.call('/contacts/individualSearch', {'CRITERIA':'genre||8||1'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'individualSearch')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_xml_equal('CONTEXT/PARAM[@name="CRITERIA"]', 'genre||8||1')
        self.assert_count_equal('COMPONENTS/*', 18)
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 1)

        self.factory.xfer = IndividualSearch()
        self.call('/contacts/individualSearch', {'CRITERIA':'genre||8||2'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'individualSearch')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_xml_equal('CONTEXT/PARAM[@name="CRITERIA"]', 'genre||8||2')
        self.assert_count_equal('COMPONENTS/*', 18)
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 1)

    def test_legalentity(self):
        self.factory.xfer = LegalEntityList()
        self.call('/contacts/legalEntityList', {}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntityList')
        self.assert_comp_equal('COMPONENTS/SELECT[@name="structure_type"]', '0', (1, 2, 1, 1))
        self.assert_count_equal('COMPONENTS/SELECT[@name="structure_type"]/CASE', 4)
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="legal_entity"]', (0, 3, 2, 1))
        self.assert_count_equal('COMPONENTS/GRID[@name="legal_entity"]/RECORD', 1)

        self.factory.xfer = LegalEntityAddModify()
        self.call('/contacts/legalEntityAddModify', {}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntityAddModify')
        self.assert_count_equal('COMPONENTS/*', 25)

        self.factory.xfer = LegalEntityAddModify()
        self.call('/contacts/legalEntityAddModify', {"address":'Avenue de la Paix{[newline]}BP 987', \
                        "comment":'no comment', "name":'truc-muche', \
                        "city":'ST PIERRE', "country":'MARTINIQUE', "tel2":'06-54-87-19-34', "SAVE":'YES', \
                        "tel1":'09-96-75-15-00', "postal_code":'97250', "email":'contact@truc-muche.org', \
                        "structure_type":2}, False)
        self.assert_observer('Core.Acknowledge', 'contacts', 'legalEntityAddModify')

        self.factory.xfer = LegalEntityList()
        self.call('/contacts/legalEntityList', {}, False)
        self.assert_count_equal('COMPONENTS/GRID[@name="legal_entity"]/RECORD', 2)
        self.factory.xfer = LegalEntityList()
        self.call('/contacts/legalEntityList', {"structure_type":1}, False)
        self.assert_count_equal('COMPONENTS/GRID[@name="legal_entity"]/RECORD', 0)
        self.factory.xfer = LegalEntityList()
        self.call('/contacts/legalEntityList', {"structure_type":2}, False)
        self.assert_count_equal('COMPONENTS/GRID[@name="legal_entity"]/RECORD', 1)
        self.factory.xfer = LegalEntityList()
        self.call('/contacts/legalEntityList', {"structure_type":3}, False)
        self.assert_count_equal('COMPONENTS/GRID[@name="legal_entity"]/RECORD', 0)

    def test_legalentity_delete(self):
        self.factory.xfer = LegalEntityDel()
        self.call('/contacts/legalEntityDel', {'legal_entity':'1'}, False)
        self.assert_observer('CORE.Exception', 'contacts', 'legalEntityDel')
        self.assert_xml_equal("EXCEPTION/MESSAGE", "Vous ne pouvez supprimer cette structure morale!")

    def test_legalentity_responsability(self):
        self.factory.xfer = LegalEntityShow()
        self.call('/contacts/legalEntityShow', {'legal_entity':'1'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntityShow')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="name"]', "WoldCompany")
        self.assert_count_equal('COMPONENTS/GRID[@name="responsability_set"]/HEADER', 2)
        self.assert_count_equal('COMPONENTS/GRID[@name="responsability_set"]/RECORD', 0)
        self.assert_count_equal('COMPONENTS/GRID[@name="responsability_set"]/ACTIONS/ACTION', 3)

        self.factory.xfer = ResponsabilityAdd()
        self.call('/contacts/responsabilityAdd', {'legal_entity':'1'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'responsabilityAdd')
        self.assert_count_equal('COMPONENTS/*', 7)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="legal_entity"]', "WoldCompany")
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/HEADER', 5)
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 1)
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/ACTIONS/ACTION', 3)
        self.assert_attrib_equal('COMPONENTS/GRID[@name="individual"]/RECORD[1]', 'id', '2')

        self.factory.xfer = ResponsabilityModify()
        self.call('/contacts/responsabilityModify', {'legal_entity':'1', 'individual':'2', "SAVE":"YES"}, False)
        self.assert_observer('Core.Acknowledge', 'contacts', 'responsabilityModify')

        self.factory.xfer = LegalEntityShow()
        self.call('/contacts/legalEntityShow', {'legal_entity':'1'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntityShow')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="name"]', "WoldCompany")
        self.assert_count_equal('COMPONENTS/GRID[@name="responsability_set"]/RECORD', 1)
        self.assert_attrib_equal('COMPONENTS/GRID[@name="responsability_set"]/RECORD[1]', 'id', '1')
        self.assert_xml_equal('COMPONENTS/GRID[@name="responsability_set"]/RECORD[1]/VALUE[@name="individual"]', "jack MISTER")
        self.assert_xml_equal('COMPONENTS/GRID[@name="responsability_set"]/RECORD[1]/VALUE[@name="functions"]', None)

        self.factory.xfer = ResponsabilityModify()
        self.call('/contacts/responsabilityModify', {'responsability_set':'1'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'responsabilityModify')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="legal_entity"]', "WoldCompany")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="individual"]', "jack MISTER")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="lbl_functions"]', "{[b]}fonctions{[/b]}")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="hd_functions_available"]', "{[center]}{[i]}Fonctions disponibles{[/i]}{[/center]}")
        self.assert_xml_equal('COMPONENTS/CHECKLIST[@name="functions_available"]', None)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="hd_functions_chosen"]', "{[center]}{[i]}Fonctions choisies{[/i]}{[/center]}")
        self.assert_xml_equal('COMPONENTS/CHECKLIST[@name="functions_chosen"]', None)

        self.factory.xfer = LegalEntityShow()
        self.call('/contacts/legalEntityShow', {'legal_entity':'1'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntityShow')
        self.assert_count_equal('COMPONENTS/GRID[@name="responsability_set"]/RECORD', 1)

        self.factory.xfer = ResponsabilityModify()
        self.call('/contacts/responsabilityModify', {'responsability_set':'1', 'functions':'2;4', "SAVE":"YES"}, False)
        self.assert_observer('Core.Acknowledge', 'contacts', 'responsabilityModify')

        self.factory.xfer = LegalEntityShow()
        self.call('/contacts/legalEntityShow', {'legal_entity':'1'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntityShow')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="name"]', "WoldCompany")
        self.assert_count_equal('COMPONENTS/GRID[@name="responsability_set"]/RECORD', 1)
        self.assert_attrib_equal('COMPONENTS/GRID[@name="responsability_set"]/RECORD[1]', 'id', '1')
        self.assert_xml_equal('COMPONENTS/GRID[@name="responsability_set"]/RECORD[1]/VALUE[@name="individual"]', "jack MISTER")
        self.assert_xml_equal('COMPONENTS/GRID[@name="responsability_set"]/RECORD[1]/VALUE[@name="functions"]', "Secretaire{[br/]}Troufion")

    def test_legalentity_search(self):
        self.factory.xfer = LegalEntityAddModify()
        self.call('/contacts/legalEntityAddModify', {"address":'Avenue de la Paix{[newline]}BP 987', \
                        "comment":'no comment', "name":'truc-muche', \
                        "city":'ST PIERRE', "country":'MARTINIQUE', "tel2":'06-54-87-19-34', "SAVE":'YES', \
                        "tel1":'09-96-75-15-00', "postal_code":'97250', "email":'contact@truc-muche.org', \
                        "structure_type":2}, False)
        self.assert_observer('Core.Acknowledge', 'contacts', 'legalEntityAddModify')

        self.factory.xfer = LegalEntitySearch()
        self.call('/contacts/legalEntitySearch', {}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntitySearch')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_xml_equal('CONTEXT/PARAM[@name="CRITERIA"]', None)
        self.assert_count_equal('COMPONENTS/*', 16)
        self.assert_count_equal('COMPONENTS/GRID[@name="legal_entity"]/RECORD', 2)

        self.factory.xfer = LegalEntitySearch()
        self.call('/contacts/legalEntitySearch', {'searchSelector':'name', 'searchOperator':'5', 'searchValueStr':'truc', 'ACT':'ADD'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntitySearch')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_xml_equal('CONTEXT/PARAM[@name="CRITERIA"]', 'name||5||truc')
        self.assert_count_equal('COMPONENTS/*', 18)
        self.assert_count_equal('COMPONENTS/GRID[@name="legal_entity"]/RECORD', 1)

        self.factory.xfer = LegalEntitySearch()
        self.call('/contacts/legalEntitySearch', {'searchSelector':'structure_type', 'searchOperator':'9', 'searchValueList':'2', 'ACT':'ADD'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntitySearch')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_xml_equal('CONTEXT/PARAM[@name="CRITERIA"]', 'structure_type||9||2')
        self.assert_count_equal('COMPONENTS/*', 18)
        self.assert_count_equal('COMPONENTS/GRID[@name="legal_entity"]/RECORD', 1)

        self.factory.xfer = LegalEntitySearch()
        self.call('/contacts/legalEntitySearch', {'CRITERIA':'name||5||truc//structure_type||9||2'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntitySearch')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_xml_equal('CONTEXT/PARAM[@name="CRITERIA"]', 'name||5||truc//structure_type||9||2')
        self.assert_count_equal('COMPONENTS/*', 20)
        self.assert_count_equal('COMPONENTS/GRID[@name="legal_entity"]/RECORD', 1)

        self.factory.xfer = LegalEntitySearch()
        self.call('/contacts/legalEntitySearch', {'CRITERIA':'name||5||truc//structure_type||9||2', 'ACT':'0'}, False)
        self.assert_observer('Core.Custom', 'contacts', 'legalEntitySearch')
        self.assert_count_equal('CONTEXT/PARAM', 1)
        self.assert_xml_equal('CONTEXT/PARAM[@name="CRITERIA"]', 'structure_type||9||2')
        self.assert_count_equal('COMPONENTS/*', 18)
        self.assert_count_equal('COMPONENTS/GRID[@name="legal_entity"]/RECORD', 1)

def suite():
    # pylint: disable=redefined-outer-name
    suite = TestSuite()
    loader = TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(PostalCodeTest))
    suite.addTest(loader.loadTestsFromTestCase(ConfigurationTest))
    suite.addTest(loader.loadTestsFromTestCase(ContactsTest))
    return suite
