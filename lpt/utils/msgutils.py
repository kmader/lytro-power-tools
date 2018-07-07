# -*- coding: utf-8 -*-
"""Lytro Power Tools - utilities package - shared messaging utilities"""

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


import contextlib
import itertools
import os
import sys
import time
import json
import getpass
import threading
import functools

__prog__ = 'LPT'


class MsgIndicator(threading.Thread):
    """threaded class used for messaging indicator

    :param msg: `str`, message to write to stdout
    :param delay: `float`, time to wait between character changes
    :param chars: `str`/`iter`, characters to cycle through
    """

    def __init__(self, msg='', delay=.1, chars='|/-\\'):
        threading.Thread.__init__(self)
        self.msg = msg
        self.delay = delay
        self.chars = chars
        self.running = True

    def run(self):
        """overrides threading.Thread.run"""

        sys.stdout.flush()
        cycle = itertools.cycle(self.chars)

        while self.running:
            if not self.running:
                break
            n = str(cycle.next())
            o = ''.join([self.msg, n])
            sys.stdout.write(o)
            sys.stdout.flush()
            sys.stdout.write('\b')
            sys.stdout.write('\r')
            time.sleep(self.delay)


class MsgUtils(object):
    """class for primary messaging and status output

    :param prog_: `str`, program name
    """

    def __init__(self, prog_=__prog__):
        self.prog = prog_
        self.running = False

    def msg(self, msg, crlf='\r\n', indent=False, input_=False, getpass_=False,
            mute=False, raw=False, answer=False, space=0, type_='INFO'):
        """primary messaging system for Lytro Power Tools

        :param crlf: `str`, carriage return, '' to disable printing newline
        :param getpass_: `bool`, getpass.getpass prompt for user password
        :param indent: `bool`, indent message (w/out timestamp, type, prog)
        :param input_: `bool`, return a raw_input to gather user input
        :param msg: `str`, message to write to stdout/stderr
        :param mute: `bool`, enable/disable writing to sys.stdout
        :param raw: `bool`, raw stdout output
        :param answer: `bool`, return the generated msg instead of writing out
        :param space: `bool`, passed to `self.msg_meta`; defines margin size
        :param type_: `str`, message type (INFO, WARN, ERROR)
        :return: generated message if requested else (writes to stdout/stderr
        """

        if raw:
            sys.stdout.write(msg + crlf)
            return

        if input_:
            crlf = ''
            mute = True

        meta_msg, margin = self.msg_meta(type_, space=space)
        meta = margin if indent else meta_msg
        out = meta + msg + crlf

        if type_ == 'ERROR':
            sys.excepthook = lambda t, e, tb: sys.stderr.write(str(e))
            raise _LptError(out)
        elif input_:
            return raw_input(out)
        elif getpass_:
            return getpass.getpass(out)
        elif answer:
            return out
        elif not mute:
            sys.stdout.write(out)

    def msg_meta(self, type_='INFO', space=0):
        """generates meta information for messaging system

        :param space: `int`, number of spaces to generate margin (override)
        format: [<timestamp>][<type_>][<prog>]
        example: [1427926719][INFO][LPT]

        :param type_: `str`, message type (INFO, WARN, ERROR)
        :return: formatted meta string
        """

        now = int(time.time())

        meta = ("[{ts}][{msg_type}][{program}]:  "
                .format(ts=now, msg_type=type_, program=self.prog))

        margin = ' ' * (space or len(meta))
        return meta, margin

    @contextlib.contextmanager
    def msg_indicator(self, msg, end="...done!", **kwargs):
        """adds a threaded, cycling, text object to indicate progress

        :param end: `str`, message to print after indicator is complete
        :param msg: `str`, message output
        :param kwargs: `dict`, arguments passed to MsgIndicator class
        """

        indicator = MsgIndicator(msg, **kwargs)
        indicator.daemon = True
        indicator.start()
        time.sleep(.25)
        yield indicator

        indicator.running = False
        time.sleep(.25)
        done = msg + end + '\r\n'
        sys.stdout.write(done)
        sys.stdout.flush()

    @staticmethod
    def display_path(path):
        """returns a display path for std(out|err)

        relative path format if path is relative to the current working
        directory; absolute path format if not (i.e., Windows drive letters)

        :param path: path to format/print
        :return: formatted path string
        """

        sep = os.sep if os.path.isdir(path) else ''
        abs_path = os.path.abspath(path) + sep

        if sys.platform == 'win32':
            cur_dir = os.path.abspath(os.curdir)
            if cur_dir[0] != abs_path[0]:
                return abs_path

        return os.path.relpath(path) + sep

    def dumps(self, obj, indent=True, answer=False, sort_keys=True):
        """wrapper for json.dumps

        serializes object to a JSON formatted string

        :param obj: `object`, object to serialize
        :param indent: `bool`, indent object when writing to sys.stdout
        :param answer: `bool`, return object instead of writing to sys.stdout
        :param sort_keys: `bool`, if object is a dict, sort the keys
        :return: the serialized object if requested else None
        """

        dump = json.dumps(obj, indent=4, sort_keys=sort_keys)

        if answer:
            return dump
        elif not indent:
            self.msg(dump, raw=True)
            return

        if isinstance(obj, (list, dict)):
            lines = dump.split('\n')
            [self.msg(line, indent=indent) for line in lines]
        else:
            self.msg(str(obj), indent=True)

    @staticmethod
    def rjust(lst=(), alt=(), pad=1):
        """provides constant right alignment while printing

        :param lst: `list`, list of words to generate max length of strings
        :param alt: `list`, used as an alternative source for string lengths
        :param pad: `int`, pad additional spaces to the alignment
        :return: the longest word length from inputted values
        """

        lst = lst or "analyzing lfps",
        items = list(lst) + list(alt)
        return max(len(key) for key in items) + pad

    def status(self, msg='', src=None, dest=None, count=None, type_='INFO',
               answer=False, indent=False, one_line=False, rjust=None):
        """prints status of processing command

        :param indent:
        :param msg: `str`, message to print
        :param type_: `str`, message type (INFO, WARN, ERROR)
        :param src: `str`, input object being processed
        :param dest: `str`, output object being processed
        :param count: `int`, current count of items being processed
        :param answer: `bool`, sets function to return message or not
        :param rjust: `int`, rjust to set for `self.item`
        :param one_line: `bool`, print joined msg/src/dest lines
        :return: message if `answer` else None
        """

        def pad(x, i=4): return str(x).zfill(i)

        def lst(l): return [l] if not isinstance(l, (list, tuple, set)) else l

        item = functools.partial(self.item, rjust=rjust)
        disp = self.display_path

        count_s = "({}) ".format(pad(count)) if count or count == 0 else ''
        message = "{}{} : ".format(count_s, msg)
        src = [disp(s) for s in lst(src)] if src else []
        dest = [disp(d) for d in lst(dest)] if dest else []

        if one_line:
            message += ','.join(src)
            message += ' > '
            message += ','.join(dest)
            src = dest = []

        if answer:
            return message
        if msg:
            self.msg(message, type_=type_, indent=indent)
        if src:
            [self.msg(item('input', s), indent=True) for s in src if s]
        if dest:
            [self.msg(item('output', d), indent=True) for d in dest if d]

    def item(self, item, value='', rjust=None):
        """properly formats and aligns items for status function

        example:

             input : /path/to/input
            output : /path/to/output
            schema : /path/to/schema

        :param rjust: `int`, right justify the item by amount provided
        :param item: `str`, object key to format
        :param value: `str`, object value to format
        :return: formatted string
        """

        rjust = rjust or self.rjust()
        aligned = item.rjust(rjust)
        item = "{} :".format(aligned)

        if value is not None:
            item = ' '.join([item, str(value)])

        return item


class _LptError(Exception):
    """pass through exception class"""


class ToolError(Exception):
    """general error for Lytro Power Tools if anything goes wrong

    passes error to primary Lytro Power Tools messaging function (stderr)

    :param message: `str`, message to write to stderr
    :param func: `object`, function to execute before writing error
    """

    msgutil = MsgUtils()

    def __init__(self, message, func=object):
        func()
        self.msgutil.msg("ERROR: {}".format(message), type_='ERROR')


class ToolWarn(object):
    """general warning for Lytro Power Tools if anything goes _sort of_ wrong

    passes warning to primary Lytro Power Tools messaging function (stdout)
    :param message: `str`, message to write to stdout
    """

    msgutil = MsgUtils()

    def __init__(self, message):
        self.msgutil.msg("WARNING! {}".format(message), type_='WARN')
