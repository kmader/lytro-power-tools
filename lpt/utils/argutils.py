# -*- coding: utf-8 -*-
"""Lytro Power Tools - utilities package - shared argument parsing utilities"""

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

import argparse
import datetime
import glob
import multiprocessing
import os
import re
import pytweening

from numpy import less_equal as le
from numpy import greater_equal as ge

from lpt.utils.utils import Utils
from lpt.utils.jsonutils import JsonUtils
from lpt.utils.msgutils import ToolError

utils = Utils()
jsonutils = JsonUtils()


class ArgUtils(object):
    """Lytro Power Tools argument types and utilities"""

    int_meta = 'INT'
    float_meta = 'FLOAT'
    positive_meta = '+NUMBER'
    negative_meta = '-NUMBER'
    path_meta = 'PATH'
    file_float = 0

    _manifest_json = 'cal_file_manifest.json'

    min_max = "(min: {min_} | max: {max_})"
    bad_range = "{arg}: value out of range '{obj}' " + min_max
    bad_amt = "{arg}: invalid amount of items ({obj}) " + min_max
    bad_path = "{arg}: invalid {type_}: '{path_in}'"

    print_help = object

    def set_print_help(self, print_help):
        """sets `argparse` help menu for current command

        :param print_help: `object`, passed to ToolError for command help menu
        """

        self.print_help = print_help
        utils.set_print_help(print_help)
        jsonutils.set_print_help(print_help)

    def _arg(self, arg):
        pre = '' if arg.startswith('-') else '--'
        return self.arg_format(arg, split='_', join='-', pre=pre)

    def all_or_none(self, allow_none=True, index=None, **kwargs):
        """requires all kwargs have values

        :param kwargs: keyword args parsed through for values
        :param allow_none: `bool`,, allows all kwargs to not have value
        :param index: `int`, indicates that kwargs are a subset of an array and
                      changes the assertion error to include an index number
        :return: dict object of kwargs if values present, empty dict if not
        :raise: `ToolError` specified `kwargs` that both do/don't have values
        """

        def arg_str(l): return ', '.join([self._arg(x) for x in l])

        values = kwargs.values()
        any_ = utils.any_(values, iter_=False)
        all_ = utils.all_(values, iter_=False)

        set_args = [k for k, v in kwargs.items() if v]
        not_set_args = [k for k, v in kwargs.items() if not v]

        req = [k for k in set_args if k not in not_set_args]
        req_args = kwargs if set_args else {}

        must = not (any_ and not all_) if allow_none else all_

        e = ("{set_}: requires additional arguments; "
             "{not_} not set".format(set_=arg_str(req),
                                     not_=arg_str(not_set_args)))

        if index:
            e = "index {}: ".format(index) + e

        assert must, ToolError(e, self.print_help)
        return req_args

    @staticmethod
    def arg_choices(args):
        """generates a string with available choices for a given argparse arg

        :param args: `str`/`list`, arguments that conflict
        :return: formatted string
        """

        if not args:
            return ''
        return "[choices: {}]".format(','.join(args))

    @staticmethod
    def arg_conflict(args, switch='-'):
        """generates a string noting conflicting arguments for argparse

        :param args: `str`/`list`, arguments that conflict
        :param switch: `str`, prepended to each arg to not the arg switch
        :return: formatted string
        """

        if not args:
            return ''

        conflicts = '/'.join([switch + s for s in args])
        return "[conflicts: {}]".format(conflicts)

    @staticmethod
    def arg_default(default):
        """generates a string noting a default value for an argparse argument

        :param default: `object`, default value
        :return: formatted string
        """

        if not utils.any_(default, iter_=False):
            return ''
        return "(default: {})".format(str(default))

    @staticmethod
    def arg_format(str_, rm='', split='', join='', pre='', ver=False,
                   camel=False):
        """formats passed in string to the specified argument format

        :param str_: `str`, string to format
        :param rm: `str`, removes value from str_
        :param split: `str`, replaces value with join value
        :param join: `str`, value replaced when split is called
        :param pre: `str`, prepended to arguments
        :param ver: `bool`, removes integers at the end of str_
        :param camel: `bool`, converts str_ from camel case
        :return: formatted argument string
        """

        s = str_

        if rm:
            s = re.sub(rm, '', s)
        if camel and join:
            s = utils.camel_split(s, join=join)
        if split and join:
            s = re.sub(split, join, s)
        if ver:
            s = re.sub('[0-9]+', '', s)

        return pre + s

    def assert_len(self, props, len_=1):
        """assert that values in a dictionary are of an acceptable length

        :param props: `dict`, dictionary to parse through
        :param len_: acceptable length of dictionary values
        :raise: `ToolError` if `len_` does not match length of `props`
        """

        for key, value in props.items():
            arg = self._arg(key)
            e = arg + ": only {} value can be specified".format(len_)
            l = len(value) if hasattr(value, '__len__') else 1
            assert l == len_, ToolError(e, self.print_help)

    def boolean(self, obj, arg=None):
        """checks if object is boolean

        :param obj: `object`, object to check
        :param arg: `str`, argument used for the call
        :return: `obj` if bool
        :raise: `ToolError` if `obj` not boolean
        """

        if isinstance(obj, bool):
            return obj

        arg = self._arg(arg)
        e = "{}: expected boolean value: {}".format(arg, obj)
        raise ToolError(e, self.print_help)

    def calibration_dir(self, dir_path_in, arg=None):
        """verifies that a inputted path is an actual calibration directory

        :param dir_path_in: `str`, path to check
        :param arg: `str`, argument used for the call
        :return: absolute path to `dir_path_in` if valid
        :raise: `ToolError` if `dir_path_in` is invalid
        """

        if dir_path_in is False:
            return dir_path_in

        dir_path = utils.full_path(dir_path_in)

        if os.path.isdir(dir_path):
            list_dir = os.listdir(dir_path)
            for obj in list_dir:
                path = os.path.join(dir_path, obj)
                if not os.path.isdir(path):
                    continue

                manifest = os.path.join(path, self._manifest_json)
                if os.path.exists(manifest):
                    return dir_path

                raw = os.path.join(path, '*.RAW')
                if glob.glob(raw):
                    return dir_path

                calib = os.path.join(path, 'Calibration')
                if os.path.exists(calib):
                    gct = os.path.join(calib, '*.GCT')
                    if glob.glob(gct):
                        return dir_path

        arg = self._arg(arg)
        e = self.bad_path.format(arg=arg, path_in=dir_path_in,
                                 type_='calibration directory')
        raise ToolError(e, self.print_help)

    def choice(self, obj, choices, arg=None, convert=str):
        """checks if a object is in a container of available choices

        emulates argparse 'choices' function

        :param obj: `object`, object to check
        :param choices: `iter`, container of available choices
        :param arg: `str`, argument used for the call
        :param convert: `type`, convert object to specified type
        :return: `obj` if `obj` is in choices
        :raise: `ToolError` if `obj` not in `choices` or `convert` fails
        """

        choices = [str(x) for x in choices]
        arg = self._arg(arg)
        e = ("{arg}: invalid choice: {obj} (choose from {choices})"
             .format(arg=arg, obj=obj, choices=', '.join(choices)))

        if str(obj) in choices:
            try:
                return convert(obj)
            except ValueError:
                raise ToolError(e, self.print_help)

        raise ToolError(e, self.print_help)

    def ease_function(self, ease, shape):
        """converts an acceleration and shape to a pytweening easing function

        see `self.easers` for available accelerations and shapes

        :param shape: `str`, pytweening ease shape (underscore format)
        :param ease: `str`, pytweening ease acceleration (underscore format)
        :return: pytweening easing function
        :raise: `ToolError` if easing function not available in `pytweening`
        """

        if shape == 'linear':
            return pytweening.linear

        func = utils.camel_join('_'.join(['ease', ease, shape]))
        e = "invalid easing function: {} - {}".format(ease, shape)
        assert func in dir(pytweening), ToolError(e, self.print_help)
        return getattr(pytweening, func)

    @property
    def easers(self):
        """:return all available pytweening functions"""

        shapes = ['linear']
        eases = []
        ease_dir = [x for x in dir(pytweening) if x.startswith('ease')]

        for i in ease_dir:
            keys = utils.camel_split(i).split('_')
            shape = keys[-1]
            ease = '_'.join(keys[1:-1])
            if ease not in eases:
                eases.append(ease)
            if shape not in shapes:
                shapes.append(shape)

        return eases, shapes

    @staticmethod
    def formatter_class(w=120, m=32, raw=True):
        """centralized argparse formatter class for LFP Tool

        provides default formatting for help menus

        :param w: `int`, attempted console width
        :param m: `int`, attempted help column width
        :param raw: `bool`, use argparse raw description formatter
        :return: argparse formatter with defined w/m/raw arguments
        """

        if raw:
            formatter = argparse.RawDescriptionHelpFormatter
        else:
            formatter = argparse.HelpFormatter

        return lambda prog: formatter(prog, width=w, max_help_position=m)

    def in_range(self, obj, arg=None, range_=(0, 0), type_=int, clip=True):
        """verifies if a number is in range of the specified range

        :param obj: `int`/`float`, object to check
        :param arg: `str`, argument used for the call
        :param range_: `tuple`, range to check if object is in
        :param type_: `int`/`float`, expected type
        :param clip: `bool`, adjust value to be within requested range
        :return: ``self.number(obj)`` if number in range
        :raise: `ToolError` if `obj` not in range
        """

        min_, max_ = range_
        num = self.number(obj, arg=arg, type_=type_)
        num = int(round(num)) if type_ is int else num
        arg = self._arg(arg)
        lt_gt = self.lt_gt(num, min_, max_)

        if not clip:
            e = self.bad_range.format(obj=obj, arg=arg, min_=min_, max_=max_)
            assert lt_gt is not False, ToolError(e, self.print_help)

        if lt_gt is False:
            max_closer = (num - min_) > abs(num - max_)
            num = max_ if max_closer else min_

        return num

    def json_file(self, file_path_in):
        """verifies that a inputted file is a valid JSON file

        :param file_path_in: `str`, input path to check
        :return: file path if valid
        :raise: `ToolError` if `file_path_in` does not contain JSON data
        """

        file_path = utils.full_path(file_path_in)
        json_data = jsonutils.data(file_path)
        e = "invalid JSON file: " + file_path_in
        assert json_data or json_data == {}, ToolError(e, self.print_help)
        return file_path

    def lens_match(self, **kwargs):
        """checks that all values in kwargs are of equal length

        :param kwargs: `dict`,, standard Python **kwargs convention
        :raise: `ToolError` if `kwargs` values do not match length
        """

        keys = kwargs.keys()
        values = kwargs.values()

        max_len = max([len(v) for v in values])
        match = all([len(x) == max_len for x in values])

        lens = ['{}={}'.format(k, len(v)) for k, v in kwargs.items()]

        e = ("{set_}: each argument must contain the same "
             "amount of values; {not_}".format(set_=', '.join(keys),
                                               not_=' != '.join(lens)))

        assert match, ToolError(e, self.print_help)
        return True

    @staticmethod
    def lt_gt(num, min_=0, max_=0):
        """checks if a number is within an allowed range

        :param num: `int`/`float`, number to check
        :param min_: `int`, minimum value
        :param max_: `int`, maximum value
        :return: number if in range else False
        """

        if min_ is 0 and max_ is 0:
            return num
        elif (min_ or min_ == 0) and max_:
            if le(min_, num) and le(num, max_):
                return num
        elif min_ or min_ == 0:
            if ge(num, min_):
                return num
        elif max_ or max_ == 0:
            if le(num, max_):
                return num

        return False

    @staticmethod
    def meta_range(range_):
        """generates a metavar string for argparse

        :param range_: `tuple`, low/high range to parse
        :return: formatted string
        """

        x = range_[0]
        y = range_[1]
        return '{{{x}..{y}}}'.format(x=x, y=y).replace('None', '..')

    def mutual(self, arg, **kwargs):
        """verifies that mutually exclusive arguments were not passed

        emulates `argparse.ArgumentParser.mutually_exclusive_group`

        :param arg: `str`, argument to verify against
        :param kwargs: `dict`, standard python convention
        :raise: `ToolError` if an allowed argument is used with `arg`
        """

        have_val = utils.flatten(kwargs, iter_=False)

        if not have_val:
            return

        arg = self._arg(arg)
        con = self._arg(have_val.keys()[0])
        e = "{}: not allowed with {}".format(arg, con)
        raise ToolError(e, self.print_help)

    def number(self, obj, arg=None, type_=float):
        """verifies if a obj is an int or float

        :param obj: `int`/`float`, object to check
        :param arg: `str`, argument used for the call
        :param type_: `int`/`float`, impose type (`int` or `float`)
        :return: `int` if `int` or `obj` % 1 == 0, `float` if `float`
        :raise: `ToolError` if `obj` cannot be converted to a number
        """

        if isinstance(obj, (float, int)):
            return type_(obj)

        try:
            f = float(str(obj))
            return type_(round(f)) if type_ == int else type_(f)
        except ValueError:
            arg = self._arg(arg)
            t = type_.__name__
            e = "{}: could not convert string to {}: {}".format(arg, t, obj)
            raise ToolError(e, self.print_help)

    def processors(self, obj, arg=None):
        """processor count, checks system for valid count

        :param obj: `int`, object to check
        :param arg: `str`, argument used for the call
        :return: obj if obj is a valid count
        :raise: `ToolError` if an invalid cpu count is provided
        """

        cpu_count = multiprocessing.cpu_count()

        if obj.lower() == 'max':
            return cpu_count
        elif obj.lower() == 'half':
            return cpu_count / 2

        num = self.number(obj, arg=arg, type_=int)
        arg = self._arg(arg)

        e = ("{}: invalid cpu count: {}; processors available = {}"
             .format(arg, num, cpu_count))

        assert num <= cpu_count, ToolError(e, self.print_help)
        return num

    def show_keyframe(self, obj, arg=None):
        """verifies obj matches ``keyframes`` or an integer

            keyframes : all x/y points
              integer : specific index

        :param obj: `str`, object to check
        :param arg: `str`, argument used for the call
        :return: string version of object or integer if object is a number
        :raise: `ToolError` if an invalid keyframe index type is provided
        """

        obj = str(obj).lower()

        if obj == 'keyframes':
            index = 0, None, 1
            return slice(*index)
        elif obj.isdigit():
            return self.number(obj, arg, type_=int)
        else:
            arg = self._arg(arg)
            e = arg + ": invalid points type: {}".format(obj)
            raise ToolError(e, self.print_help)

    def show_xy(self, obj, arg=None):
        """verifies obj matches ``x``, ``y``, ``points``, or an integer

                  x : all x coordinates
                  y : all y coordinates
             points : all x/y points
            integer : specific index

        :param obj: `str`, object to check
        :param arg: `str`, argument used for the call
        :return: string version of object or integer if object is a number
        :raise: `ToolError` if an invalid point type is provided
        """

        obj = str(obj).lower()

        if obj in ('x', 'y', 'points'):
            return obj
        elif obj.isdigit():
            return self.number(obj, arg, type_=int)
        else:
            arg = self._arg(arg)
            e = arg + ": invalid points type: {}".format(obj)
            raise ToolError(e, self.print_help)

    def str_(self, obj, arg=None):
        """wrapper for builtin 'str', try to convert obj to str

        :param obj: `type`, object to check
        :param arg: `str`, argument used for the call
        :return: string version of object
        :raise: `ToolError` if `obj` can't be converted to a string
        """

        try:
            obj = str(obj)
            return obj
        except Exception as e:
            arg = self._arg(arg)
            e = "{arg}: {e}".format(arg=arg, e=e)
            raise ToolError(e, self.print_help)

    # noinspection PyUnusedLocal
    @staticmethod
    def type_type(obj, *args, **kwargs):
        """generic type for simple pass through
        :param obj: `object`, object to pass
        :param args: unused
        :param kwargs: unused
        :return: object
        """

        return obj

    def unsigned_number(self, obj, arg=None):
        """verifies if an object is an unsigned int or float

        :param obj: `int`/`float`, object to check
        :param arg: `str`, argument used for the call
        :return: ``self.number(obj)`` if unsigned
        :raise: `ToolError` if number is not unsigned
        """

        num = self.number(obj, arg=arg)
        if num >= 0:
            return num

        arg = self._arg(arg)
        e = self.bad_range.format(arg=arg, obj=obj, min_=0, max_='..')
        raise ToolError(e, self.print_help)

    def valid_file(self, file_path_in, arg=None, type_=''):
        """verifies that a inputted path is an actual file

        :param file_path_in: `str`, path to check
        :param arg: `str`, argument used for the call
        :param type_: `str`, type of file being checked for validity;
                      used only if there is an error
        :return: absolute path to `file_path_in` if valid
        :raise: `ToolError` if `file_path_in` not valid
        """

        file_path = utils.full_path(file_path_in)

        if os.path.isfile(file_path):
            return file_path

        arg = self._arg(arg)
        e = self.bad_path.format(arg=arg, path_in=file_path_in, type_=type_)
        raise ToolError(e, self.print_help)

    def zulu_time(self, str_, arg=None):
        """verifies that the inputted string matches zulu time format

        :param str_: `type`, object to check
        :param arg: `str`, argument used for the call
        :return: string version of object
        :raise: `ToolError` if `str_` not zulu time key format
        """

        try:
            _ = datetime.datetime.strptime(str_, '%Y-%m-%dT%H:%M:%S.%fZ')
            return str_
        except Exception as e:
            arg = self._arg(arg)
            e = "{arg}: {e}".format(arg=arg, e=e)
            raise ToolError(e, self.print_help)


class StoreWithConst(argparse.Action):
    """custom argparse.Action wrapper

    stores the resulting namespace object as destination/constant tuple
    """

    def __call__(self, parser, args, values, option_string=None):
        setattr(args, self.dest, (self.const, values))


class ArgumentParser(argparse.ArgumentParser):
    """
    custom argument parser for standard Python module argparse; specifically
    increases output (displays Lytro Power Tools help) when an error occurs
    """

    def error(self, message):
        """
        overrides error function provided by argparse
        :param message: message to display when error occurs
        :raise: `ToolError` if error occurs
        """

        raise ToolError(message, self.print_help)

    def args_meta(self, dflt_verbose=False):
        """shared Lytro Power Tools arguments

        :param dflt_verbose: `bool`, specifies if verbose should be True/False
        """

        self.add_argument(
            '--verbose',
            default=dflt_verbose,
            help="increase verbosity",
            action='store_true')

        self.add_argument(
            '--debug',
            default=False,
            help=argparse.SUPPRESS,
            action='store_true')
