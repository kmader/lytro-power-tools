# -*- coding: utf-8 -*-
"""Lytro Power Tools - web package - configuration"""

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

# web configurations
#
#
#
#
#

import ConfigParser
import collections
import os
import re
import sys

__prog__ = 'webtool'
__version__ = '1.1.2'

od = collections.OrderedDict


def abspath(p, c): return os.path.abspath(os.path.join(p, c))


if sys.platform == 'darwin':
    home = os.getenv('HOME')
    lytro_home = abspath(home, 'Library/Application Support/Lytro')

elif sys.platform == 'win32':
    profile = os.getenv('USERPROFILE')
    lytro_home = abspath(profile, 'AppData\Local\Lytro')

else:
    raise OSError("unsupported operating system: " + sys.platform)

bools = True, False, None, 0, 1

loc_url = "https://pictures.lytro.com"
api_url = "https://api.lytro.com"
host = loc_url.replace('https://', '')

base_headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Lytro-API-version': 3,
    'User-Agent': 'Lytro Web Tool {}'.format(__version__)}

powertools_cfg = abspath(lytro_home, 'lytro-power-tools.cfg')

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
    ('username', None),
    ('password', None),
    ('user_id', None),
    ('auth_token', None),
    ('verbose', False)])

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


_valid(db['verbose'] in bools, 'verbose', db['verbose'], bools)
