#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lytro Power Tools - cameracontrols script"""

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

from __future__ import division

__prog__ = 'cameracontrols'
__version__ = '1.1'

import argparse
import textwrap
import os
import sys
import functools


try:
    import lpt
except ImportError:
    mod_dir = os.path.dirname(os.path.realpath(__file__))
    lpt_dir = os.path.abspath(os.path.join(mod_dir, '../..'))
    sys.path.insert(0, lpt_dir)
    import lpt

from lpt.camera import camerabin
from lpt.camera import builder

bld = builder.Build()
cam = camerabin.CameraControls()

parser = argparse.ArgumentParser(epilog='Control',
                                 description="LYTRO DEVELOPER KIT CAMERA TOOL \nsee help on "
                                             "individual sub commands for details",
                                 prog="cameracontrols",
                                 formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-v",
                    "--verbose",
                    default=False,
                    dest="verbose",
                    action='store_true',
                    help="increase output verbosity")

subparser = parser.add_subparsers()


def print_current_state(state, description_str="Current State is"):
    print "\n\n{description} ---> {state}\n".format(description=description_str, state=state)


def check_range(usr_input, val_range, string):
    usr_input = float(usr_input)
    min_, max_ = tuple(val_range)
    if usr_input < min_ or usr_input > max_:
        raise argparse.ArgumentTypeError("{string} '{input}' out of range. MIN {min} | MAX {max} "
                                         .format(string=string, input=usr_input, min=min_, max=max_))
    return usr_input


def check_shutterSpeed_range(x):
    x = float(eval(x))
    if x < 0.00025 or x > 32:
        raise argparse.ArgumentTypeError("ShutterSpeed '{}' out of range. MIN 1/4000 | MAX 32 ".format(x))
    return x


def check_bracketing_range(x):
    x = float(eval(x))
    if x < 0.333333333333 or x > 2:
        raise argparse.ArgumentTypeError("Exposure Offset '{}' out of range. MIN 1/3 | MAX 2 ".format(x))
    return x

def check_focus_range(usr_input):
    min_, max_ = tuple(cam.get_valid_focus_range())
    focusStep = int(usr_input)
    if focusStep < min_ or focusStep > max_:
        cam.disable_virtual_cable(True)
        #parser.error("Focus Step '{step}' out of range. Valid range for current focal length is MIN {min} | MAX {max} "
        #             .format(step=focusStep, min=min_, max=max_))
        print "\n\ncameracontrols: error: Focus Step '{step}' out of range. Valid range for current focal length is MIN" \
              " {min} | MAX {max}\n ".format(step=focusStep, min=min_, max=max_)
        sys.exit()
    return focusStep


def check_zoom_range(x):
    x = int(x)
    if x < 1 or x > cam.max_user_zoom_step:
        raise argparse.ArgumentTypeError("Zoom Step '{x}' out of range. MIN 1 | MAX {max} "
                                         .format(x=x, max=cam.max_user_zoom_step))
    return x


def whiteBalance(args):
    if args.wb_preset:
        cam.set_white_balance_mode(args.wb_preset, True)
    if args.get_wb_preset:
        print_current_state(cam.get_white_balance_mode(True))


def exposureMode(args):
    if args.exp_mode:
        cam.set_exposure_mode(args.exp_mode, True)
    if args.get_exp_mode:
        print_current_state(cam.get_exposure_mode(True))


def exposureComp(args):

    if args.exp_comp:
        cam.set_exposure_compensation(args.exp_comp, True)
    if args.get_exp_comp:
        print_current_state(cam.get_exposure_compensation(True))


def iso(args):
    if args.iso:
        cam.set_iso(args.iso, True)
    if args.get_iso:
        print_current_state(cam.get_iso(True))


def shutterSpeed(args):
    if args.sp:
        cam.set_shutter_speed(args.sp, True)
    if args.get_sp:
        print_current_state(cam.get_shutter_speed(True))


def focusStep(args):
    if args.focusStep:
        cam.set_real_focus(args.focusStep, True)
    if args.get_focusStep:
        print_current_state(cam.get_real_focus(True), "Focus Step")


def zoomStep(args):
    if args.zoomStep:
        cam.set_real_zoom(args.zoomStep, True)
    if args.get_zoomStep:
        print_current_state(cam.get_real_zoom(True), "Zoom Step")


