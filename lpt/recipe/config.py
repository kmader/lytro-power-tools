# -*- coding: utf-8 -*-
"""Lytro Power Tools - recipe package - configuration"""

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

# recipe configurations
#
#
#
#
#


import os
import re
import sys
import collections
import ConfigParser

__prog__ = 'recipetool'
__version__ = '1.0.1'

od = collections.OrderedDict


def abspath(p, c): return os.path.abspath(os.path.join(p, c))

dir_module = os.path.dirname(os.path.realpath(__file__))
dir_lpt = abspath(dir_module, '..')
dir_resources = abspath(dir_lpt, 'resources')
dir_schema = abspath(dir_resources, 'schema')

if sys.platform == 'darwin':
    home = os.getenv('HOME')
    lytro_home = abspath(home, 'Library/Application Support/Lytro')
    recipe_version = 4
    schema_dummy = abspath(dir_schema, 'picture_schema_2.1.6_dummy.json')
    schema_file = abspath(dir_schema, 'lfp/picture/2.1.6/picture_schema.json')

elif sys.platform == 'win32':
    profile = os.getenv('USERPROFILE')
    lytro_home = abspath(profile, 'AppData\Local\Lytro')
    recipe_version = 5
    schema_dummy = abspath(dir_schema, 'picture_schema_2.1.7_dummy.json')
    schema_file = abspath(dir_schema, 'lfp/picture/2.1.7/picture_schema.json')

else:
    raise OSError("unsupported operating system: " + sys.platform)

recipe_json = 'recipe.json'
recipe_versions = 1, 2, 3, 4, 5
bools = True, False, None, 0, 1
powertools_cfg = abspath(lytro_home, 'lytro-power-tools.cfg')
auto_buffer = .0001

# user configuration initialization
#
#
#
#
#

config = ConfigParser.ConfigParser()
config.read(powertools_cfg)
write = False

if not config.has_section(__prog__):
    config.add_section(__prog__)
if not os.path.exists(lytro_home):
    os.makedirs(lytro_home)

db = od([
    ('auto_ease', 'in_out'),
    ('auto_shape', 'quad'),
    ('auto_steps', 12),
    ('auto_duration', 10.0),
    ('recipe_version', recipe_version),
    ('verbose', False)
])

for option, value in db.items():
    if config.has_option(__prog__, option):

        config_value = config.get(__prog__, option)

        if re.match(r'^\d+?\.\d+?$', config_value):
            config_value = config.getfloat(__prog__, option)

        elif config_value.isdigit():
            config_value = config.getint(__prog__, option)

        elif config_value.lower() in ('false', 'true'):
            config_value = config.getboolean(__prog__, option)

        elif config_value.lower() == 'none':
            config_value = None

        db[option] = config_value

    else:
        write = True
        config.set(__prog__, option, value)

if write:
    with open(powertools_cfg, 'w') as f:
        config.write(f)
        config.read(powertools_cfg)


# sanity checks
#
#
#
#
#


def _valid(assertion, obj, val, opts=()):
    """:raise: `AssertionError` on invalid configuration items"""

    opt_str = ','.join([str(x) for x in opts])
    err = "invalid {obj} option in {prog}'s configuration ({path}): {val}"
    err = err.format(obj=obj, prog=__prog__, path=powertools_cfg, val=val)
    err += " (options: {})".format(opt_str) if opts else ''
    assert assertion, err


for option, choices in [('recipe_version', recipe_versions)]:

    _valid(db[option] in choices, option, db[option], choices)

_valid(isinstance(db['auto_steps'], int),
       'auto_steps', db['auto_steps'])

_valid(isinstance(db['auto_duration'], float),
       'auto_duration', db['auto_duration'])
