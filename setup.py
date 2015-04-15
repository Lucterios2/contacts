# -*- coding: utf-8 -*-
'''
Created on fevr. 2015

@author: sd-libre
'''

from setuptools import setup
from lucterios.contacts import __version__

setup(
    name="lucterios-contacts",
    version=__version__,
    author="Lucterios",
    author_email="support@lucterios.org",
    url="http://www.lucterios.org",
    description="contacts managment module for Lucterios.",
    long_description="""
    contacts managment module for Lucterios.
    """,
    include_package_data=True,
    platforms=('Any',),
    license="GNU General Public License v2",
    # Packages
    packages=["lucterios", "lucterios.contacts"],
    package_data={
       "lucterios.contacts.migrations":['*'],
       "lucterios.contacts":['build', 'images/*', 'locale/*/*/*', 'help/*'],
    },
    install_requires=["lucterios >=2.0b0,<2.0b9999", "Pillow ==2.8"],
)
