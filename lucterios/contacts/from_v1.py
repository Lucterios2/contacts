# -*- coding: utf-8 -*-
'''
from_v1 module for contacts

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

from django.apps import apps

from lucterios.install.lucterios_migration import MigrateAbstract
from django.utils import six
from os.path import join, isfile
from shutil import copyfile


class ContactsMigrate(MigrateAbstract):

    def __init__(self, old_db):
        MigrateAbstract.__init__(self, old_db)
        self.user_list = self.old_db.objectlinks['users']
        self.abstract_list = {}
        self.legalentity_list = {}
        self.individual_list = {}
        self.structuretype_list = {}
        self.function_list = {}
        self.customfield_list = {}

    def _config(self):

        function_mdl = apps.get_model("contacts", "Function")
        function_mdl.objects.all().delete()
        self.function_list = {}
        cur = self.old_db.open()
        cur.execute("SELECT id, nom FROM org_lucterios_contacts_fonctions")
        for functionid, function_name in cur.fetchall():
            self.print_debug("=> Function %s", (function_name,))
            self.function_list[functionid] = function_mdl.objects.create(
                name=function_name)

        structuretype_mdl = apps.get_model("contacts", "StructureType")
        structuretype_mdl.objects.all().delete()
        self.structuretype_list = {}
        cur = self.old_db.open()
        cur.execute("SELECT id, nom FROM org_lucterios_contacts_typesMorales")
        for structuretypeid, structuretype_name in cur.fetchall():
            self.print_debug("=> StructureType %s", (structuretype_name,))
            self.structuretype_list[structuretypeid] = structuretype_mdl.objects.create(
                name=structuretype_name)

        customfield_mdl = apps.get_model("contacts", "CustomField")
        customfield_mdl.objects.all().delete()
        self.customfield_list = {}
        cur = self.old_db.open()
        modelnames_relation = {}

        modelnames_relation[
            "org_lucterios_contacts/personneAbstraite"] = "contacts.AbstractContact"
        modelnames_relation[
            "org_lucterios_contacts/personneMorale"] = "contacts.LegalEntity"
        modelnames_relation[
            "org_lucterios_contacts/personnePhysique"] = "contacts.Individual"
        # modelnames_relation["fr_sdlibre_membres/adherents"] = ""
        cur.execute(
            "SELECT id, class, description, type, param FROM org_lucterios_contacts_champPerso")
        for customfield_val in cur.fetchall():
            self.print_debug("=> CustomField %s", customfield_val[2])
            if customfield_val[1] in modelnames_relation.keys():
                old_args = ""
                args = {
                    'min': 0, 'max': 0, 'prec': 0, 'list': '', 'multi': False}
                try:
                    old_args = customfield_val[4].replace(
                        'array(', '{').replace(')', '}').replace('=>', ':')
                    old_args = old_args.replace(
                        'false', 'False').replace("true", 'True')
                    old_args_eval = eval(old_args)
                    for arg_key, arg_val in old_args_eval.items():
                        if arg_key == "Multi":
                            args['multi'] = bool(arg_val)
                        if arg_key == "Min":
                            args['min'] = int(arg_val)
                        if arg_key == "Max":
                            args['max'] = int(arg_val)
                        if arg_key == "Prec":
                            args['prec'] = int(arg_val)
                        if arg_key == "Enum":
                            args['list'] = arg_val
                except:
                    import sys
                    import traceback
                    traceback.print_exc(file=sys.stdout)
                    self.print_debug(
                        "--- CustomField: error args=%s/%s", (customfield_val[4], old_args))
                new_cf = customfield_mdl.objects.create(
                    name=customfield_val[2], kind=customfield_val[3])
                new_cf.modelname = modelnames_relation[customfield_val[1]]
                new_cf.args = six.text_type(args)
                new_cf.save()
                self.customfield_list[customfield_val[0]] = new_cf

    def _structure(self):

        def assign_abstact_values(new_legalentity, abstract_id):
            from lucterios.framework.filetools import get_user_path
            super_cur = self.old_db.open(True)
            super_cur.execute(
                "SELECT * FROM org_lucterios_contacts_personneAbstraite WHERE id=%d" % abstract_id)
            abst_val = super_cur.fetchone()
            for old_field, new_field in [['adresse', 'address'], ['codePostal', 'postal_code'],
                                         ['ville', 'city'], [
                                             'pays', 'country'], ['fixe', 'tel1'],
                                         ['portable', 'tel2'], ['mail', 'email'], ['commentaire', 'comment']]:
                if abst_val[old_field] is not None:
                    setattr(new_legalentity, new_field, abst_val[old_field])
            old_image_filename = join(
                self.old_db.tmp_path, "usr", "org_lucterios_contacts", "Image_%d.jpg" % abstract_id)
            if isfile(old_image_filename):
                new_image_filename = get_user_path(
                    "contacts", "Image_%s.jpg" % new_legalentity.abstractcontact_ptr_id)
                copyfile(old_image_filename, new_image_filename)
        legalentity_mdl = apps.get_model("contacts", "LegalEntity")
        legalentity_mdl.objects.all().delete()
        individual_mdl = apps.get_model("contacts", "Individual")
        individual_mdl.objects.all().delete()
        abstractcontact_mdl = apps.get_model("contacts", "AbstractContact")
        abstractcontact_mdl.objects.all().delete()

        cur = self.old_db.open()
        cur.execute(
            "SELECT id, superId, raisonSociale, type, siren FROM org_lucterios_contacts_personneMorale ORDER BY id")
        for legalentityid, legalentity_super, legalentity_name, legalentity_type, legalentity_siren in cur.fetchall():
            if legalentity_name is None:
                legalentity_name = ''
            self.print_debug(
                "=> LegalEntity[%d] %s (siren=%s)", (legalentityid, legalentity_name, legalentity_siren))
            new_legalentity = legalentity_mdl.objects.create(
                name=legalentity_name)
            assign_abstact_values(new_legalentity, legalentity_super)
            if legalentity_type in self.structuretype_list.keys():
                new_legalentity.structure_type = self.structuretype_list[
                    legalentity_type]
            if legalentity_siren is not None:
                new_legalentity.identify_number = legalentity_siren
            new_legalentity.save()
            if (legalentityid == 1) and (new_legalentity.id != 1):
                other_le = legalentity_mdl.objects.get(id=new_legalentity.id)
                new_legalentity.id = 1
                new_legalentity.save()
                other_le.delete()
            self.legalentity_list[legalentityid] = new_legalentity
            self.abstract_list[legalentity_super] = new_legalentity

        cur = self.old_db.open()
        cur.execute(
            "SELECT id, superId, nom, prenom, sexe, user FROM org_lucterios_contacts_personnePhysique")
        for individualid, individual_super, individual_lastname, individual_firstname, individual_sexe, individual_user in cur.fetchall():
            self.print_debug("=> Individual %s %s (user=%s)",
                             (individual_firstname, individual_lastname, individual_user))
            new_individual = individual_mdl.objects.create(
                firstname=individual_firstname, lastname=individual_lastname)
            assign_abstact_values(new_individual, individual_super)
            new_individual.genre = individual_sexe + 1
            if individual_user in self.user_list.keys():
                new_individual.user = self.user_list[individual_user]
                new_individual.user.first_name = new_individual.firstname
                new_individual.user.last_name = new_individual.lastname
                new_individual.user.email = new_individual.email
                new_individual.user.save()
                self.user_list[individual_user] = new_individual.user
            new_individual.save()
            self.individual_list[individualid] = new_individual
            self.abstract_list[individual_super] = new_individual

    def _relations(self):

        function_mdl = apps.get_model("contacts", "Function")
        responsability_mdl = apps.get_model("contacts", "Responsability")
        responsability_mdl.objects.all().delete()
        cur = self.old_db.open()
        cur.execute(
            "SELECT DISTINCT physique, morale FROM org_lucterios_contacts_liaison")
        for physique, morale in cur.fetchall():
            if (morale in self.legalentity_list.keys()) and (physique in self.individual_list.keys()):
                new_resp = responsability_mdl.objects.create(
                    individual=self.individual_list[physique], legal_entity=self.legalentity_list[morale])
                ids = []
                fctcur = self.old_db.open()
                fctcur.execute(
                    'SELECT fonction FROM org_lucterios_contacts_liaison WHERE physique=%d AND morale=%d' % (physique, morale))
                for fonction, in fctcur.fetchall():
                    if fonction in self.function_list.keys():
                        ids.append(self.function_list[fonction].pk)

                self.print_debug("=> Responsability %s %s =%s", (six.text_type(self.individual_list[
                    physique]), six.text_type(self.legalentity_list[morale]), six.text_type(ids)))
                new_resp.functions = function_mdl.objects.filter(id__in=ids)
                new_resp.save()
        contactcustomfield_mdl = apps.get_model(
            "contacts", "ContactCustomField")
        contactcustomfield_mdl.objects.all().delete()
        cur = self.old_db.open()
        cur.execute(
            "SELECT contact, champ, value FROM org_lucterios_contacts_personneChamp")
        self.print_debug("=> ContactCustomField %d", len(list(cur.fetchall())))
        for contactcustomfield_val in cur.fetchall():
            abs_contact = self.abstract_list[contactcustomfield_val[0]]
            if (contactcustomfield_val[2] != '') and (contactcustomfield_val[1] in self.customfield_list.keys()):
                cust_field = self.customfield_list[contactcustomfield_val[1]]
                contactcustomfield_mdl.objects.create(
                    contact=abs_contact, field=cust_field, value=contactcustomfield_val[2])

    def _params(self):
        from lucterios.CORE.models import Parameter
        cur_p = self.old_db.open()
        cur_p.execute(
            "SELECT paramName,value FROM CORE_extension_params WHERE extensionId LIKE 'org_lucterios_contacts' and paramName in ('MailToConfig')")
        for param_name, param_value in cur_p.fetchall():
            pname = ''
            if param_name == 'MailToConfig':
                pname = 'contacts-mailtoconfig'
                if param_value == '':
                    param_value = '0'
            if pname != '':
                self.print_debug(
                    "=> parameter of contacts %s - %s", (pname, param_value))
                Parameter.change_value(pname, param_value)

    def run(self):
        try:
            self._params()
            self._config()
            self._structure()
            self._relations()
        finally:
            self.old_db.close()
        self.print_info("Nb individuals:%d", len(self.individual_list))
        self.print_info("Nb legal entities:%d", len(self.legalentity_list))
        self.old_db.objectlinks['abstracts'] = self.abstract_list
        self.old_db.objectlinks['legalentity'] = self.legalentity_list
        self.old_db.objectlinks['individual'] = self.individual_list
        return
