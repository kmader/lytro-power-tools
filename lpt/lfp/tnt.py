# -*- coding: utf-8 -*-
"""Lytro Power Tools - lfp package - tnt (Lytro lightfield engine) executor"""

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

import subprocess
import functools
import sys
import collections

from lpt.lfp import config
from lpt.utils.argutils import ArgUtils
from lpt.utils.jsonutils import JsonUtils
from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.utils.utils import Utils

argutils = ArgUtils()
utils = Utils()
jsonutils = JsonUtils()
msgutils = MsgUtils()

od = collections.OrderedDict
arg_format = argutils.arg_format
key_arg = functools.partial(argutils.arg_format, split='_', join='-', pre='--')


class Tnt(object):
    """class wrapper for interacting with TNT binary

    1) TNT commands can be built, then executed:

        from lpt.lfp.tnt import Tnt
        tnt = Tnt()
        tnt.lfp_in('foo.lfp')
        tnt.lfp_out('bar.lfp')
        tnt.imagerep('jpeg')
        tnt.execute()

    2) they can be daisy-chained off one another:

        from lpt.lfp.tnt import Tnt
        tnt = Tnt()

        tnt.lfp_in('foo.lfp').lfp_out('bar.lfp').imagerep('jpeg').execute()

    3) passed with kwargs during instantiation:

        from lpt.lfp.tnt import Tnt
        tnt = Tnt(lfp_in='foo.lfp', lfp_out='bar.lfp', imagerep='jpeg')
        tnt.execute()

    all three examples resulting in the same TNT command:

    $ tnt --lfp-in foo.lfp --lfp-out bar.lfp --imagerep jpeg

    upon execution, the command queue is emptied, so the tnt instance
    can be re-used:

    tnt.lfp_in('foo.lfp').lfp_out('bar0.lfp').recipe_in('rec0.json').execute()
    tnt.lfp_in('foo.lfp').lfp_out('bar1.lfp').recipe_in('rec1.json').execute()
    tnt.lfp_in('foo.lfp').lfp_out('bar2.lfp').recipe_in('rec2.json').execute()

    :param verbose: `bool`, increase verbosity, i.e., show TNT output
    :param kwargs: `dict`, TNT parameters to set when `Tnt` is instantiated
    :raise: `ToolError` if invalid keyword arguments specified
    """

    _exe = config.tnt
    _command = [_exe]
    print_help = object

    def __init__(self, verbose=False, **kwargs):

        self.verbose = verbose
        self.arg_sets = []
        self.init()

        self.calibration_in = CalibrationIn(self)
        self.depth_in = DepthIn(self)
        self.depth_out = DepthOut(self)
        self.depthrep = Depthrep(self)
        self.depthrep_depth = Depthrep(self, depth_out=True)
        self.dir_out = DirOut(self)
        self.eslf_out = EslfOut(self)
        self.focus = Focus(self)
        self.height = Height(self)
        self.help_ = Help(self)
        self.ignore_rest = IgnoreRest(self)
        self.image_out = ImageOut(self)
        self.imagerep = Imagerep(self)
        self.imagerep_lfp = Imagerep(self, lfp=True)
        self.imagerep_eslf = Imagerep(self, eslf=True)
        self.lfp_in = LfpIn(self)
        self.lfp_out = LfpOut(self)
        self.lfp2raw = Lfp2Raw(self)
        self.lfr2xraw = Lfr2Xraw(self)
        self.orientation = Orientation(self)
        self.perspective_u = PerspectiveU(self)
        self.perspective_v = PerspectiveV(self)
        self.raw_in = RawIn(self)
        self.raw_out = RawOut(self)
        self.raw2lfp = Raw2Lfp(self)
        self.recipe_in = RecipeIn(self)
        self.recipe_out = RecipeOut(self)
        self.threads = Threads(self)
        self.transcode = self.pack = Transcode(self)
        self.unpack = Unpack(self)
        self.version = Version(self)
        self.width = Width(self)

        self.actions = self.dests(filter_group='action', combine=False)

        for arg, value in kwargs.items():
            e = "tnt argument not found: {}".format(arg)
            assert arg in vars(self), ToolError(e, self.print_help)
            cls = vars(self)[arg]
            cls(value)

    def set_print_help(self, print_help):
        """sets `argparse` help menu for current command
        :param print_help: `object`, passed to ToolError for command help menu
        """

        self.print_help = print_help
        argutils.set_print_help(print_help)
        jsonutils.set_print_help(print_help)
        utils.set_print_help(print_help)

    @property
    def cmd_queue(self):
        """str version of the current TNT command

        :return: formatted string
        """

        return ' '.join([str(s) for s in self._command])

    def init(self):
        """reinitialize TNT command (empties command build)"""

        self._command = [self._exe]
        self.arg_sets = []

    def argument(self, arg, val=None, multi=False):
        """adds argument and value to TNT command

        :param arg: `str`, argument flag to set
        :param val: `str`, value of the argument (if applicable)
        :param multi: `bool`, (dis)allows an argument to be more than once
        :raise: `ToolError` if argument is already in the built command
        """

        if arg in self._command and not multi:
            e = "argument already set: {}".format(arg)
            raise ToolError(e, self.print_help)

        if val is True:
            set_ = [arg]
        elif utils.any_(val, bool_=False):
            set_ = [arg, str(val)]
        else:
            set_ = []

        if set_:
            self._command.extend(set_)
            self.arg_sets.append(set_)

    def execute(self, failure=object, lock=None):
        """executes the TNT command

        :param failure: `object`, function to execute upon tnt failure
        :param lock: `multiprocessing.Lock` used with multiprocessing to avoid
                     processes from writing to stdout
        """

        if self.verbose:

            def quotes(): return '"{}"'.format(x) if ' ' in x else x
            command = [quotes() for x in self._command]
            command = ' '.join(command)

            if not lock:

                msgutils.msg(self._command[0])
                rjust = max(len(i[0]) for i in self.arg_sets) + 1

                for row in self.arg_sets:
                    arg = row[0].rjust(rjust)
                    val = " : {}".format(row[1]) if len(row) > 1 else ''
                    msgutils.msg('\t' + arg + val, indent=True)

        else:
            command = self._command

        sp = subprocess.Popen(command,
                              shell=self.verbose,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)

        if self.verbose:
            stderr = None
            while not sp.poll():
                stdout = sp.stdout.readline()

                if stdout and not lock:
                    sys.stdout.write(stdout)
                else:
                    stderr = sp.stderr.readline()
                    if stderr:
                        sys.stderr.write(stderr)
                    break

            if sp.returncode or stderr:
                failure()

        else:
            stdout, stderr = sp.communicate()
            if stderr or sp.returncode:
                sys.stderr.write('\r\n' + stderr)
                failure()

        self.init()

    @staticmethod
    def dests(filter_group=None, combine=True, mode=None):
        """filter for all destinations in `tnt` classes sorted by group

        :param filter_group: `str`, filter destinations by group name
        :param combine: `bool`, combine result into list, else a grouped dict
        :param mode: `str`, filter destinations by mode
        :return: resulting destinations
        """

        group_dests = od()
        module = sys.modules[__name__]

        for obj in dir(module):

            attr = getattr(module, obj)
            if 'dest' not in dir(attr):
                continue

            group = attr.group
            dest = attr.const if group == 'action' else attr.dest
            modes = attr.modes

            if group == 'meta':
                continue
            if filter_group and filter_group is not group:
                continue
            if mode and mode not in modes:
                continue

            if group not in group_dests:
                group_dests[group] = []

            group_dests[group].append(dest)

        all_dests = [d for g in group_dests.values() for d in g]

        return group_dests if combine else all_dests


