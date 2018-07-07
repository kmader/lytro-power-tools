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
__version__ = '1.0.3'

import os
import sys

try:
    import lpt
except ImportError:

    mod_dir = os.path.dirname(os.path.realpath(__file__))
    lpt_dir = os.path.abspath(os.path.join(mod_dir, '../..'))
    sys.path.insert(0, lpt_dir)
    import lpt

from lpt.camera import camerabin

import time
import json
import argparse
import subprocess
import shlex


class Build:

    def __init__(self):

        self.cam = camerabin.CameraControls()

        self.dwl_and_del_string = "Deletes ALL pictures from camera after import is complete"

        self.dwl_string = "Downloads images to the local file system'"

        self.adb = "adb shell "

        self.epilog = "Lytro Developer Kit Camera {} Tool"

        self.min_proc_time = 10

        self.parser = argparse.ArgumentParser(epilog=self.epilog.format('Control'),
                                              description="LYTRO DEVELOPER KIT CAMERA TOOL \nsee help on "
                                                          "individual sub commands for details",
                                              prog="cameratool",
                                              formatter_class=argparse.RawTextHelpFormatter)

        self.real_path = os.path.dirname(os.path.realpath(__file__))
        self.base_path = os.path.join(self.real_path, '..')



        abspath = lambda p, c: os.path.abspath(os.path.join(p, c))

        if sys.platform == 'darwin':
            home = os.getenv('HOME')
            self.cal_data_path = abspath(home, 'Library/Application\ Support/Lytro')
            self.currentDir = os.getcwd()


        elif sys.platform == 'win32':
            profile = os.getenv('USERPROFILE')
            self.cal_data_path = abspath(profile, 'AppData\Local\Lytro')
            self.currentDir = os.getcwd().replace(r"\\", r"\\\\")

        else:
            raise OSError("unsupported operating system: " + sys.platform)


    def check_min_value(self, x, subparser_caller):

        if subparser_caller in "exp-bracketing" "focus-bracketing":
            x = int(x)
            if x < 1:
                raise argparse.ArgumentTypeError("Invalid input '{}'.  Minimum reps is 1".format(x))
            return x

        #If sleep time we want to keep it a float.
        elif subparser_caller == "interval":
            x = float(x)
            if x < 0:
                raise argparse.ArgumentTypeError("Invalid input '{}'. Negative values not accepted".format(x))
            return x

        elif subparser_caller in "focus-sweep" "zoom-sweep":
            x = int(x)
            if x < 2:
                raise argparse.ArgumentTypeError("Invalid input '{}'. Minimum captures is 2".format(x))
            return x

        else:
            x = int(x)
            if x < 0:
                raise argparse.ArgumentTypeError("Invalid input '{}'. Negative values not accepted".format(x))
            return x




    def number(self, obj):
        # returns an int if obj % 1 == 0 else return a float
        f = float(obj)
        n = lambda x: int(x) if (float(x) % 1 == 0) else x
        return n(f)


    def check_range(self, obj, arg_range, arg_name='value'):
        # verify that 'obj' is a number and within an acceptable range
        try:
            num = self.number(obj=obj)
        except ValueError as err:
            raise argparse.ArgumentTypeError(str(err))

        # arg_range is a tuple, e.g. (1, 10)
        min_, max_ = arg_range

        # do comparison(s)
        if min_ and max_:
            if min_ <= num <= max_:
                return num
        elif min_:
            if num >= min_:
                return num
        elif max_:
            if num <= max_:
                return num

        # if the above comparisons fail to return, run a function or simply display parser error:
        message = ("{arg_name} out of range: '{obj}' (min: {min_} | max: {max_})\n"
                   .format(arg_name=arg_name, obj=obj, min_=min_, max_=max_))
        self.parser.error(message)


    def get_focus_range(self, zoom):
        if zoom == 1:
            return [972, 1521]
        min_focus = 1
        max_focus_step_for_given_zoom = {'2': '982',
                                         '3': '705',
                                         '4': '563',
                                         '5': '542',
                                         '6': '642',
                                         '7': '882',
                                         '8': '1187'}
        return [min_focus, int(max_focus_step_for_given_zoom[str(zoom)])]


    def push_args_to_camera(self, args):
        json_obj = json.dumps(args)
        os.system("adb push {} storage/sdcard1/".format(json_obj))

    def setup_captures_script(self, args):
        #Convert from namespace object to dictionary
        args_dict = vars(args)
        user_timeout = self.cam.get_timeout_value(True)
        self.cam.init()
        picture_count = args_dict['pictures']
        self.check_space_and_framing(picture_count, self.cam.get_pictures_remaining(True))
        args_dict.update({'func': 'self.perform_captures()',
                          'tool_name': 'Captures',
                          'total_captures': picture_count,
                          'sleep_timeout': user_timeout,
                          'label_margin': 150,
                          'script_duration': "Not finished"})
        self.log_to_json(args_dict)
        self.push_files_to_sdcard()
        self.launch_scripts()


    def setup_cont_captures_script(self, args):
        #Convert from namespace object to dictionary
        args_dict = vars(args)
        user_timeout = self.cam.get_timeout_value(True)
        self.cam.init()
        picture_count = args_dict['reps'] * args_dict['capture_size']
        self.check_space_and_framing(picture_count, self.cam.get_pictures_remaining(True))
        args_dict.update({'func': 'self.perform_cont_captures()',
                          'tool_name': 'Cont Captures',
                          'total_captures': picture_count,
                          'sleep_timeout': user_timeout,
                          'label_margin': 65,
                          'script_duration': "Not finished"})
        self.log_to_json(args_dict)
        self.push_files_to_sdcard()
        self.launch_scripts()


    def setup_exp_bracketing_script(self, args):
        #Convert from namespace object to dictionary
        args_dict = vars(args)
        user_timeout = self.cam.get_timeout_value(True)
        self.cam.init()
        picture_count = args_dict['size'] * args_dict['reps']
        self.check_space_and_framing(picture_count, self.cam.get_pictures_remaining(True))
        args_dict.update({'func': 'self.perform_exp_bracketing()',
                          'tool_name': 'Exp Bracketing',
                          'total_captures': picture_count,
                          'sleep_timeout': user_timeout,
                          'label_margin': 45,
                          'script_duration': "Not finished"})
        self.log_to_json(args_dict)
        self.push_files_to_sdcard()
        self.launch_scripts()



    def setup_focus_bracketing_script(self, args):
        #Convert from namespace object to dictionary
        args_dict = vars(args)
        user_timeout = self.cam.get_timeout_value(True)
        self.cam.init()
        picture_count = args_dict['size'] * args_dict['reps']
        self.check_space_and_framing(picture_count, self.cam.get_pictures_remaining(True))
        args_dict.update({'func': 'self.perform_focus_bracketing()',
                          'tool_name': 'Focus Bracketing',
                          'total_captures': picture_count,
                          'sleep_timeout': user_timeout,
                          'label_margin': 10,
                          'script_duration': "Not finished"})
        self.log_to_json(args_dict)
        self.push_files_to_sdcard()
        self.launch_scripts()


    def setup_focus_sweep_script(self, args):
        #Convert from namespace object to dictionary
        args_dict = vars(args)
        user_timeout = self.cam.get_timeout_value(True)
        self.cam.init()
        picture_count = args_dict['pictures']
        self.check_space_and_framing(picture_count, self.cam.get_pictures_remaining(True))
        args_dict.update({'func': 'self.perform_focus_sweep()',
                          'tool_name': 'Focus Sweep',
                          'total_captures': picture_count,
                          'sleep_timeout': user_timeout,
                          'label_margin': 100,
                          'script_duration': "Not finished"})
        self.log_to_json(args_dict)
        self.push_files_to_sdcard()
        self.launch_scripts()

    def setup_zoom_sweep_script(self, args):
        #Convert from namespace object to dictionary
        args_dict = vars(args)
        user_timeout = self.cam.get_timeout_value(True)
        self.cam.init()
        picture_count = args_dict['pictures']
        self.check_space_and_framing(picture_count, self.cam.get_pictures_remaining(True))
        args_dict.update({'func': 'self.perform_zoom_sweep()',
                          'tool_name': 'Zoom Sweep',
                          'total_captures': picture_count,
                          'sleep_timeout': user_timeout,
                          'label_margin': 120,
                          'script_duration': "Not finished"})
        self.log_to_json(args_dict)
        self.push_files_to_sdcard()
        self.launch_scripts()


    def send_command(self, cmd):
        out = subprocess.Popen(shlex.split(self.adb + cmd), stdout=subprocess.PIPE)
        #makes previous call blocking
        out.communicate()[0]


    def check_space_and_framing(self, picture_count, pictures_remaining):
        #If cameratool is not awake it will not run the script.
        if int(pictures_remaining) == 0:
            print"\nTurn ON camera display and try again. Make sure sdcard is properly mounted and that is not completely "\
                 "full\n\n"
            self.cam.disable_virtual_cable(True)
            sys.exit()

        elif int(picture_count) > int(pictures_remaining):
            print "\nNot enough space in your sdcard to accomodate {} pictures.\n\n".format(picture_count)
            self.cam.disable_virtual_cable(True)
            sys.exit()

    def log_to_json(self, dict):
        json_file = os.path.join(self.real_path, "args.json")
        with open(json_file, "w") as json_file:
            json.dump(dict, json_file, indent=4)
            json_file.close()

    def push_files_to_sdcard(self):
        sdcard_path = 'storage/sdcard1'
        print "\nPush 'args.json' to {}".format(sdcard_path)
        os.system("adb push {source} {dest}".format(source=os.path.join(self.real_path, "args.json"), dest=sdcard_path))
        time.sleep(.5)
        print "\nPush 'run.py' to {}".format(sdcard_path)
        os.system("adb push {source} {dest}".format(source=os.path.join(self.real_path, "run.py"), dest=sdcard_path))
        time.sleep(.5)
        print "\nPush 'camerabin.py' to {}".format(sdcard_path)
        os.system("adb push {source} {dest}".format(source=os.path.join(self.real_path, "camerabin.py"),
                                                    dest=sdcard_path))
        time.sleep(.5)
        print "\nPush '__init__.py' to {}".format(sdcard_path)
        os.system("adb push {source} {dest}".format(source=os.path.join(self.real_path, "__init__.py"),
                                                    dest=sdcard_path))
        time.sleep(.5)


    def launch_scripts(self):
        # Button combination press to start scripts.
        os.system("adb shell sendevent /dev/input/event2 1 557 1")
        os.system("adb shell sendevent /dev/input/event2 0 0 0")
        time.sleep(.5)
        os.system("adb shell sendevent /dev/input/event2 1 559 1")
        os.system("adb shell sendevent /dev/input/event2 0 0 0")
        time.sleep(4)
        os.system("adb shell sendevent /dev/input/event2 1 557 0")
        os.system("adb shell sendevent /dev/input/event2 0 0 0")
        os.system("adb shell sendevent /dev/input/event2 1 559 0")
        os.system("adb shell sendevent /dev/input/event2 0 0 0")
        print "\nYou can now disconnect USB cable and press start on camera display to begin \n"
