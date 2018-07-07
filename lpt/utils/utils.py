# -*- coding: utf-8 -*-
"""Lytro Power Tools - utilities package - shared miscellaneous utilities"""

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

import datetime
import json
import os
import re
import textwrap

from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError

msgutils = MsgUtils()


class Utils(object):
    """miscellaneous shared Lytro Power Tools functions"""

    print_help = object

    def set_print_help(self, print_help):
        """sets `argparse` help menu for current command

        :param print_help: `object`, passed to ToolError for command help menu
        """

        self.print_help = print_help

    def _all_any_alter(self, obj, num=True, bool_=True, iter_=True,
                       not_none=False):
        """handles logic for `self.all_` and `self.any_`

        :param obj: `object`, object to inspect
        :param num: `bool`, allow number (i.e.: 0, 0.0)
        :param bool_: `bool`, allow bool (i.e.: False)
        :param iter_: `bool`, allow empty iterators (i.e.: [], {}, ())
        :param not_none: `bool`, allow anything but None
        :return: True if criteria is met else False
        """

        obj = self.make_iter(obj)
        instances = []

        if num:
            instances.extend([float, int])
        if iter_:
            iter_types = dict, list, tuple, set
            instances.extend(iter_types)
            if isinstance(obj, iter_types) and len(obj) == 0:
                yield [True]

        def _is_inst(x):
            if not_none:
                return x is not None
            elif x in [True, False] and isinstance(x, bool):
                return True if bool_ else False
            else:
                return isinstance(x, tuple(instances))

        for i in obj:
            yield True if i or _is_inst(i) else False

    def all_(self, *args, **kwargs):
        """alternate to built-in function `all`

        same functionality as all but also accepts 0, 0.0, False, and
        empty iterators

        :param args: positional args passed to `self._all_any_alter`
        :param kwargs: keyword args passed to `self._all_any_alter`
        :return: True if all requested elements present, else False
        """

        return all([x for x in self._all_any_alter(*args, **kwargs)])

    def any_(self, *args, **kwargs):
        """ alternate to built-in function `any`

        same functionality as any but also accepts 0, 0.0, False, and
        empty iterators

        :param args: positional args passed to `self._all_any_alter`
        :param kwargs: keyword args passed to `self._all_any_alter`
        :return: True if any requested elements present, else False
        """

        for value in self._all_any_alter(*args, **kwargs):
            if value:
                return True
        return False

    @staticmethod
    def camel_join(str_, split='_'):
        """formats provided string into camelCase format, ignoring split chars

        :param str_: `str`, string to format
        :param split: `str`, characters to ignore when formatting string
        :return: formatted string
        """

        s = ''.join(x for x in str_.title() if x not in split)
        return str_[0].lower() + s[1:]

    @staticmethod
    def camel_split(str_, join='_'):
        """formats provided camelString into joined format

        :param str_: `str`, camel string to format
        :param join: `str`, character(s) to join split words with
        :return: formatted string
        """

        s = re.sub('(.)([A-Z][a-z]+)', r'\1{}\2'.format(join), str_)
        s = re.sub('([a-z0-9])([A-Z])', r'\1{}\2'.format(join), s).lower()
        return s

    @staticmethod
    def dedent(text):
        """wrapper for textwrap.dedent

        additionally strips newlines and rstrips space characters

        :param text: `str`, text to dedent
        :return: de-dented string
        """

        return textwrap.dedent(text.strip('\n').rstrip(' '))

    def file_filter(self, path, file_range=(0, 0), file_pattern='*'):
        """filters file names using provided pattern and sequence range

        * = wildcard
        # = start of sequence (required)

        IMG_#       : matches files beginning with 'IMG_' and ending with any
                      amount of numbers
        IMG_*x.01_# : matches IMG_foo_x.01_<SEQUENCE>

        :param path: `str`, path to file
        :param file_range: `tuple`, start/end of sequence to filter for
        :param file_pattern: `str`, pattern to filter
        :return: `path` if file name is a match else False
        :raise: `ToolError` if `file_pattern` does not contain 1 ``#`` char
        """

        d, name, ext = self.split_path(path)
        file_start = min(file_range)
        file_end = max(file_range)

        if not file_end:
            return path

        fp = file_pattern.replace('#', '[0-9]+').replace('*', '.*')
        fp = re.compile(fp)

        if not re.match(fp, name):
            return False

        file_range = xrange(file_start, file_end + 1)
        e = "pattern must contain one numeric '#' start point: " + file_pattern
        assert file_pattern.count('#') == 1, ToolError(e, self.print_help)

        s = file_pattern.index('#')
        counts = re.findall('[0-9]+', name[s:])

        for count in counts:
            count = count.lstrip('0')
            count = int(count) if count else 0
            if count in file_range:
                return path

        return False

    def flatten(self, dict_, **kwargs):
        """flattens one level dictionaries

        acceptable values are matched through `self.any_`

        :param dict_: `dict`, dictionary to flatten
        :param kwargs: keyword args passed to `self.any_`
        :return: flattened dictionary
        """

        return {k: v for k, v in dict_.items() if self.any_(v, **kwargs)}

    @staticmethod
    def full_path(path):
        """converts path to an expanded, absolute path

        :param path: `str`, input path to check
        :return: absolute path
        """

        file_path = os.path.expanduser(path)
        file_path = os.path.abspath(file_path)
        return file_path

    @staticmethod
    def get_from_dict(dict_, map_list):
        """get value from a nested location in a dictionary

        :param dict_: `dict`, dictionary to search
        :param map_list: `list`, path to nested key
        :return: requested value
        """

        def index(s): return int(s) if s.isdigit() else s
        map_list = [index(x) for x in map_list]
        return reduce(lambda d, k: d[k], map_list, dict_)

    @staticmethod
    def join_abspath(parent, child):
        """combination of os.path.join and os.path.abspath

        :param parent: `str`, parent directory
        :param child: `str`, child file or directory
        :return: for
        """

        return os.path.abspath(os.path.join(parent, child))

    @staticmethod
    def make_iter(obj):
        """checks if an object can iterated, if not convert it to one

        :param obj: `object`, object to check
        :return: a list version of the object
        """

        return obj if hasattr(obj, '__iter__') else [obj]

    def mkdir(self, dir_path):
        """make a directory

        :param dir_path: `str`, input directory to create
        :raise: `ToolError` if there is an `OSError` exception
        """

        try:
            os.makedirs(dir_path)
            return dir_path
        except OSError as e:
            raise ToolError(e, self.print_help)

    def sanitize_path(self, path):
        """creates unique filename based off of provided path

        :param path: `str`, path to make unique
        :return: unique version of the path
        """

        if not os.path.exists(path):
            return path

        if os.path.isdir(path):
            o_ext = ''
            d_root, o_root = os.path.split(path)
        else:
            d_root, o_root, o_ext = self.split_path(path)

        def unique(): return '{}_{}{}'.format(o_root, str(i).zfill(4), o_ext)

        i = -1
        unique_path = path
        while os.path.exists(unique_path):
            i += 1
            unique_path = os.path.join(d_root, unique())

        return unique_path

    @staticmethod
    def search_dict(obj, field, exact=False, case_sensitive=False, join=''):
        """case insensitive search of keys in a dict

        by default, for the key path, a list is returned with keys that can
        be followed to the found value; if join is provided, a string based
        key path is returned

        :param obj: `dict`, object to perform search on
        :param field: `str`, key to perform search for
        :param exact: `bool`, exact key match in place of character sequence
        :param case_sensitive: `bool`, make case (in)sensitive search
        :param join: `str`, if provided, join key path with provided str
        :return: tuple, [0] == key path, [1] == value
        """

        results = []
        key_list = []

        def _find_field(data, index=None):
            index = str(index) if index or index == 0 else index

            if isinstance(data, (tuple, list)):
                for i, value in enumerate(data):
                    results.extend(_find_field(value, i))

            elif isinstance(data, dict):
                for key, value in data.items():
                    match = None
                    if exact:
                        if field == key:
                            match = True
                    elif case_sensitive:
                        if field in key:
                            match = True
                    else:
                        if field.lower() in key.lower():
                            match = True
                    if match:
                        keys = [index, key] if index else [key]
                        path = key_list + keys
                        results.append((tuple(path), value))

                    key_list.extend([index, key] if index else [key])
                    results.extend(_find_field(value))
                    [key_list.pop() for _ in range(2 if index else 1)]
            return []

        _find_field(obj)
        results.sort()
        joined = [(join.join(p), v) for p, v in results]
        return joined if join else results

    def set_in_dict(self, dict_, map_list, value):
        """set a dictionary value based of key map list

        :param dict_: `dict`, dictionary to write to
        :param map_list: `list`, path to nested key
        :param value: `object`, value to set in dictionary
        """

        self.get_from_dict(dict_, map_list[:-1])[map_list[-1]] = value

    @staticmethod
    def split_path(path):
        """splits path into a directory root, filename and extension tuple

        :param path: `str`, path to split
        :return: split path tuple
        """

        dir_root, filename = os.path.split(path)
        obj_root, ext = os.path.splitext(filename)
        return dir_root, obj_root, ext

    @staticmethod
    def walk_path(path, pattern=None, ext=None):
        """walk a path for files and yield results

        :param path: `str`, root path to start search from
        :param pattern: `SRE_Pattern`, pattern based file filter
        :param ext: `str`, filter based off of extension
        :yield: files/directories found
        """

        _ext = re.compile('.+\.{}$'.format(ext), flags=re.IGNORECASE)
        pattern = pattern or (_ext if ext else re.compile(''))

        for root, dir_names, file_names, in os.walk(path):
            for file_name in file_names:
                if re.match(pattern, file_name):
                    file_path = os.path.join(root, file_name)
                    yield file_path

    @staticmethod
    def write(file_path, obj, write='w'):
        """writes an object to disk

        if the object is a dict or list, file is written out as a json object

        :param file_path: `str`, file to write out object to
        :param obj: `type`, object to write
        :param write: `str`, write method: w=overwrite, a=append
        """

        with open(file_path, write) as f:
            if isinstance(obj, (list, dict)):
                f.write(json.dumps(obj, indent=2, separators=(',', ': ')))
            else:
                f.write("{}".format(obj.encode('utf-8').strip()))

    @staticmethod
    def zulu_time():
        """datetime in zulu time format

        e.g: '1969-12-31T16:00:00.000000Z'

        :return: current datetime in zulu format
        """

        return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