class _Partial(functools.partial):
    """wrapper for functools.partial; overrides __repr__ to be blank"""

    def __repr__(self):
        return '\b'


class _TntParser(object):
    """base tnt parameter class for interacting with argparse"""

    action = None
    choices = None
    const = None
    default = None
    dest = None
    help_ = None
    metavar = None
    nargs = None
    required = None
    type_ = None
    arg_alt = None

    group = 'meta'
    modes = 'meta'
    actions = ()
    allowed = ()
    overrides = ()


class CalibrationIn(_TntParser):
    """calibration data directory

    :param cls: `Tnt` object for pass through
    """

    dest = 'calibration_in'
    default = config.db['calibration_in']
    help_ = __doc__.split('\n')[0]
    arg = key_arg(dest)
    metavar = argutils.path_meta
    type_ = _Partial(argutils.calibration_dir, arg=arg)

    group = 'input'
    actions = ('image_out', 'lfp_out', 'unpack', 'eslf_out', 'lfr2xraw',
               'depth_out')
    modes = 'raw', 'batch'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class DepthIn(_TntParser):
    """input BMP or PNG depth map

    :param cls: `Tnt` object for pass through
    """

    dest = 'depth_in'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(dest)
    type_ = _Partial(argutils.valid_file, arg=arg, type_='depthmap file')

    group = 'input'
    actions = 'image_out', 'lfp_out', 'unpack', 'depth_out'
    modes = 'raw', 'batch'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class DepthOut(_TntParser):
    """output depth map

    :param cls: `Tnt` object for pass through
    """

    const = 'depth_out'
    action = 'store_const'
    dest = '{}_action'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(const)
    type_ = str

    group = 'action'
    actions = 'depth_out',
    modes = 'raw',

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Depthrep(_TntParser):
    """depth map representation

    :param cls: `Tnt` object for pass through
    :param depth_out: `bool`, specifies if object is being used with `DepthOut`
    """

    dest = 'depthrep'
    help_ = __doc__.split('\n')[0]
    arg = key_arg(dest)

    group = 'representation'
    actions = 'lfp_out', 'unpack', 'depth_out'
    modes = 'raw', 'warp'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls, depth_out=False):
        self.cls = cls
        self.execute = cls.execute

        if depth_out:
            self.choices = config.depthrep_depth_out
        else:
            self.choices = config.depthrep_lfp_out

        self.type_ = _Partial(argutils.choice, choices=self.choices,
                              arg=self.arg)