def opticalOffset(args):
    if args.optOffset:
        cam.set_optical_offset(args.optOffset, True)
    if args.restore_optOffset:
        cam.set_optical_offset(-4, True)
    if args.get_optOffset:
        print_current_state(cam.get_optical_offset(True), "Optical Offset")


def focusLock(args):
    if args.focusLockState:
        cam.set_focus_ring_lock(args.focusLockState, True)
    if args.restore:
        cam.set_focus_ring_lock('0', True)
    if args.get_focusLockState:
        print_current_state(cam.get_focus_ring_lock(True), "Focus Ring Lock")


def zoomLock(args):
    if args.zoomLockState:
        cam.set_zoom_ring_lock(args.zoomLockState, True)
    if args.restore:
        cam.set_zoom_ring_lock('0', True)
    if args.get_zoomLockState:
        print_current_state(cam.get_zoom_ring_lock(True), "Zoom Ring Lock")


def aeLock(args):
    if args.aeLockState:
        cam.set_ae_lock(args.aeLockState, True)
    if args.restore:
        cam.set_ae_lock('0', True)
    if args.get_aeLockState:
        print_current_state(cam.get_ae_lock(True), "Auto Exposure Ring Lock")


def depthFeedback(args):
    if args.depthFeed:
        cam.set_depthAssist_mode(args.depthFeed, True)
    if args.restore:
        cam.set_depthAssist_mode('0', True)
    if args.get_depthFeed:
        print_current_state(cam.get_depthAssist_mode(True), "Depth Feedback State")


def focusMode(args):
    if args.focusMode:
        cam.set_focus_method(args.focusMode, True)
    if args.restore:
        cam.set_focus_method('auto', True)
    if args.get_focusMode:
        print_current_state(cam.get_focus_method(True), "Focus Mode State")


def shutterMode(args):
    if args.shutterMode:
        cam.set_shooting_mode(args.shutterMode, True)
    if args.restore:
        cam.set_shooting_mode('single', True)
    if args.get_shutterMode:
        print_current_state(cam.get_shooting_mode(True), "Shutter Mode State")


def selfTimer(args):
    if args.timer:
        cam.set_self_timer(args.timer, True)
    if args.restore:
        cam.set_self_timer('0', True)
    if args.get_timer:
        print_current_state(cam.get_self_timer(True), "Self-Timer State")


def expBracketing(args):
    if args.enable:
        if args.enable == '1':
            cam.enable_exp_bracketing(True)
        elif args.enable == '0':
            cam.disable_exp_bracketing(True)
    if args.count:
        cam.set_exposure_bracket_size(args.count, True)
    if args.offset:
        cam.set_exposure_bracket_offset(args.offset, True)
    if args.restore:
        cam.disable_exp_bracketing(True)
    if args.get_bracket:
        print_current_state(cam.get_exp_bracketing(True), "Exposure Bracket State")


def focusBracketing(args):
    if args.enable:
        if args.enable == '1':
            cam.enable_focus_bracketing(True)
        elif args.enable == '0':
            cam.disable_focus_bracketing(True)
    if args.count:
        cam.set_focus_bracket_size(args.count, True)
    if args.offset:
        cam.set_focus_bracket_offset(args.offset, True)
    if args.restore:
        cam.disable_focus_bracketing(True)
    if args.get_bracket:
        print_current_state(cam.get_focus_bracketing(True), "Focus Bracket State")


def sleepTimer(args):
    if args.sleep:
        if args.sleep == '0':
            cam.disable_timeout(True)
        else:
            cam.set_timeout(args.sleep, True)
    if args.restore:
        cam.set_timeout(120, True)
    if args.get_sleep:
        print_current_state(cam.get_timeout_value(True), "Sleep Timer set to")


def meteringMode(args):
    if args.meter:
        cam.set_metering_mode(args.meter, True)
    if args.restore:
        cam.set_metering_mode('evaluative', True)
    if args.get_meter:
        print_current_state(cam.get_metering_mode(True), "Metering Mode")


def flashSync(args):
    if args.flashSync:
        cam.set_flash_sync_mode(args.flashSync, True)
    if args.restore:
        cam.set_flash_sync_mode('front', True)
    if args.get_flashSync:
        print_current_state(cam.get_flash_sync_mode(True), "Flash Sync Mode")


def flashAF(args):
    if args.flashAF:
        cam.set_flashAF_assist(args.flashAF, True)
    if args.restore:
        cam.set_flashAF_assist('1', True)
    if args.get_flashAF:
        print_current_state(cam.get_flashAF_assist(True), "Flash AF Assist Mode")


