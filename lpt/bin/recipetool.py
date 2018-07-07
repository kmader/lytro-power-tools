#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lytro Power Tools - recipetool script"""

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


try:
    import lpt
except ImportError:
    import os
    import sys

    mod_dir = os.path.dirname(os.path.realpath(__file__))
    lpt_dir = os.path.abspath(os.path.join(mod_dir, '../..'))
    sys.path.insert(0, lpt_dir)
    import lpt

from lpt.recipe import config
from lpt.recipe.argparser import ArgParser
from lpt.recipe.cmds import Cmds
from lpt.recipe.params import Params
from lpt.utils.argutils import ArgUtils
from lpt.utils.argutils import ArgumentParser
from lpt.utils.utils import Utils

__prog__ = 'recipetool'
__version__ = '1.0.1'

cmds = Cmds()
utils = Utils()
params = Params()
argutils = ArgUtils()
arg_parser = ArgParser()


def build():
    """build function and arguments for Recipe Tool"""

    parser = ArgumentParser(
            prog=__prog__,
            epilog="Lytro Power Tools - Recipe Tool",
            usage=__prog__ + ' ... ',
            description=utils.dedent('''
        modification operations for Lytro light-field recipe files
        '''),
            formatter_class=argutils.formatter_class())

    parser.args_meta(dflt_verbose=config.db['verbose'])

    subparsers = parser.add_subparsers(
            title=__prog__ + " commands",
            description="see help on individual sub commands for details")

    def blank(g=''):
        subparsers.add_parser('', help=g)

    blank("primary commands")

    destroy_help = "destroy view/animation parameters"
    info_help = "display view/animation parameters values"
    merge_help = "merge source recipe view parameters into single animation"
    new_help = "generate new recipe file(s)"
    plot_help = "plot animation time/value (x/y) line (requires matplotlib)"
    validate_help = "validate recipe file(s) against LFP schema"
    view_help = "view parameter adjustments"

    new_desc = new_help + "; multiple filenames are accepted"
    plot_desc = plot_help + "; if no view parameter is specified, plot all"
    view_desc = view_help + "; some parameters not available in this mode"

    destroy = subparsers.add_parser(
            'destroy',
            help=destroy_help,
            description=destroy_help,
            formatter_class=argutils.formatter_class(m=48))

    info = subparsers.add_parser(
            'info',
            help=info_help,
            description=info_help,
            formatter_class=argutils.formatter_class(m=48))

    merge = subparsers.add_parser(
            'merge',
            help=merge_help,
            description=merge_help,
            formatter_class=argutils.formatter_class(m=48))

    new = subparsers.add_parser(
            'new',
            help=new_help,
            description=new_desc,
            formatter_class=argutils.formatter_class(m=48))

    plot = subparsers.add_parser(
            'plot',
            help=plot_help,
            description=plot_desc,
            formatter_class=argutils.formatter_class(m=48))

    validate = subparsers.add_parser(
            'validate',
            help=validate_help,
            description=validate_help,
            formatter_class=argutils.formatter_class(m=48))

    view = subparsers.add_parser(
            'view',
            help=view_help,
            description=view_desc,
            formatter_class=argutils.formatter_class(m=48))

    arg_parser.arg_animation_store_true(destroy)
    arg_parser.args_store(info, info=True)

    arg_parser.arg_recipe_out(new)
    arg_parser.arg_recipe_out(merge)

    arg_parser.arg_recipe_in(view)
    arg_parser.arg_recipe_in(destroy)
    arg_parser.arg_recipe_in(info)
    arg_parser.arg_recipe_in(plot)
    arg_parser.arg_recipe_in(validate)

    arg_parser.arg_destroy_all(destroy)

    param_dests = params.dests(
            cls=True,
            enabled=True,
            exclude=('priorities',),
            grouped=True)

    destroy_groups = {}
    info_groups = {}
    merge_groups = {}
    plot_groups = {}

    for group, dests in param_dests.items():

        blank()
        blank(group)
        view_group = view.add_argument_group(group)

        destroy_groups[group] = []
        info_groups[group] = []
        merge_groups[group] = []
        plot_groups[group] = []

        for dest in dests:

            prop = getattr(params, dest)
            arg_parser.add_parser(prop, subparsers, view_group)
            destroy_groups[group].append(prop)
            info_groups[group].append(prop)
            merge_groups[group].append(prop)
            plot_groups[group].append(prop)

    arg_parser.args_view_store_true(destroy, destroy_groups)
    arg_parser.args_view_store_true(info, info_groups)
    arg_parser.args_view_store_true(plot, plot_groups)
    arg_parser.args_merge(merge, merge_groups)
    arg_parser.args_plot(plot)

    parser.set_defaults(print_help=parser.print_help)

    destroy.set_defaults(
            func=cmds.current,
            action=cmds.destroy,
            help_=destroy.print_help)

    info.set_defaults(
            func=cmds.current,
            action=cmds.info,
            print_help=info.print_help)

    view.set_defaults(
            func=cmds.current,
            action=cmds.view,
            print_help=view.print_help)

    new.set_defaults(
            func=cmds.new,
            print_help=new.print_help)

    merge.set_defaults(
            func=cmds.merge,
            print_help=merge.print_help)

    plot.set_defaults(
            func=cmds.current,
            action=cmds.plot,
            print_help=plot.print_help)

    validate.set_defaults(
            func=cmds.current,
            action=cmds.validate,
            print_help=validate.print_help)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    build()
