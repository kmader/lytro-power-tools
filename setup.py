#!/usr/bin/env python
# coding=utf-8
"""Lytro Power Tools setuptools installer"""

# -*- coding: utf-8 -*-
# <copyright>
# Copyright (c) 2011-2015 Lytro, Inc. All rights reserved.
# This software is the confidential and proprietary information of Lytro, Inc.
# You shall not disclose such confidential information and shall use it only in
# accordance with the license granted to you by Lytro, Inc.

# EXCEPT AS EXPRESSLY SET FORTH IN A WRITTEN LICENSE AGREEMENT WITH LICENSEE,
# LYTRO, INC. MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY OF
# THE SOFTWARE, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR
# NON-INFRINGEMENT. LYTRO, INC. SHALL NOT BE LIABLE FOR ANY DAMAGES SUFFERED BY
# LICENSEE AS A RESULT OF USING, COPYING, MODIFYING OR DISTRIBUTING THIS
# SOFTWARE OR ITS DERIVATIVES.
# </copyright>

import sys
import os

err = ('''

Lytro Power Tools installation requires Mac OS X or Windows with Python 2
(version 2.7.10 or greater), see Lytro Power Tools documentation for more
information.
''')

os_err = "Invalid operating system: " + sys.platform + err
py_err = "Invalid Python version: " + sys.version + err

if not (2, 7, 10) <= sys.version_info < (3, 0, 0):
    sys.stderr.write(py_err)
    exit(1)

if sys.platform not in ('darwin', 'win32'):
    sys.stderr.write(os_err)
    exit(1)

try:
    from setuptools import setup
    from setuptools import find_packages
except ImportError as e:
    setup = None
    find_packages = None
    raise Exception(e)

try:
    import numpy
    import scipy
except ImportError:

    e = ('''
numpy or scipy is missing; refer to Python or the Lytro Power Tools
documentation for help on installing these modules before running
``python setup.py install``
''')

    numpy = scipy = None

    if sys.platform == 'win32':
        sys.stderr.write(e)
        exit(1)

    try:
        import pip
    except ImportError:
        pip = None
        sys.stderr.write(e)
        exit(1)
    else:
        pip.main(['install', 'numpy'])
        pip.main(['install', 'scipy'])

if sys.platform == 'win32':
    profile = os.getenv('USERPROFILE')
    lytro_home = os.path.join(profile, 'AppData\Local\Lytro')
    cfg_file = os.path.join(lytro_home, 'lytro-power-tools.cfg')
    if os.path.exists(cfg_file):
        import ConfigParser
        cfg = ConfigParser.ConfigParser()
        cfg.read(cfg_file)
        if cfg.has_section('recipetool'):
            cfg.set('recipetool', 'recipe_version', 5)
            with open(cfg_file, 'w') as f:
                cfg.write(f)

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

with open('LICENSE') as license_file:
    license_ = license_file.read()

setup(
    name='lytro-power-tools',
    version='1.0.1b0',
    description="Lytro camera control and light field image processing",
    long_description=readme + '\n\n' + history,
    author='Lytro, Inc.',
    author_email='support@lytro.com',
    license='LYTRO POWER TOOLS (BETA) LICENSE AGREEMENT',
    url='https://www.lytro.com/platform/power-tools/',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    setup_requires=['numpy'],
    install_requires=[
        'jsonschema',
        'dictdiffer',
        'numpy',
        'scipy',
        'pytweening'],
    entry_points={
        'console_scripts': [
            'lfptool = lpt.bin.lfptool:build',
            'recipetool = lpt.bin.recipetool:build',
            'webtool = lpt.bin.webtool:build',
            'cameratool = lpt.bin.cameratool:main',
            'cameracontrols = lpt.bin.cameracontrols:main',
        ]
    }
)