def flashExpComp(args):
    if args.flashExpComp is not None:
        cam.set_exposure_flash_compensation(args.flashExpComp, True)
    if args.restore:
        cam.set_exposure_flash_compensation(0, True)
    if args.get_flashExpComp:
        print_current_state(cam.get_exposure_flash_compensation(True), "Flash Exposure Compensation Mode")


def touchInput(args):
    cam.send_touch_event(args.xcoord, args.ycoord, args.sleep, args.repeat, True)


def swipeInput(args):
    cam.send_swipe_event(args.direction, args.sleep, args.repeat, True)


def buttonPress(args):
    if args.buttonPress.lower() == "shutter":
        cam.press_shutter(args.repeat, args.sleep, True)
    elif args.buttonPress.lower() == "depthassist":
        cam.press_lytro(args.repeat, args.sleep, True)
    elif args.buttonPress.lower() == "power":
        cam.press_power(args.repeat, args.sleep, True)
    elif args.buttonPress.lower() == "af":
        cam.press_af(args.repeat, args.sleep, True)
    elif args.buttonPress.lower() == "ael":
        cam.press_ael(args.repeat, args.sleep, True)
    elif args.buttonPress.lower() == "hyperfocal":
        cam.press_hyperfocal(args.repeat, args.sleep, True)
    elif args.buttonPress.lower() == "fn":
        cam.press_fn(args.repeat, args.sleep, True)


def captureImage(args):
    bld.check_space_and_framing(args.count, cam.get_pictures_remaining(True))
    cam.disable_focus_bracketing(True)
    cam.disable_exp_bracketing(True)
    if args.count > 10:
        sleep_timer = cam.get_timeout_value(True)
        cam.disable_timeout(True)
        cam.capture_wait(args.count, args.sleep, True)
        cam.set_timeout(sleep_timer, True)
    else:
        cam.capture_wait(args.count, args.sleep, True)


