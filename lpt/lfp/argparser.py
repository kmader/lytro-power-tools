# -*- coding: utf-8 -*-
"""Lytro Power Tools - lfp package - lfptool argument parsing"""

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

import multiprocessing
from functools import partial

import config
from lpt.lfp.tnt import Tnt
from lpt.recipe.params import Params
from lpt.utils.argutils import ArgUtils
from lpt.utils.utils import Utils

tnt = Tnt()
utils = Utils()
argutils = ArgUtils()
params = Params()

arg_format = argutils.arg_format


class ArgParser(object):
    """LFP Tool-specific argument parser functions"""

    _file_pattern = config.file_pattern
    _cpu_count = config.db['processors']

    @staticmethod
    def _cls_vals(cls):
        """flattens arguments passed to argparse.add_parser"""
        return utils.flatten({
            'action': cls.action,
            'dest': cls.dest,
            'choices': cls.choices,
            'const': cls.const,
            'default': cls.default,
            'help': cls.help_,
            'metavar': cls.metavar,
            'nargs': cls.nargs,
            'required': cls.required,
            'type': cls.type_})

    def builder(self, subparser, add_actions=False, input_args=None,
                mode=None, **kwargs):
        """LFP Tool argument subparser builder

        :param subparser: <argparse subparser> parser to add arguments to
        :param add_actions: `bool`, add lfp.tnt 'actions' group  to parser
        :param input_args: <argparse group> passed to consolidate input
                           arguments for some lfptool sub-commands
        :param mode: `str`, filter for specific lfptool sub-commands
                     candidates = 'raw', 'warp', 'batch'
        :param kwargs: `dict`, keyword arguments passed to tnt.dests
        """

        dests = tnt.dests(mode=mode, **kwargs)
        for group, dests in dests.items():

            build = subparser.add_argument_group(group + ' arguments')

            if group == 'action':

                if not add_actions:
                    continue

                build = build.add_mutually_exclusive_group()

            for dest in dests:

                cls = getattr(tnt, dest)
                opts = self._cls_vals(cls)
                short = None

                if cls.action:

                    if cls.const == 'transcode':
                        dest = cls.const_alt
                        opts['help'] = cls.help_alt
                    else:
                        dest = cls.const

                    opts['dest'] = opts['dest'].format(mode)
                    if 'type' in opts:
                        del opts['type']

                if mode == 'batch' and dest == 'recipe_in':
                    opts['help'] = "globally applied recipe (see: --per-lfp)"

                if dest.startswith('perspective'):

                    short = dest[-1]
                    opts['metavar'] = short

                arg = arg_format(dest, split='_', join='-', pre='--')

                args = [arg]
                if short:
                    short_arg = arg_format(short, pre='-')
                    args = [short_arg, arg]

                if input_args and group == 'input':
                    input_args.add_argument(*args, **opts)
                else:
                    build.add_argument(*args, **opts)

    def arg_multiprocessing(self, parser):
        """adds processors arg (for multiprocessing)

        :param parser: <argparse parser> parser to add argument to
        """

        max_ = "[max: {}]".format(multiprocessing.cpu_count())
        dflt = argutils.arg_default(self._cpu_count)

        help_ = "processes to run concurrently {} {}".format(max_, dflt)

        parser.add_argument(
            '-P', '--processors',
            help=help_,
            type=partial(argutils.processors, arg='--processors'),
            default=self._cpu_count)

    def arg_src(self, parser):
        """creates a argparse group and adds input arguments

        :param parser: <argparse parser> parser to add argument to
        :return: created argparse group
        """

        title = "input arguments"
        help_ = "execute operation on input LFP files or scanned directories"
        group = parser.add_argument_group(title=title)
        pat = argutils.arg_default(self._file_pattern)

        group.add_argument(
            '-i', '--lfp-in',
            nargs='+',
            required=True,
            dest='paths',
            metavar='PATH',
            help=help_)

        group.add_argument(
            '--range',
            dest='file_range',
            help="start/end range of LFP files to parse",
            metavar=argutils.int_meta,
            type=int,
            nargs=2,
            default=(0, 0))

        group.add_argument(
            '--pattern',
            help="--range pattern; *=wildcard, #=start of sequence) " + pat,
            dest='file_pattern',
            metavar='PATTERN',
            default=config.file_pattern)

        return group

    @staticmethod
    def args_info(parser):
        """adds info arguments to a given argparse parser

        :param parser: <argparse parser> parser to add arguments to
        """

        info_opts = parser.add_mutually_exclusive_group()
        pv = argutils.arg_conflict('pv')
        ov = argutils.arg_conflict('ov')
        ops = argutils.arg_conflict('ops')

        info_opts.add_argument(
            '-o', '--json-out',
            default=False,
            help="write results as JSON " + pv,
            dest='json_out',
            action='store_true')

        info_opts.add_argument(
            '-v', '--validate',
            default=False,
            help="validate LFP schema " + ops,
            dest='validate',
            action='store_true')

        info_opts.add_argument(
            '-p', '--property',
            default=(),
            nargs='+',
            help="query LFP metadata for specified property key " + ov,
            metavar='KEY',
            dest='property')

        parser.add_argument(
            '-x', '--exact',
            default=False,
            action='store_true',
            help="with --property, search for exact match",
            dest='exact')

    @staticmethod
    def args_four_d(parser):
        """adds 4D arguments to a given argparse parser

        :param parser: <argparse parser> parser to add arguments to
        """

        parser.add_argument(
            '-r', '--row',
            dest='row',
            required=True,
            type=int,
            help="eslf row")

        parser.add_argument(
            '-c', '--column',
            dest='column',
            required=True,
            type=int,
            help="eslf column")

    @staticmethod
    def args_batch(parser):
        """adds batch arguments to a given argparse parser

        :param parser: <argparse parser> parser to add arguments to
        """

        parser.add_argument(
            '--per-lfp',
            help="process against each individual LFP (image count required)",
            metavar="IMAGES",
            default=False,
            type=int)