class DirOut(_TntParser):
    """output directory (default: output to the source LFP file's directory)

    :param cls: `Tnt` object for pass through
    """

    dest = 'dir_out'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(dest)
    type_ = _Partial(argutils.str_, arg=arg)

    group = 'output'
    actions = ('depth_out', 'eslf_out', 'image_out', 'lfp2raw', 'lfp_out',
               'lfr2xraw', 'raw2lfp', 'recipe_out', 'unpack')
    modes = 'raw', 'warp', 'batch'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class EslfOut(_TntParser):
    """output standardized lightfield

    :param cls: `Tnt` object for pass through
    """

    const = 'eslf_out'
    action = 'store_const'
    dest = '{}_action'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(const)
    type_ = str

    group = 'action'
    actions = 'eslf_out',
    modes = 'raw',

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Focus(_TntParser):
    """one element of the lambda list

    :param cls: `Tnt` object for pass through
    """

    dest = 'focus'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.float_meta
    arg = key_arg(dest)
    type_ = _Partial(argutils.number, arg=arg)

    group = 'perspective'
    actions = 'image_out',
    modes = 'raw',

    def __call__(self, value):
        value = self.type_(value) if (value or value == 0) else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Height(_TntParser):
    """output y resolution

    :param cls: `Tnt` object for pass through
    """

    dest = 'height'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.int_meta
    arg = key_arg(dest)
    type_ = _Partial(argutils.number, type_=int, arg=arg)

    group = 'window'
    actions = 'image_out', 'lfp_out', 'unpack'
    modes = 'raw', 'warp', 'batch'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Help(_TntParser):
    """displays usage information and exits

    :param cls: `Tnt` object for pass through
    """

    dest = 'help'
    action = 'store_true'
    help_ = __doc__.split('\n')[0]
    arg = key_arg(dest)

    group = 'meta'
    actions = ()
    modes = 'meta',

    def __call__(self, value=True):
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class ImageOut(_TntParser):
    """output image file

    :param cls: `Tnt` object for pass through
    """

    const = 'image_out'
    action = 'store_const'
    dest = '{}_action'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(const)
    type_ = str

    group = 'action'
    actions = 'image_out',
    allowed = 'calibration_in',
    modes = 'raw',

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Imagerep(_TntParser):
    """image representation

    :param cls: `Tnt` object for pass through
    :param eslf: `bool`, specifies if object is being used with `Eslf`
    :param lfp: `bool`, specifies if object is being used with `LfpOut`
    """

    dest = 'imagerep'
    help_ = __doc__.split('\n')[0]
    arg = key_arg(dest)

    group = 'representation'
    actions = 'image_out', 'lfp_out', 'unpack', 'eslf_out', 'depth_out'
    modes = 'raw', 'warp', 'batch'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls, eslf=False, lfp=False):
        self.cls = cls
        self.execute = cls.execute

        if lfp:
            self.choices = config.imagerep_lfp_out
        elif eslf:
            self.choices = config.imagerep_eslf
        else:
            self.choices = config.imagerep_image_out

        self.type_ = _Partial(argutils.choice, choices=self.choices,
                              arg=self.arg)


