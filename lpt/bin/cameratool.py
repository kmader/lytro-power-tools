#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lytro Power Tools - cameratool script"""

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

__prog__ = 'cameratool'
__version__ = '1.1'

import os
import sys

try:
    import lpt
except ImportError:
    mod_dir = os.path.dirname(os.path.realpath(__file__))
    lpt_dir = os.path.abspath(os.path.join(mod_dir, '../..'))
    sys.path.insert(0, lpt_dir)
    import lpt

from lpt.camera import builder
import functools
import textwrap


def main():

    bld = builder.Build()

    subparsers = bld.parser.add_subparsers()

    ''' CAPTURES '''
    p_captures = subparsers.add_parser("captures",
                                       description=textwrap.dedent(
                                       ''' This program takes a series of captures. Users specify number of captures and
                                        sleep interval '''),

                                       help="Takes a series of captures...")

    p_captures.add_argument("--pictures",
                            dest='pictures',
                            type=functools.partial(bld.check_min_value, subparser_caller="captures"),
                            default=10,
                            help="Number of pictures to take",
                            metavar=" ")


    p_captures.add_argument("--interval",
                            dest='interval',
                            type=functools.partial(bld.check_min_value, subparser_caller="interval"),
                            default=0,
                            help="Additional sleep time in between captures\n\n",
                            metavar=" ")


    p_captures.set_defaults(func=bld.setup_captures_script)


    ''' CONTINUOUS CAPTURE '''
    p_cont_captures = subparsers.add_parser("cont-captures",
                                            description=textwrap.dedent(
                                            '''This program takes multiple series of burst captures. Users specify
                                               the burst size, the time interval and the number of iterations. (This
                                               tool may not perform properly at shutter speeds slower than 1/25)'''),

                                            help="Takes multiple series of burst captures...\n")

    p_cont_captures.add_argument("--size",
                                 dest='capture_size',
                                 type=functools.partial(bld.check_min_value, subparser_caller="cont-captures"),
                                 default=3,
                                 help="Burst captures size. 1 to 8",
                                 metavar='')

    p_cont_captures.add_argument("--interval",
                                 dest='cont_interval',
                                 type=functools.partial(bld.check_min_value, subparser_caller="interval"),
                                 default=0,
                                 help="Additional sleep time in between each capture series",
                                 metavar=" ")

    p_cont_captures.add_argument("--repeat",
                                 dest='reps',
                                 type=int,
                                 default=1,
                                 help="Number of iterations",
                                 metavar=" ")


    p_cont_captures.set_defaults(func=bld.setup_cont_captures_script)



    ''' EXPOSURE BRACKETING '''
    p_exp_bracketing = subparsers.add_parser("exp-bracketing",
                                             description=textwrap.dedent('''This program takes multiple series of
                                            exposure bracketed shots. Users specify bracket series size, exposure stop
                                            increments, time intervals, and the number of iterations. '''),

                                             help="Takes multiple series of exposure bracketed captures...\n")

    p_exp_bracketing.add_argument("--size",
                                  dest='size',
                                  type=int,
                                  default=3,
                                  choices={3, 5},
                                  help="Number of captures for each bracketing series: 3 or 5",
                                  metavar=" ")

    p_exp_bracketing.add_argument("--offset",
                                  dest='offset',
                                  type=float,
                                  default=.6,
                                  choices={.3, .6, 1, 2},
                                  help="Exposure stop increments .3, .6, 1 or 2",
                                  metavar=" ")

    p_exp_bracketing.add_argument("--interval",
                                  dest='bracket_interval',
                                  type=functools.partial(bld.check_min_value, subparser_caller="interval"),
                                  default=0,
                                  metavar=" ",
                                  help="Additional sleep time in between each series")

    p_exp_bracketing.add_argument("--repeat",
                                  dest='reps',
                                  type=functools.partial(bld.check_min_value, subparser_caller="exp-bracketing"),
                                  default=1,
                                  metavar=" ",
                                  help="Number of iterations")


    p_exp_bracketing.set_defaults(func=bld.setup_exp_bracketing_script)

    ''' FOCUS BRACKETING '''
    p_focus_bracketing = subparsers.add_parser("focus-bracketing",
                                               description=textwrap.dedent('''This program takes  multiple series of
                                               focus bracketed shots. Users specify burst size, focus stop increments,
                                               time intervals, and the number of iterations. '''),

                                               help="Takes multiple series of focus bracketed captures...\n")

    p_focus_bracketing.add_argument("--size",
                                    dest='size',
                                    type=int,
                                    default=3,
                                    choices={3, 5},
                                    help="Number of captures for each bracketing series: 3 or 5",
                                    metavar=" ")

    p_focus_bracketing.add_argument("--offset",
                                    dest='offset',
                                    type=int,
                                    default=5,
                                    choices={1, 2, 3, 4, 5, 6, 7, 8, 9, 10},
                                    help="Focus stop increments: 1 to 10",
                                    metavar=" ")

    p_focus_bracketing.add_argument("--interval",
                                    dest='bracket_interval',
                                    type=functools.partial(bld.check_min_value, subparser_caller="interval"),
                                    default=0,
                                    metavar=" ",
                                    help="Additional sleep time in between each series")

    p_focus_bracketing.add_argument("--repeat",
                                    dest='reps',
                                    type=functools.partial(bld.check_min_value, subparser_caller="focus-bracketing"),
                                    default=1,
                                    metavar=" ",
                                    help="Number of iterations")


    p_focus_bracketing.set_defaults(func=bld.setup_focus_bracketing_script)

    ''' FOCUS SWEEP '''
    p_focus_sweep = subparsers.add_parser("focus-sweep",
                                          description=textwrap.dedent('''This program takes a number of captures evenly
                                          distributed across the specified focus range. (Applicable focus range size
                                          depends on camera's current focal length) '''),

                                          help="Takes a number of captures evenly distributed across the specified "
                                               "focus range...\n")


    p_focus_sweep.add_argument("--interval",
                               dest='interval',
                               type=functools.partial(bld.check_min_value, subparser_caller="interval"),
                               default=0,
                               help="Additional sleep time in between captures\n\n",
                               metavar=" ")

    p_focus_sweep.add_argument("--focus-range",
                               type=int,
                               default=None,
                               help='Focus range: int startFocusStep  int endFocusStep',
                               metavar=" ",
                               dest="focus_range",
                               nargs=2)

    p_focus_sweep.add_argument("--pictures",
                               dest='pictures',
                               default=10,
                               type=functools.partial(bld.check_min_value, subparser_caller="focus-sweep"),
                               help='Number of pictures. Minimum of 2',
                               metavar=" ")

    p_focus_sweep.set_defaults(func=bld.setup_focus_sweep_script)

    ''' ZOOM SWEEP '''
    p_zoom_sweep = subparsers.add_parser("zoom-sweep",
                                         description=textwrap.dedent('''This program takes a number of captures evenly
                                         distributed across the specified zoom range. '''),

                                         help="Takes a number of captures evenly distributed across the specified "
                                         "zoom range...\n")

    p_zoom_sweep.add_argument("--interval",
                              dest='interval',
                              type=functools.partial(bld.check_min_value, subparser_caller="interval"),
                              default=0,
                              help="Additional sleep time in between captures\n\n",
                              metavar=" ")

    p_zoom_sweep.add_argument("--zoom-range",
                              type=functools.partial(bld.check_range, arg_range=(1, 1522), arg_name='Zoom step'),
                              default=(2, 1500),
                              dest="zoom_range",
                              nargs=2,
                              metavar=" ",
                              help="Zoom range (int startZoomStep) (int endZoomStep)")

    p_zoom_sweep.add_argument("--pictures",
                              dest='pictures',
                              default=10,
                              type=functools.partial(bld.check_min_value, subparser_caller="zoom-sweep"),
                              help='Number of pictures. Minimum of 2',
                              metavar=" ")

    p_zoom_sweep.set_defaults(func=bld.setup_zoom_sweep_script)

    ''' PULL CALIBRATION DATA '''
    p_pull_cal_data = subparsers.add_parser("pull-cal-data",
                                            description=textwrap.dedent('''Pulls calibration data from camera to the
                                            local file system' '''),

                                            help="Pulls calibration data from camera to the local file system")

    p_pull_cal_data.add_argument("--path",
                                 type=str,
                                 default=bld.cal_data_path,
                                 dest="path",
                                 metavar=" ",
                                 help="Choose this option to specify a destination path other than the default path: "
                                      "{}".format(bld.cal_data_path))

    p_pull_cal_data.set_defaults(func=bld.cam.pull_cal_data)


    ''' DOWNLOAD RECENT IMAGES '''
    p_import_pictures = subparsers.add_parser("download-images",
                                              description=textwrap.dedent(''' Downloads images to the local file
                                              system '''),

                                              help=bld.dwl_string)
    p_import_pictures.add_argument("--path",
                                   type=str,
                                   default=bld.currentDir,
                                   dest="path",
                                   metavar=" ",
                                   help="Choose this option to specify a destination path other than the default path: "
                                        "{}".format(bld.currentDir))


    p_import_pictures.add_argument("--all",
                                   action="store_true",
                                   default=False,
                                   dest="dwl_all",
                                   help="import all pictures as opposed to only the pictures captured in latest run.")

    p_import_pictures.set_defaults(func=bld.cam.download_images)


    ''' DELETE_ALL_PICTURES '''
    p_delete_all = subparsers.add_parser("delete-all",
                                         description=textwrap.dedent('''Deletes all pictures from the camera '''),
                                         help="Deletes ALL pictures from the camera\n")
    p_delete_all.set_defaults(func=bld.cam.delete_all_pictures)

    args = bld.parser.parse_args()

    bld.cam.handle_if_adb_not_running()

    #Check FOCUS SWEEP values
    try:
        #If user did not specify focus range than use current min and max as focus range
        if not args.focus_range:
            bld.cam.init(False)
            args.focus_range = tuple(bld.cam.get_valid_focus_range())
        else:
            lowest_focus = args.focus_range[0]
            highest_focus = args.focus_range[1]
            bld.cam.init(False)
            valid_focus_range = tuple(bld.cam.get_valid_focus_range())
            bld.check_range(lowest_focus, valid_focus_range, "Focus step")
            bld.check_range(highest_focus, valid_focus_range, "Focus step")
            bld.check_range(args.pictures, tuple([1, highest_focus - lowest_focus]), "Picture count")
    except AttributeError:
        pass

    #Check CONT CAPTURES values
    try:
        bld.check_range(args.capture_size, tuple([1, 8]), "Consecutive captures")
    except AttributeError:
        pass

    args.func(args)


if __name__ == "__main__":

    main()