def main():


    ''' WHITE BALANCE '''

    p_whiteBalance = subparser.add_parser("whiteBalance",
                                          description=textwrap.dedent(
                                          ''' Setters and getters for whiteBalance setting '''),
                                          help="Adjust and get current whiteBalance state")

    p_whiteBalance.add_argument("-s",
                                "--set",
                                dest='wb_preset',
                                choices=['auto', 'tungsten', 'fluorescent', 'flash', 'daylight',
                                         'cloudy', 'shade', 'custom'],
                                help="WhiteBalance choices are: ['auto', 'tungsten', 'fluorescent', "
                                     "'flash', 'daylight', 'cloudy', 'shade', 'custom']",
                                metavar=" ")

    p_whiteBalance.add_argument("-g",
                                "--get",
                                action="store_true",
                                default=False,
                                help="Get current WhiteBalance Mode",
                                dest='get_wb_preset')

    p_whiteBalance.set_defaults(func=whiteBalance)


    ''' EXPOSURE MODE '''

    p_exposureMode = subparser.add_parser("exposureMode",
                                          description=textwrap.dedent(
                                          ''' Setters and getters for exposureMode setting '''),
                                          help="Adjust and get current exposureMode state")

    p_exposureMode.add_argument("-s",
                                "--set",
                                dest='exp_mode',
                                choices=['program', 'iso', 'shutter', 'manual'],
                                help="ExposureMode choices are: ['program', 'iso', 'shutter', 'manual']",
                                metavar=" ")

    p_exposureMode.add_argument("-g",
                                "--get",
                                action="store_true",
                                default=False,
                                help="Get current exposureMode state",
                                dest='get_exp_mode')

    p_exposureMode.set_defaults(func=exposureMode)



    '''  EXPOSURE COMPENSATION MODE '''

    p_exposureComp = subparser.add_parser("exposureComp",
                                          description=textwrap.dedent(
                                          ''' Setters and getters for Exposure Compensation setting '''),
                                          help="Adjust and get current Exposure Compensation state")

    p_exposureComp.add_argument("-s",
                                "--set",
                                dest='exp_comp',
                                type=float,
                                choices=[-2.0, -1.7, -1.3, -1.0, -0.7, -0.3, 0, 0.3, 0.7, 1.0, 1.3, 1.7, 2.0],
                                help="Exposure Compensation valid values: [-2.0, -1.7, -1.3, -1.0, -0.7, -0.3, 0, +0.3,"
                                     " +0.7, +1.0, +1.3, +1.7, +2.0]",
                                metavar=" ")

    p_exposureComp.add_argument("-g",
                                "--get",
                                action="store_true",
                                default=False,
                                help="Get current exposureMode state",
                                dest='get_exp_comp')

    p_exposureComp.set_defaults(func=exposureComp)


    ''' ISO '''

    p_iso = subparser.add_parser("iso",
                                 description=textwrap.dedent(
                                 ''' Setters and getters for iso setting '''),
                                 help="Adjust and get current iso value")

    p_iso.add_argument("-s",
                       "--set",
                       dest='iso',
                       type=int,
                       choices=[80, 100, 125, 160, 200, 250, 320, 400, 500,
                                640, 800, 1000, 1250, 1600, 2000, 2500, 3200],
                       help="iso ranges 80-3200",
                       metavar=" ")

    p_iso.add_argument("-g",
                       "--get",
                       action="store_true",
                       default=False,
                       help="Get current iso value",
                       dest='get_iso')

    p_iso.set_defaults(func=iso)




    ''' SHUTTER SPEED '''

    p_shutterSpeed = subparser.add_parser("shutterSpeed",
                                          description=textwrap.dedent(
                                          ''' Setters and getters for shutterSpeed setting '''),
                                          help="Adjust and get current shutterSpeed value")

    p_shutterSpeed.add_argument("-s",
                                "--set",
                                dest='sp',
                                type=check_shutterSpeed_range,
                                help="shutters speed ranges 1/4000 - 32",
                                metavar=" ")

    p_shutterSpeed.add_argument("-g",
                                "--get",
                                action="store_true",
                                default=False,
                                help="Get current shutter speed value",
                                dest='get_sp')

    p_shutterSpeed.set_defaults(func=shutterSpeed)



    ''' FOCUS STEP '''

    p_focusStep = subparser.add_parser("focusStep",
                                       description=textwrap.dedent(
                                       ''' Setters and getters for focus step setting '''),
                                       help="Adjust and retrieve current focus step value")

    p_focusStep.add_argument("-s",
                             "--set",
                             dest='focusStep',
                             type=int,
                             help="Total Focus Range 1 - 1522",
                             metavar=" ")

    p_focusStep.add_argument("-g",
                             "--get",
                             action="store_true",
                             default=False,
                             help="Get current focus step",
                             dest='get_focusStep')

    p_focusStep.set_defaults(func=focusStep)



    ''' ZOOM STEP '''

    p_zoomStep = subparser.add_parser("zoomStep",
                                      description=textwrap.dedent(
                                      ''' Setters and getters for zoom step setting '''),
                                      help="Adjust and retrieve zoom step value")

    p_zoomStep.add_argument("-s",
                            "--set",
                            dest='zoomStep',
                            type=check_zoom_range,
                            help="zoomSteps range [1 - {}]".format(cam.max_user_zoom_step),
                            metavar=" ")

    p_zoomStep.add_argument("-g",
                            "--get",
                            action="store_true",
                            default=False,
                            help="Get current zoom step",
                            dest='get_zoomStep')

    p_zoomStep.set_defaults(func=zoomStep)



    ''' OPTICAL OFFSET '''

    p_opticalOffset = subparser.add_parser("opticalOffset",
                                           description=textwrap.dedent(
                                           ''' Setters and getters for optical offset setting '''),
                                           help="Adjust and retrieve optical offset value")

    p_opticalOffset.add_argument("-s",
                                 "--set",
                                 dest='optOffset',
                                 type=functools.partial(check_range, val_range=(-10, 10), string="Optical Offset"),
                                 help="opticalOffset range [-10 to +10]",
                                 metavar=" ")

    p_opticalOffset.add_argument("-g",
                                 "--get",
                                 action="store_true",
                                 default=False,
                                 help="Get current optical offset value",
                                 dest='get_optOffset')

    p_opticalOffset.add_argument("-r",
                                 "--restore",
                                 action="store_true",
                                 default=False,
                                 help="Restore to default, value of -4",
                                 dest='restore_optOffset')

    p_opticalOffset.set_defaults(func=opticalOffset)



    ''' FOCUS LOCK '''

    p_focusLock = subparser.add_parser("focusLock",
                                       description=textwrap.dedent(
                                       ''' Setters and getters for focus lock setting '''),
                                       help="Adjust and retrieve focus lock value")

    p_focusLock.add_argument("-s",
                             "--set",
                             dest='focusLockState',
                             choices=['0', '1'],
                             help="Disable or enable use 0 or 1",
                             metavar=" ")

    p_focusLock.add_argument("-g",
                             "--get",
                             action="store_true",
                             default=False,
                             help="Get current focusLock state",
                             dest='get_focusLockState')

    p_focusLock.add_argument("-r",
                             "--restore",
                             action="store_true",
                             default=False,
                             help="Restore to default, value of 0",
                             dest='restore')

    p_focusLock.set_defaults(func=focusLock)



    ''' ZOOM LOCK '''

    p_zoomLock = subparser.add_parser("zoomLock",
                                      description=textwrap.dedent(
                                      ''' Setters and getters for zoom ring lock setting '''),
                                      help="Adjust and retrieve zoom ring lock setting")

    p_zoomLock.add_argument("-s",
                            "--set",
                            dest='zoomLockState',
                            choices=['0', '1'],
                            help="Disable or enable use 0 or 1",
                            metavar=" ")

    p_zoomLock.add_argument("-g",
                            "--get",
                            action="store_true",
                            default=False,
                            help="Get current zoomLock state",
                            dest='get_zoomLockState')

    p_zoomLock.add_argument("-r",
                            "--restore",
                            action="store_true",
                            default=False,
                            help="Restore to default, value of 0",
                            dest='restore')

    p_zoomLock.set_defaults(func=zoomLock)



    ''' AE LOCK '''

    p_aeLock = subparser.add_parser("aeLock",
                                    description=textwrap.dedent(
                                    ''' Setters and getters for Auto Exposure lock setting '''),
                                    help="Adjust and retrieve Auto Exposure lock setting")

    p_aeLock.add_argument("-s",
                          "--set",
                          dest='aeLockState',
                          choices=['0', '1'],
                          help="Disable or enable use 0 or 1",
                          metavar=" ")

    p_aeLock.add_argument("-g",
                          "--get",
                          action="store_true",
                          default=False,
                          help="Get current AutoExposure Lock state",
                          dest='get_aeLockState')

    p_aeLock.add_argument("-r",
                          "--restore",
                          action="store_true",
                          default=False,
                          help="Restore to default, value of 0",
                          dest='restore')

    p_aeLock.set_defaults(func=aeLock)


    ''' DEPTH FEEDBACK '''

    p_depthFeedBack = subparser.add_parser("depthAssist",
                                           description=textwrap.dedent(
                                           ''' Setters and getters for Depth Assist setting '''),
                                           help="Adjust and retrieve Depth Assist setting")

    p_depthFeedBack.add_argument("-s",
                                 "--set",
                                 dest='depthFeed',
                                 choices=['0', '1'],
                                 help="Disable or enable use 0 or 1",
                                 metavar=" ")

    p_depthFeedBack.add_argument("-g",
                                 "--get",
                                 action="store_true",
                                 default=False,
                                 help="Get current Depth Assist state",
                                 dest='get_depthFeed')

    p_depthFeedBack.add_argument("-r",
                                 "--restore",
                                 action="store_true",
                                 default=False,
                                 help="Restore to default, value of 0",
                                 dest='restore')

    p_depthFeedBack.set_defaults(func=depthFeedback)


    ''' FOCUS DRIVE MODE '''

    p_focusMode = subparser.add_parser("focusMode",
                                       description=textwrap.dedent(
                                       ''' Setters and getters for Focus Mode setting '''),
                                       help="Adjust and retrieve Focus Mode setting")

    p_focusMode.add_argument("-s",
                             "--set",
                             dest='focusMode',
                             choices=['auto', 'manual'],
                             help="Choices are ['auto' or 'manual']",
                             metavar=" ")

    p_focusMode.add_argument("-g",
                             "--get",
                             action="store_true",
                             default=False,
                             help="Get current Focus Mode state",
                             dest='get_focusMode')

    p_focusMode.add_argument("-r",
                             "--restore",
                             action="store_true",
                             default=False,
                             help="Restore to default, value of 'auto'",
                             dest='restore')

    p_focusMode.set_defaults(func=focusMode)


    ''' SHUTTER MODE '''

    p_shutterMode = subparser.add_parser("shutterMode",
                                         description=textwrap.dedent(
                                         ''' Setters and getters for Shutter Mode setting '''),
                                         help="Adjust and retrieve Shutter Mode setting")

    p_shutterMode.add_argument("-s",
                               "--set",
                               dest='shutterMode',
                               choices=['single', 'continuous'],
                               help="Choices are ['single' or 'continuous']",
                               metavar=" ")

    p_shutterMode.add_argument("-g",
                               "--get",
                               action="store_true",
                               default=False,
                               help="Get current Shutter Mode state",
                               dest='get_shutterMode')

    p_shutterMode.add_argument("-r",
                               "--restore",
                               action="store_true",
                               default=False,
                               help="Restore to default, value of 'single'",
                               dest='restore')

    p_shutterMode.set_defaults(func=shutterMode)




    ''' SELF TIMER '''

    p_selfTimer = subparser.add_parser("selfTimer",
                                       description=textwrap.dedent(
                                       ''' Setters and getters for Self-Timer Mode setting '''),
                                       help="Adjust and retrieve Self-Timer Mode setting")

    p_selfTimer.add_argument("-s",
                             "--set",
                             dest='timer',
                             choices=['0', '2', '10'],
                             help="Timer in secs [0, 2, 10] ",
                             metavar=" ")

    p_selfTimer.add_argument("-g",
                             "--get",
                             action="store_true",
                             default=False,
                             help="Get current Self-Timer state",
                             dest='get_timer')

    p_selfTimer.add_argument("-r",
                             "--restore",
                             action="store_true",
                             default=False,
                             help="Restore to default, value of 'disabled'",
                             dest='restore')

    p_selfTimer.set_defaults(func=selfTimer)



    ''' EXPOSURE BRACKETING '''


    p_expBracketing = subparser.add_parser("expBracketing",
                                           description=textwrap.dedent(
                                           ''' Setters and getters for Exposure Bracketing setting '''),
                                           help="Adjust and retrieve Exposure Bracketing setting")

    p_expBracketing.add_argument("-s",
                                 "--set",
                                 dest='enable',
                                 choices=['0', '1'],
                                 help="Disable or enable Exposure Bracketing. Choose 0 or 1",
                                 metavar=" ")

    p_expBracketing.add_argument("-o",
                                 "--offset",
                                 dest='offset',
                                 type=check_bracketing_range,
                                 help="Exposure stop size [1/3, 2/3, 1, 2]",
                                 metavar=" ")

    p_expBracketing.add_argument("-c",
                                 "--count",
                                 dest='count',
                                 type=int,
                                 choices=[3, 5],
                                 help="Number of bracketed captures 3 or 5",
                                 metavar=" ")

    p_expBracketing.add_argument("-g",
                                 "--get",
                                 action="store_true",
                                 default=False,
                                 help="Get current Exposure Bracketing state",
                                 dest='get_bracket')

    p_expBracketing.add_argument("-r",
                                 "--restore",
                                 action="store_true",
                                 default=False,
                                 help="Restore to default, value of '0'",
                                 dest='restore')

    p_expBracketing.set_defaults(func=expBracketing)




    ''' FOCUS BRACKETING '''


    p_expBracketing = subparser.add_parser("focusBracketing",
                                           description=textwrap.dedent(
                                           ''' Setters and getters for Focus Bracketing setting '''),
                                           help="Adjust and retrieve Focus Bracketing setting")

    p_expBracketing.add_argument("-s",
                                 "--set",
                                 dest='enable',
                                 choices=['0', '1'],
                                 help="Disable or enable Focus Bracketing. Choose 0 or 1",
                                 metavar=" ")

    p_expBracketing.add_argument("-o",
                                 "--offset",
                                 dest='offset',
                                 type=functools.partial(check_range, val_range=(1, 10), string="Focus Bracketing DS"),
                                 help="Focus DS stop values [1 - 10]",
                                 metavar=" ")

    p_expBracketing.add_argument("-c",
                                 "--count",
                                 dest='count',
                                 type=int,
                                 choices=[3, 5],
                                 help="Number of bracketed captures 3 or 5",
                                 metavar=" ")

    p_expBracketing.add_argument("-g",
                                 "--get",
                                 action="store_true",
                                 default=False,
                                 help="Get current Focus Bracketing state",
                                 dest='get_bracket')

    p_expBracketing.add_argument("-r",
                                 "--restore",
                                 action="store_true",
                                 default=False,
                                 help="Restore to default, value of '0'",
                                 dest='restore')

    p_expBracketing.set_defaults(func=focusBracketing)



    ''' SLEEP TIMER '''

    p_sleepTimer = subparser.add_parser("sleepTimer",
                                        description=textwrap.dedent(
                                        ''' Setters and getters for Sleep Timer setting '''),
                                        help="Adjust and retrieve Sleep Timer setting")

    p_sleepTimer.add_argument("-s",
                              "--set",
                              dest='sleep',
                              choices=['0', '15', '30', '60', '120', '300', '600', '1800'],
                              help="Sleep Timer in secs. Set to '0' to disable.",
                              metavar=" ")

    p_sleepTimer.add_argument("-g",
                              "--get",
                              action="store_true",
                              default=False,
                              help="Get current Sleep Timer state",
                              dest='get_sleep')

    p_sleepTimer.add_argument("-r",
                              "--restore",
                              action="store_true",
                              default=False,
                              help="Restore to default, value of '120' secs",
                              dest='restore')

    p_sleepTimer.set_defaults(func=sleepTimer)



    ''' METERING MODE '''

    p_meteringMode = subparser.add_parser("meteringMode",
                                          description=textwrap.dedent(
                                          ''' Setters and getters for Metering Mode setting '''),
                                          help="Adjust and retrieve Metering Mode setting")

    p_meteringMode.add_argument("-s",
                                "--set",
                                dest='meter',
                                choices=['average', 'evaluative'],
                                help="set Metering Mode to ['average' or 'evaluative'] ",
                                metavar=" ")

    p_meteringMode.add_argument("-g",
                                "--get",
                                action="store_true",
                                default=False,
                                help="Get current Metering Mode state",
                                dest='get_meter')

    p_meteringMode.add_argument("-r",
                                "--restore",
                                action="store_true",
                                default=False,
                                help="Restore to default, value of 'evaluative'",
                                dest='restore')

    p_meteringMode.set_defaults(func=meteringMode)



    ''' FLASH SYNC '''

    p_flashSync = subparser.add_parser("flashSync",
                                       description=textwrap.dedent(
                                       ''' Setters and getters for Flash Sync setting '''),
                                       help="Adjust and retrieve Flash Sync setting")

    p_flashSync.add_argument("-s",
                             "--set",
                             dest='flashSync',
                             choices=['back', 'front'],
                             help="Switch between front curtain or back curtain modes ['back' or 'front'] ",
                             metavar=" ")

    p_flashSync.add_argument("-g",
                             "--get",
                             action="store_true",
                             default=False,
                             help="Get current Flash Sync state",
                             dest='get_flashSync')

    p_flashSync.add_argument("-r",
                             "--restore",
                             action="store_true",
                             default=False,
                             help="Restore to default, disabled, value of f '0'",
                             dest='restore')

    p_flashSync.set_defaults(func=flashSync)


    ''' FLASH AF ASSIST '''

    p_flashAF = subparser.add_parser("flashAF",
                                     description=textwrap.dedent(
                                     ''' Setters and getters for Flash AF Assist setting '''),
                                     help="Adjust and retrieve Flash AF Assist setting")

    p_flashAF.add_argument("-s",
                             "--set",
                             dest='flashAF',
                             choices=['0', '1'],
                             help="Disable or Enable Flash AF Assist mode [0 or 1] ",
                             metavar=" ")

    p_flashAF.add_argument("-g",
                           "--get",
                           action="store_true",
                           default=False,
                           help="Get current Flash AF Assist state",
                           dest='get_flashAF')

    p_flashAF.add_argument("-r",
                           "--restore",
                           action="store_true",
                           default=False,
                           help="Restore to default, value of 'front curtain'",
                           dest='restore')

    p_flashAF.set_defaults(func=flashAF)



    ''' FLASH EXPOSURE COMPENSATION '''

    p_flashExpComp = subparser.add_parser("flashExpComp",
                                          description=textwrap.dedent(
                                          ''' Setters and getters for Flash Exposure Compensation setting '''),
                                          help="Adjust and retrieve Flash Exposure Compensation setting")

    p_flashExpComp.add_argument("-s",
                                "--set",
                                dest='flashExpComp',
                                type=functools.partial(check_range, val_range=(-3, 3),
                                     string="Flash Exposure Compensation"),
                                help="Flash Exposure Compensation values [-3 to +3] ",
                                metavar=" ")

    p_flashExpComp.add_argument("-g",
                                "--get",
                                action="store_true",
                                default=False,
                                help="Get current Flash Exposure Compensation state",
                                dest='get_flashExpComp')

    p_flashExpComp.add_argument("-r",
                                "--restore",
                                action="store_true",
                                default=False,
                                help="Restore to default, value of '0'",
                                dest='restore')

    p_flashExpComp.set_defaults(func=flashExpComp)



    ''' INPUT TOUCH EVENT '''

    p_inputTouch = subparser.add_parser("sendTouchEvent",
                                        description=textwrap.dedent(
                                        ''' Send touch event by specifying x and y coordinates '''),
                                        help="Send touch event by specifying x and y coordinates")

    p_inputTouch.add_argument("-x",
                              "--xcoord",
                              dest='xcoord',
                              type=functools.partial(check_range, val_range=(1, 799),
                                   string="x coordinate"),
                              default=400,
                              help="x coordinate ranges [1 to 799] ",
                              metavar=" ")

    p_inputTouch.add_argument("-y",
                              "--ycoord",
                              dest='ycoord',
                              type=functools.partial(check_range, val_range=(1, 479),
                                   string="y coordinate"),
                              default=250,
                              help="y coordinate ranges [1 to 479] ",
                              metavar=" ")

    p_inputTouch.add_argument("-sl",
                              "--sleep",
                              dest='sleep',
                              type=int,
                              default=1,
                              help="Sleep in secs after sending touch event ",
                              metavar=" ")


    p_inputTouch.add_argument("-re",
                              "--repeat",
                              dest='repeat',
                              type=int,
                              default=1,
                              help="Number of iterations ",
                              metavar=" ")

    p_inputTouch.set_defaults(func=touchInput)


    ''' INPUT SWIPE EVENT '''

    p_inputSwipe = subparser.add_parser("sendSwipeEvent",
                                        description=textwrap.dedent(
                                        ''' Send swipe gesture event by specifying direction: left, right,
                                         up or down  '''),
                                        help="Send swipe gesture event by specifying direction: left, right,up or down")

    p_inputSwipe.add_argument("-d",
                              "--direction",
                              dest='direction',
                              choices=["left", "right", "up", "down"],
                              help="Set swipe direction, [up, down left or right] ",
                              metavar=" ")

    p_inputSwipe.add_argument("-sl",
                              "--sleep",
                              dest='sleep',
                              type=int,
                              default=1,
                              help="Sleep in secs after sending swipe event ",
                              metavar=" ")

    p_inputSwipe.add_argument("-re",
                              "--repeat",
                              dest='repeat',
                              type=int,
                              default=1,
                              help="Number of iterations ",
                              metavar=" ")

    p_inputSwipe.set_defaults(func=swipeInput)





    ''' PHYSICAL CONTROLS '''


    p_buttonPress = subparser.add_parser("physicalControls",
                                         description=textwrap.dedent(
                                         ''' Send button press event '''),
                                         help="Send button press event")

    p_buttonPress.add_argument("-pr",
                               "--press",
                               dest='buttonPress',
                               choices=['shutter', 'depthAssist', 'power', 'AF',
                                        'AEL', 'hyperFocal', 'Fn'],
                               help="Send button press event. ['shutter', 'depthAssist', 'power', 'AF', "
                                    "'AEL', 'hyperFocal', 'Fn'] ",
                               metavar=" ")


    p_buttonPress.add_argument("-sl",
                               "--sleep",
                               dest='sleep',
                               type=int,
                               default=1,
                               help="Sleep in secs after sending button press ",
                               metavar=" ")


    p_buttonPress.add_argument("-re",
                               "--repeat",
                               dest='repeat',
                               type=int,
                               default=1,
                               help="Number of iterations ",
                               metavar=" ")

    p_buttonPress.set_defaults(func=buttonPress)



    ''' CAPTURE IMAGE '''


    p_buttonPress = subparser.add_parser("captureImage",
                                         description=textwrap.dedent(
                                         ''' Send capture command  '''),
                                         help="Send capture command")

    p_buttonPress.add_argument("-p",
                               "--pictures",
                               dest='count',
                               type=int,
                               default=1,
                               help="Number of pictures to take",
                               metavar=" ")

    p_buttonPress.add_argument("-as",
                               "--addSleep",
                               dest='sleep',
                               type=int,
                               default=0,
                               help="Additional sleep on top of processing time ",
                               metavar=" ")

    p_buttonPress.set_defaults(func=captureImage)


    args = parser.parse_args()

    cam.handle_if_adb_not_running()

    if args.verbose:
        cam.verbose = True
    cam.init(False)

    try:
        if args.focusStep:
            check_focus_range(args.focusStep)
    except AttributeError:
        pass

    args.func(args)

    cam.disable_virtual_cable(True)


if __name__ == "__main__":

    main()

