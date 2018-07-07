# -*- coding: utf-8 -*-
"""Lytro Power Tools - lfp package - configuration"""

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

# lfptool configurations
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
import multiprocessing

__prog__ = 'lfptool'
__version__ = '1.3.1'

od = collections.OrderedDict


def abspath(p, c): return os.path.abspath(os.path.join(p, c))

dir_module = os.path.dirname(os.path.realpath(__file__))
dir_lpt = abspath(dir_module, '..')

dir_resources = abspath(dir_lpt, 'resources')
dir_schema = abspath(dir_resources, 'schema')
dir_bin = abspath(dir_resources, 'bin')

if sys.platform == 'darwin':
    tnt = abspath(dir_bin, 'tnt')
    home = os.getenv('HOME')
    lytro_home = abspath(home, 'Library/Application Support/Lytro')

elif sys.platform == 'win32':
    tnt = abspath(dir_bin, 'tnt.exe')
    profile = os.getenv('USERPROFILE')
    lytro_home = abspath(profile, 'AppData\Local\Lytro')

else:
    raise OSError("unsupported operating system: " + sys.platform)

output_jsn = '.jsn'
output_lfp = '.lfp'
output_lfr = '.lfr'
output_raw = '.raw'
output_txt = '.txt'
output_xraw = '_xraw'
output_unpacked = '_unpacked'
output_json = '.json'
recipe_json = 'recipe.json'
depthstr = 'warp_depth'
eslfstr = 'eslf'
file_pattern = 'IMG_#'

imagerep_eslf = 'jpeg', 'png'
imagerep_image_out = 'jpeg', 'png', 'tiff', 'bmp', 'exr'
imagerep_lfp_out = 'jpeg', 'png', 'tiff'
depthrep_lfp_out = 'bmp', 'png', 'dat'
depthrep_depth_out = 'bmp', 'png'
bools = True, False, None, 0, 1
cpu_count = multiprocessing.cpu_count()
cpus = range(1, cpu_count + 1)
powertools_cfg = abspath(lytro_home, 'lytro-power-tools.cfg')

if os.path.exists(abspath(lytro_home, 'cameras')):
    dflt_calibration_in = abspath(lytro_home, 'cameras')
else:
    dflt_calibration_in = None

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
    ('calibration_in', dflt_calibration_in),
    ('imagerep_raw_depth_out', 'tiff'),
    ('imagerep_raw_eslf_out', 'png'),
    ('imagerep_raw_image_out', 'tiff'),
    ('imagerep_raw_lfp_out', 'jpeg'),
    ('imagerep_raw_unpack', 'tiff'),
    ('imagerep_warp_pack', 'jpeg'),
    ('imagerep_warp_unpack', 'jpeg'),
    ('depthrep_raw_depth_out', 'png'),
    ('depthrep_raw_lfp_out', 'png'),
    ('depthrep_raw_unpack', 'png'),
    ('depthrep_warp_pack', 'png'),
    ('depthrep_warp_unpack', 'png'),
    ('processors', 1),
    ('validate', True),
    ('verbose', False),
])

for option, value in db.items():
    if config.has_option(__prog__, option):

        config_value = config.get(__prog__, option)

        if re.match(r'^\d+?\.\d+?$', config_value):
            config_value = config.getfloat(__prog__, option)

        elif config_value.isdigit():
            config_value = config.getint(__prog__, option)

        elif config_value in ('False', 'True'):
            config_value = config.getboolean(__prog__, option)

        elif config_value == 'None':
            config.set(__prog__, option, value)
            config_value = value
            write = True

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

for obj, opts in [('imagerep_raw_depth_out', imagerep_image_out),
                  ('imagerep_raw_image_out', imagerep_image_out),
                  ('imagerep_raw_eslf_out', imagerep_eslf),
                  ('imagerep_raw_lfp_out', imagerep_lfp_out),
                  ('imagerep_raw_unpack', imagerep_lfp_out),
                  ('imagerep_warp_pack', imagerep_lfp_out),
                  ('imagerep_warp_unpack', imagerep_lfp_out),
                  ('depthrep_raw_depth_out', depthrep_depth_out),
                  ('depthrep_raw_lfp_out', depthrep_lfp_out),
                  ('depthrep_raw_unpack', depthrep_lfp_out),
                  ('depthrep_warp_pack', depthrep_lfp_out),
                  ('depthrep_warp_unpack', depthrep_lfp_out),
                  ('processors', cpus),
                  ('verbose', bools),
                  ('validate', bools)]:

    opt_str = ', '.join([str(x) for x in opts])
    val = db[obj]

    err = "invalid {} option in {}'s configuration ({}): {}"
    err = err.format(obj, __prog__, powertools_cfg, val)
    err += " (options: {})".format(opt_str) if opts else ''

    assert val in opts, err