class IgnoreRest(_TntParser):
    """ignores the rest of the labeled arguments following this flag

    :param cls: `Tnt` object for pass through
    """

    dest = 'ignore_rest'
    action = 'store_true'
    arg = key_arg(dest)
    help_ = __doc__.split('\n')[0]

    group = 'meta'
    actions = ()
    modes = 'meta',

    def __call__(self, value=True):
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Lfp2Raw(_TntParser):
    """unpackage RAW and corresponding TXT from an LFP container

    :param cls: `Tnt` object for pass through
    """

    const = 'lfp2raw'
    action = 'store_const'
    dest = '{}_action'
    help_ = __doc__.split('\n')[0]
    arg = key_arg(const)

    group = 'action'
    actions = 'lfp2raw',
    modes = 'raw',

    def __call__(self, value=True):
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class LfpIn(_TntParser):
    """input LFP file

    :param cls: `Tnt` object for pass through

    """

    dest = 'lfp_in'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(dest)
    type_ = _Partial(argutils.str_, arg=arg)

    group = 'meta'
    actions = ('image_out', 'lfp_out', 'unpack', 'eslf_out', 'lfr2xraw',
               'depth_out')
    modes = 'raw', 'warp', 'batch'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class LfpOut(_TntParser):
    """output warp LFP file

    :param cls: `Tnt` object for pass through
    """

    const = 'lfp_out'
    action = 'store_const'
    dest = '{}_action'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(const)
    type_ = str

    group = 'action'
    actions = 'lfp_out', 'unpack', 'lfr2xraw'
    modes = 'raw', 'warp'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Lfr2Xraw(_TntParser):
    """output XRAW LFR

    :param cls: `Tnt` object for pass through
    """

    const = 'lfr2xraw'
    action = 'store_const'
    dest = '{}_action'
    help_ = __doc__.split('\n')[0]
    arg = key_arg(const)

    group = 'action'
    actions = 'lfr2xraw',
    modes = 'raw',

    def __call__(self, value=True):
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Orientation(_TntParser):
    """orientation enumeration 1-8, matches EXIF definitions (default: 1)

    :param cls: `Tnt` object for pass through
    """

    dest = 'orientation'
    choices = [str(i) for i in range(1, 9)]
    help_ = __doc__.split('\n')[0]
    metavar = argutils.int_meta
    arg = key_arg(dest)
    type_ = _Partial(argutils.choice, choices=choices, arg=arg)

    group = 'window'
    actions = 'image_out', 'lfp_out', 'unpack', 'depth_out'
    modes = 'raw'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class PerspectiveU(_TntParser):
    """one element of the horizontal viewpoint list

    :param cls: `Tnt` object for pass through
    """

    dest = 'perspective_u'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.float_meta
    nargs = '+'
    arg = key_arg(dest)
    type_ = _Partial(argutils.number, arg=arg)
    default = []

    group = 'perspective'
    actions = 'image_out', 'lfp_out', 'unpack'
    modes = 'raw', 'batch'

    def __call__(self, value):
        if not isinstance(value, list):
            value = [value]
        for val in value:
            val = self.type_(val) if (val or val == 0) else None
            self.cls.argument(self.arg, val, multi=True)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class PerspectiveV(_TntParser):
    """one element of the vertical viewpoint list

    :param cls: `Tnt` object for pass through
    """

    dest = 'perspective_v'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.float_meta
    nargs = '+'
    arg = key_arg(dest)
    type_ = _Partial(argutils.number, arg=arg)
    default = []

    group = 'perspective'
    actions = 'image_out', 'lfp_out', 'unpack'
    modes = 'raw', 'batch'

    def __call__(self, value):
        if not isinstance(value, list):
            value = [value]
        for val in value:
            val = self.type_(val) if (val or val == 0) else None
            self.cls.argument(self.arg, val, multi=True)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Raw2Lfp(_TntParser):
    """package RAW and corresponding TXT within an LFP container

    :param cls: `Tnt` object for pass through
    """

    const = 'raw2lfp'
    action = 'store_const'
    dest = '{}_action'
    help_ = __doc__.split('\n')[0]
    arg = key_arg(const)

    group = 'action'
    actions = 'raw2lfp',
    modes = 'raw',

    def __call__(self, value=True):
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class RawIn(_TntParser):
    """input RAW file

    :param cls: `Tnt` object for pass through
    """

    dest = 'raw_in'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(dest)
    type_ = _Partial(argutils.str_, arg=arg)

    group = 'meta'
    actions = 'raw2lfp',
    modes = 'raw',

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class RawOut(_TntParser):
    """output RAW file

    :param cls: `Tnt` object for pass through
    """

    dest = 'raw_out'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(dest)
    type_ = _Partial(argutils.str_, arg=arg)

    group = 'meta'
    actions = 'lfp2raw',
    modes = 'raw',

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class RecipeIn(_TntParser):
    """input view parameter json file

    :param cls: `Tnt` object for pass through
    """

    dest = 'recipe_in'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(dest)
    type_ = _Partial(argutils.json_file)

    group = 'input'
    actions = 'image_out', 'lfp_out', 'unpack'
    modes = 'raw', 'batch'
    overrides = 'perspective_u', 'perspective_v', 'focus', 'orientation'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class RecipeOut(_TntParser):
    """output LFP view parameters

    :param cls: `Tnt` object for pass through
    """

    const = 'recipe_out'
    action = 'store_const'
    dest = '{}_action'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.path_meta
    arg = key_arg(const)
    type_ = str

    group = 'action'
    actions = 'recipe_out',
    modes = 'raw', 'warp'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Threads(_TntParser):
    """number of processing threads (per LFE instance)

    :param cls: `Tnt` object for pass through
    """

    dest = 'threads'
    arg = key_arg(dest)
    help_ = __doc__.split('\n')[0]
    metavar = argutils.int_meta
    type_ = _Partial(argutils.number, type_=int, arg=arg)

    group = 'threads'
    actions = ('image_out', 'lfp_out', 'unpack', 'eslf_out', 'lfr2xraw',
               'depth_out')
    modes = 'raw', 'warp', 'batch'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Transcode(_TntParser):
    """transcodes warp LFP files

    :param cls: `Tnt` object for pass through
    """

    const = 'transcode'
    action = 'store_const'
    dest = '{}_action'
    help_ = __doc__.split('\n')[0]
    arg = key_arg(const)
    const_alt = 'pack'
    arg_alt = key_arg(const_alt)
    help_alt = "output packed LFP from unpacked LFP asset"

    group = 'action'
    actions = 'lfp_out',
    modes = 'warp',

    def __call__(self, value=True):
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Unpack(_TntParser):
    """output non-packed LFP asset (default action)

    :param cls: `Tnt` object for pass through
    """

    const = 'unpack'
    action = 'store_const'
    dest = '{}_action'
    help_ = __doc__.split('\n')[0]
    arg = key_arg(const)

    group = 'action'
    actions = 'unpack',
    modes = 'raw', 'warp'

    def __call__(self, value=True):
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Version(_TntParser):
    """displays version information and exits

    :param cls: `Tnt` object for pass through
    """

    dest = 'version'
    action = 'store_true'
    arg = key_arg(dest)
    help_ = __doc__.split('\n')[0]

    group = 'meta'
    actions = ()
    modes = 'meta',

    def __call__(self, value=True):
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute


class Width(_TntParser):
    """output x resolution

    :param cls: `Tnt` object for pass through
    """

    dest = 'width'
    help_ = __doc__.split('\n')[0]
    metavar = argutils.int_meta
    arg = key_arg(dest)
    type_ = _Partial(argutils.number, type_=int, arg=arg)

    group = 'window'
    actions = 'image_out', 'lfp_out', 'unpack'
    modes = 'raw', 'warp', 'batch'

    def __call__(self, value):
        value = self.type_(value) if value else None
        self.cls.argument(self.arg, value)
        return self.cls

    def __init__(self, cls):
        self.cls = cls
        self.execute = cls.execute
