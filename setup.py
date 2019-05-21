# -*- coding: utf-8 -*-
'''
setup module to pip integration of Lucterios contacts

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


from setuptools import setup
from lucterios.contacts import __version__

setup(
    name="lucterios-contacts",
    version=__version__,
    author="Lucterios",
    author_email="info@lucterios.org",
    url="http://www.lucterios.org",
    description="contacts managment module for Lucterios framework.",
    long_description="""
    contacts managment module for Lucterios framework.
    """,
    include_package_data=True,
    platforms=('Any',),
    license="GNU General Public License v3",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django :: 2.0',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Natural Language :: French',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Database :: Front-Ends',
    ],
    packages=["lucterios", "lucterios.contacts", "lucterios.mailing"],
    package_data={
        "lucterios.contacts.migrations": ['*'],
        "lucterios.contacts": ['build', 'images/*', 'locale/*/*/*', 'help/*'],
        "lucterios.mailing.migrations": ['*'],
        "lucterios.mailing": ['build', 'images/*', 'locale/*/*/*', 'help/*'],
    },
    install_requires=["lucterios ==2.3.*", "Pillow ==5.4.*", "lucterios-documents ==2.3.*", "dkimpy ==0.9.*", "html2text ==2018.1.*"],
)
