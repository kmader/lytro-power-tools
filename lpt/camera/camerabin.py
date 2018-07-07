# -*- coding: utf-8 -*-
"""Lytro Power Tools - camera package - camera controls"""

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


import time
import os
import subprocess
import json
import shlex
import sys
import re
import signal
import functools


class CameraControls:

    def __init__(self):
        self.adb = "adb shell "
        self.prefix = ""
        self.max_real_focus_step = 1308
        self.max_user_focus_step = 1645
        self.max_real_zoom_step = 1043
        self.max_user_zoom_step = 1522
        self.real_path = os.path.dirname(os.path.realpath(__file__))
        self.verbose = False


    def send_cmd(self, cmd, sleep=.5):
        output = subprocess.check_output(shlex.split(cmd))
        if self.verbose:
            print output
        time.sleep(sleep)


    def get_output(self, cmd):
        return subprocess.check_output(shlex.split(self.prefix + cmd))

    def check_if_running_adb(self, running_adb):
        self.prefix = ""
        if running_adb:
            self.prefix = self.adb
            return True
        else:
            return False

    def get_valid_focus_range(self):
        print "\nChecking for valid focus range..."
        current_focus = self.get_real_focus(True)

        self.set_real_focus(1645, True)
        max_step = self.get_real_focus(True)

        self.set_real_focus(1, True)
        min_step = self.get_real_focus(True)

        self.set_real_focus(current_focus, True)
        return [min_step, max_step]


    #waits for the buffer to get freed up before capturing image. Users don't have to worry about sleep time between shots.
    def capture_wait(self, reps=1, sleep=0, adb_state=False):
        self.check_if_running_adb(adb_state)
        for i in range(reps):
            print "\nTaking picture {count} of {total}".format(count=i+1, total=reps)
            self.send_cmd("{}lyt captureBlocking 0".format(self.prefix))
            time.sleep(sleep)

    #Takes picture, users should add sleep time in between shots.
    def take_picture(self, adb_state=False, number_of_pics=1, sleep=5.5):
        self.check_if_running_adb(adb_state)
        for i in range(number_of_pics):
            print "\nTaking picture..."
            self.send_cmd("{}lyt capture 0".format(self.prefix), sleep)

    # iso value ranges: 80-3200
    def set_iso(self, iso_value, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.set_exposure_mode('manual', adb_state)
        self.send_cmd("{prefix}model set iso {iso}".format(prefix=self.prefix, iso=iso_value), 1)

    def get_iso(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        #output = self.get_output("model get iso")
        return self.get_output("model get iso")[14:]
        #return int((re.findall(r'\-?\d+', output))[0])


    #shutter speed ranges from 0.000250 to 32
    def set_shutter_speed(self, sp_value, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.set_exposure_mode('manual', adb_state)
        print "\nSetting shutter speed to {}".format(sp_value)
        self.send_cmd("{prefix}model set shutterSpeed {sp}".format(prefix=self.prefix, sp=sp_value), 1)


    def get_shutter_speed(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        #output = self.get_output("model get shutterSpeed")
        return self.get_output("model get shutterSpeed")[14:]
        #return (re.findall(r'\-?\d+', output))[0]


    #Sets focus step
    def set_real_focus(self, amount, adb_state=False):
        self.check_if_running_adb(adb_state)
        model_value = amount / float(self.max_user_focus_step)
        self.send_cmd("{pre}model set focusPos {value}".format(pre=self.prefix, value=model_value), 2)


    #Get the current focus step directly from the focus motor.
    def get_real_focus(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        out = self.get_output("diagfsalb -q")
        if "Polling timed out" in out:
            print "\nERROR: Camera display is turned OFF\n"
            sys.exit()
        #real_focus = abs(int((re.findall(r'\-?\d+', out))[22]))
        real_step = int((re.findall(r'\-?\d+', out))[22])
        user_step = abs(real_step + 337)
        #user_focus_step = self.max_user_focus_step - (self.max_real_focus_step - real_focus)
        return user_step


    #Sets focus step
    def set_real_zoom(self, amount, adb_state=False):
        self.check_if_running_adb(adb_state)
        model_value = amount / float(self.max_user_zoom_step)
        print "SETTING TO MODEL VALUE {}".format(model_value)
        self.send_cmd("{pre}model set zoomPos {value}".format(pre=self.prefix, value=model_value), 2)


    def get_real_zoom(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        out = self.get_output("diagfsalb -q")
        if "Polling timed out" in out:
            print "\nERROR: Camera display is turned OFF\n"
            sys.exit()
        real_step = int((re.findall(r'\-?\d+', out))[18])
        user_step = abs(real_step + -479)
        return user_step

    # x ranges 1-799, y ranges 1-479
    def tap_to_autofocus(self, xcord, ycord, adb_state=False, sleep=3):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{pre}input tap {x} {y}".format(pre=self.prefix, x=xcord, y=ycord), sleep)

    #Value range -2 to +2
    def set_exposure_compensation(self, value, adb_state=False):
        self.check_if_running_adb(adb_state)
        if "EXPOSURE_MANUAL" in self.get_exposure_mode(adb_state):
            self.set_exposure_mode("program", adb_state)
        self.send_cmd("{prefix}model set ExposureCompensation {value}".format(prefix=self.prefix, value=value))

    def get_exposure_compensation(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get exposureCompensation")[14:]

    #Possible modes are: 'program','iso','shutter','manual'
    def set_exposure_mode(self, mode, adb_state=False):
        self.check_if_running_adb(adb_state)
        mode = mode.lower()
        presets = {'program': 'EXPOSURE_PROGRAM',
                   'iso': 'EXPOSURE_ISO_PRIORITY',
                   'shutter': 'EXPOSURE_SHUTTER_PRIORITY',
                   'manual': 'EXPOSURE_MANUAL'}
        exp_mode = presets[mode]
        print "\nSetting exp mode to {}".format(exp_mode)
        self.send_cmd("{prefix}model set exposureMode {preset}".format(prefix=self.prefix, preset=presets[mode]), 1)

    def get_exposure_mode(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get exposureMode")[14:]

    #Set shooting mode 'single' or 'continuous'
    def set_shooting_mode(self, mode, adb_state=False):
        self.check_if_running_adb(adb_state)
        if mode.lower() == "single":
            self.send_cmd("{}model set ShutterDriveMode 0".format(self.prefix))
        elif mode.lower() == "continuous":
            #Disable other conflicting setttings first
            self.disable_focus_bracketing(adb_state)
            self.disable_exp_bracketing(adb_state)
            self.disable_self_timer(adb_state)
            #Finally set shutter mode to continuous
            self.send_cmd("{}model set ShutterDriveMode 3".format(self.prefix))

    def get_shooting_mode(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get ShutterDriveMode")[14:]


    def enable_self_timer(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{}model set SelfTimerEnable 1".format(self.prefix))


    #Applicable values are 0 for off, 2 or 10 secs
    def set_self_timer(self, secs, adb_state=False):
        self.check_if_running_adb(adb_state)
        if secs == '0':
            self.send_cmd("{}model set SelfTimerEnable 0".format(self.prefix))
        else:
            self.set_shooting_mode('single', adb_state)
            self.send_cmd("{}model set SelfTimerEnable 1".format(self.prefix))
            self.send_cmd("{prefix}model set SelfTimerSeconds {secs}".format(prefix=self.prefix, secs=secs))

    def get_self_timer(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        if 'FALSE' in self.get_output("model get SelfTimerEnable"):
            return "Self-Timer set to OFF"
        else:
            return self.get_output("model get SelfTimerSeconds")[14:]

    def disable_self_timer(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{}model set SelfTimerEnable 0".format(self.prefix))

    #Enable exposure bracketing setting.
    def enable_exp_bracketing(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.disable_focus_bracketing(adb_state)
        self.set_shooting_mode('single', adb_state)
        self.send_cmd("{}model set ExposureBracketEnable 1".format(self.prefix))

    #Sets the stop increment for exposure bracketing setting choices are 0.3, 0.6, 1, 2
    def set_exposure_bracket_offset(self, step, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{prefix}model set ExposureBracketSize {step}".format(prefix=self.prefix, step=step))

    def set_exposure_bracket_size(self, series_count, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{prefix}model set ExposureBracketCount {series}".format(prefix=self.prefix, series=series_count))

    #Disable exposure bracketing setting.
    def disable_exp_bracketing(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{}model set ExposureBracketEnable 0".format(self.prefix))

    def get_exp_bracketing(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get ExposureBracketEnable")[14:]

    #Enable focus bracketing setting.
    def enable_focus_bracketing(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.disable_exp_bracketing(adb_state)
        self.set_shooting_mode('single', adb_state)
        self.send_cmd("{}model set FocusBracketEnable 1".format(self.prefix))

    #Sets the stop increment for exposure bracketing setting choices are 0.3, 0.6, 1, 2
    def set_focus_bracket_offset(self, step, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{prefix}model set FocusBracketSize {step}".format(prefix=self.prefix, step=step))

    def set_focus_bracket_size(self, series_count, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{prefix}model set FocusBracketCount {series}".format(prefix=self.prefix, series=series_count))

    #Disable exposure bracketing setting.
    def disable_focus_bracketing(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{}model set FocusBracketEnable 0".format(self.prefix))

    def get_focus_bracketing(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get FocusBracketEnable")[14:]

    #Applicable arguments are 'evaluative' or 'average'
    def set_metering_mode(self, value, adb_state=False):
        self.check_if_running_adb(adb_state)
        if value.lower() == "average":
            self.send_cmd("{}model set metermode 1".format(self.prefix))
        else:
            self.send_cmd("{}model set metermode 0".format(self.prefix))

    def get_metering_mode(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get metermode")[14:]

    #Switch between front curtain or back curtain modes. Applicable arguments are 'back' or 'front'
    def set_flash_sync_mode(self, mode, adb_state=False):
        self.check_if_running_adb(adb_state)
        if mode.lower() == "back":
            self.send_cmd("{}model set FlashSyncMode 1".format(self.prefix))
        else:
            self.send_cmd("{}model set FlashSyncMode 0".format(self.prefix))

    def get_flash_sync_mode(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get FlashSyncMode")[14:]

    #Set flash autofocus assist mode to "off" or "auto"
    def set_flashAF_assist(self, mode, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{pre}model set FlashAfAssistEnable {mode}".format(pre=self.prefix, mode=mode))

    def get_flashAF_assist(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get FlashAfAssistEnable")[14:]

    #Applicable values are -3.0 to +3.0
    def set_exposure_flash_compensation(self, value, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{prefix}model set ExposureFlashCompensation {value}".format(prefix=self.prefix, value=value))

    def get_exposure_flash_compensation(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get ExposureFlashCompensation")[14:]

    #Applicable args [-10 to +10]
    def set_optical_offset(self, value, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{prefix}model set BiposLambdaOffset {value}".format(prefix=self.prefix, value=value))

    #Applicable args [-10 to +10]
    def get_optical_offset(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get BiposLambdaOffset")[14:]

    #Restores optical offset to default -4
    def restore_optical_offset(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{}model set BiposLambdaOffset -4".format(self.prefix))

    def set_focus_ring_lock(self, value, adb_state=False):
        self.check_if_running_adb(adb_state)
        print "{pre}model set FocusRingLock {value}".format(pre=self.prefix, value=value)
        self.send_cmd("{pre}model set FocusRingLock {value}".format(pre=self.prefix, value=value))

    def get_focus_ring_lock(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get FocusRingLock")[14:]

    def set_zoom_ring_lock(self, value, adb_state=False):
        self.check_if_running_adb(adb_state)
        print "{pre}model set ZoomRingLock {value}".format(pre=self.prefix, value=value)
        self.send_cmd("{pre}model set ZoomRingLock {value}".format(pre=self.prefix, value=value))

    def get_zoom_ring_lock(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get ZoomRingLock")[14:]

    #Applicable states are 'on' or 'off'
    def set_ae_lock(self, state, adb_state=False):
        self.check_if_running_adb(adb_state)
        if state == "1":
            self.send_cmd("{}model set 4 1".format(self.prefix))
        elif state == "0":
            self.send_cmd("{}model set 4 0".format(self.prefix))

    def get_ae_lock(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get 4")[14:]

    #Applicable states are 'auto' or 'manual'
    def set_focus_method(self, state, adb_state=False):
        self.check_if_running_adb(adb_state)
        if state.lower() == "auto":
            self.send_cmd("{}camsettings set Camera.AfDriveMode 2".format(self.prefix))
        elif state.lower() == "manual":
            self.send_cmd("{}camsettings set Camera.AfDriveMode 0".format(self.prefix))

    def get_focus_method(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        output = self.get_output("camsettings get Camera.AfDriveMode")
        if '0' in output:
            return "AfDriveMode set to MANUAL"
        else:
            return "AfDriveMode set to AUTO"


    def set_virtual_cable(self, mode, adb_state=False):
        self.check_if_running_adb(adb_state)
        if mode == '1':
            self.send_cmd("{}camsettings set Storage.Mode.VirtualCable true".format(self.prefix), 1)
        elif mode == '0':
            self.send_cmd("{}camsettings set Storage.Mode.VirtualCable false".format(self.prefix), 1)


    def get_virtual_cable(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        output = self.get_output("camsettings get Camera.virtualCable")
        if 'TRUE' in output:
            return "Virtual Cable Mode ENABLED"
        else:
            return "Virtual Cable Mode DISABLED"


    #Allows the camera to show LiveView while being connected to computer.
    def enable_virtual_cable(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        print "\nEnabling virtual cable mode..."
        self.send_cmd("{}camsettings set Storage.Mode.VirtualCable true".format(self.prefix), .5)
        self.send_cmd("{}lyt sdcardtest endUMS".format(self.prefix), 1.5)

    #Return camerat to default state
    def disable_virtual_cable(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        print "\nDisabling virtual cable mode..."
        self.send_cmd("{}camsettings set Storage.Mode.VirtualCable false".format(self.prefix), .5)
        self.send_cmd("{}lyt sdcardtest endUMS".format(self.prefix), 1.5)

    #disables idle timeout.
    def disable_timeout(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        print "\nDisabling idle timeout...."
        self.send_cmd("{}model set InactivityTimeoutSeconds 0".format(self.prefix), .5)

    def get_timeout_value(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        output = subprocess.check_output(shlex.split("{pre}model get InactivityTimeoutSeconds".format(pre=self.prefix)))
        timeout_secs = (re.findall(r'\d+', output))[0]
        return timeout_secs

    def set_timeout(self, timeout_secs, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{pre}model set InactivityTimeoutSeconds {timeout}".format(pre=self.prefix,
                                                                                 timeout=timeout_secs), 1)
    #valid modes are: 'auto', 'tungsten', 'fluorescent', 'flash', 'daylight', 'cloudy', 'shade', 'custom'
    def set_white_balance_mode(self, mode, adb_state=False):
        self.check_if_running_adb(adb_state)
        mode = mode.lower()
        if mode == "auto":
            self.send_cmd('{}model set WhiteBalanceMode 0'.format(self.prefix))

        if mode == "custom":
            self.send_cmd('{}model set WhiteBalanceMode 2'.format(self.prefix))

        valid_modes = ['tungsten', 'fluorescent', 'flash', 'daylight', 'cloudy', 'shade']
        if mode in valid_modes:
            self.send_cmd('{}model set WhiteBalanceMode 1'.format(self.prefix))
            presets = {'tungsten': '0',
                       'fluorescent': '1',
                       'flash': '5',
                       'daylight': '2',
                       'cloudy': '3',
                       'shade': '4'}
            wb_preset = presets[mode]
            self.send_cmd("{prefix}model set whitebalancepreset {preset}".format(prefix=self.prefix, preset=wb_preset))

    def get_white_balance_mode(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        if 'WB_PRESET' in self.get_output("model get WhiteBalanceMode"):
            return self.get_output("model get WhiteBalancePreset")[14:]
        else:
            return self.get_output("model get WhiteBalanceMode")[14:]

    def send_touch_event(self, xcoord, ycoord, sleep, repeat, adb_state=False):
        self.check_if_running_adb(adb_state)
        for i in range(repeat):
            self.send_cmd('{pre}input tap {x} {y}'.format(pre=self.prefix, x=xcoord, y=ycoord))
            time.sleep(sleep)

    def send_swipe_event(self, direction, sleep, repeat, adb_state=False):
        self.check_if_running_adb(adb_state)
        dir_list = []
        if direction == "right":
            dir_list = [200, 200, 1000, 200]
        elif direction == "left":
            dir_list = [650, 200, 0, 200]
        elif direction == "up":
            dir_list = [400, 470, 400, 15]
        elif direction == "down":
            dir_list = [400, 100, 400, 555]
        for i in range(repeat):
            self.send_cmd('{pre}input swipe {x1} {y1} {x2} {y2}'.format(pre=self.prefix, x1=dir_list[0], y1=dir_list[1],
                                                                        x2=dir_list[2], y2=dir_list[3]))
            time.sleep(sleep)

    def set_depthAssist_mode(self, mode, adb_state=False):
        self.check_if_running_adb(adb_state)
        if mode == '1':
            if "DEPTH_ASSIST_OFF" in self.get_depthAssist_mode(adb_state):
                self.send_cmd("{}sendevent /dev/input/event2 1 555 1".format(self.prefix), 0)
                self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
                self.send_cmd("{}sendevent /dev/input/event2 1 554 1".format(self.prefix), 0)
                self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
                self.send_cmd("{}sendevent /dev/input/event2 1 554 0".format(self.prefix), 0)
                self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
                self.send_cmd("{}sendevent /dev/input/event2 1 555 0".format(self.prefix), 0)
                self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
                time.sleep(1)
        elif mode == '0':
            self.send_cmd("{}model set DepthAssistMode 0".format(self.prefix))

    def get_depthAssist_mode(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        return self.get_output("model get DepthAssistMode")[14:]

    def delete_all_pictures(self, adb_state=False):
        if self.check_if_running_adb(adb_state):
            self.init()
        self.send_cmd("{}dcf --delete -i all".format(self.prefix), 5)
        self.remount_dcf(True)

    def remount_dcf(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        print "Remount DCF...\n"
        self.send_cmd("{}lyt unmountDcf 1".format(self.prefix))
        self.send_cmd("{}lyt mountDcf /storage/sdcard1/DCIM 1".format(self.prefix), 2)

    def half_press_shutter(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        self.send_cmd("{}sendevent /dev/input/event2 1 528 1".format(self.prefix), 0)
        self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
        #time.sleep(1)
        self.send_cmd("{}sendevent /dev/input/event2 1 528 0".format(self.prefix), 0)
        self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
        time.sleep(1)


    def disable_bracketing_modes(self):
        self.disable_exp_bracketing()
        self.disable_focus_bracketing()
        self.disable_self_timer()


    def get_battery_level(self):
        output = subprocess.check_output(["batgauge"])
        for line in output.splitlines():
            if "percent charged" in line:
                batt_level = int((re.findall(r'\-?\d+', line))[0])
                return batt_level


    def init(self, disable_inactivity_timeout=True):
        self.enable_virtual_cable(True)
        self.login_as_root_if_necessary()
        if disable_inactivity_timeout:
            self.disable_timeout(True)

    def get_serial_no(self):
        output = subprocess.check_output(['adb', 'shell', 'cat', 'unitdata/unit_info.json'])
        unit_info = json.loads(output)
        return unit_info['camera']['serialNumber'].strip()

    def convert_zoom_x_to_step(self, zoom):
        zoom_pos_x = {'1': '1',
                      '2': '623',
                      '3': '903',
                      '4': '1088',
                      '5': '1223',
                      '6': '1338',
                      '7': '1443',
                      '8': '1521'}
        return int(zoom_pos_x[str(zoom)])


    def pull_cal_data(self, args):
        self.init()
        camera_sn = self.get_serial_no()
        dest_path = os.path.join(args.path, "cameras", camera_sn)
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        print "\nPulling call data...\n"
        print "path: " + "adb pull unitdata {}".format(os.path.join(args.path, "cameras", camera_sn))
        self.send_cmd("adb pull unitdata {}".format(os.path.join(args.path, "cameras", camera_sn)))
        print "\nCal data transfer completed\n"
        self.set_timeout(self.get_entry_from_json("sleep_timeout"), True)
        self.disable_virtual_cable(True)


    def handler(self, path, signal, param):
        print "Cancelling import on {}".format(path)
        self.remove_file(path)
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

    def get_number_of_dup_folders(self, path, folderName):
        folder_counter = 0
        try:
            file_list = os.listdir(path)
            for single_file in file_list:
                if os.path.isdir(os.path.join(path, single_file)) and single_file.startswith(folderName):
                    folder_counter += 1
            return folder_counter
        except OSError:
            return folder_counter

    def download_images(self, args):
        self.init()
        if not os.path.exists(args.path):
            os.makedirs(args.path)
        DATE = time.strftime("%b%d")
        tool_name = self.get_entry_from_json("tool_name").replace(" ", "")
        end_directory_path = os.path.join(args.path, "{tool_name}_{date}".format(tool_name=tool_name, date=DATE))
        folder_count = self.get_number_of_dup_folders(args.path, os.path.basename(end_directory_path))
        if folder_count > 0:
            end_directory_path += "_({})".format(folder_count+1)

        print "\nWaiting for DCF...\n"
        #Give it a sleep in case pictures are still being written to the card
        time.sleep(5)
        if self.higher_dcf_path_exists():
            dcf_path = 'storage/sdcard1/DCIM/200PHOTO/'
        else:
            dcf_path = 'storage/sdcard1/DCIM/100PHOTO/'
        dcf_list = subprocess.check_output(['adb', 'shell', 'ls', '{}'.format(dcf_path)]).split()

        #If user specified to download all then do that
        if args.dwl_all:
            for photo in reversed(dcf_list):
                if photo.endswith("LFR"):
                    final_path = os.path.join(end_directory_path, photo)
                    base_path = "adb pull {dcf}/{pic_id} ".format(dcf=dcf_path, pic_id=photo)
                    pull_cmd = shlex.split(base_path)
                    pull_cmd.append(final_path)
                    if sys.platform == 'win32':
                        [(item.replace("\\", "\\\\")) for item in pull_cmd]
                    print "downloading {photo} to {path}".format(photo=photo, path=os.path.dirname(final_path))
                    try:
                        #Handle Ctr + Z interrupt
                        try:
                            signal.signal(signal.SIGTSTP, functools.partial(self.handler, final_path))
                        #Windows does not recognize SIGTSP and will throw an AtributeError
                        except AttributeError:
                            pass
                        #Execute image download
                        out = subprocess.Popen(pull_cmd, stdout=subprocess.PIPE)
                        #Make this call blocking
                        out.communicate()[0]

                    #Handle Ctr + C interrupt
                    except KeyboardInterrupt:
                        self.remove_file(final_path)
                        print "Cancelling import on {}".format(final_path)
                        try:
                            sys.exit(0)
                        except SystemExit:
                            os._exit(0)
            time.sleep(1)
            print "\nDONE!\n"

        #Otherwise download images from the latest script ran
        else:
            pictures_taken = self.get_entry_from_json("total_captures")
            LFR_counter = 0
            for photo in reversed(dcf_list):
                if (LFR_counter + 1) > pictures_taken:
                    time.sleep(1)
                    print "\nDONE!\n"
                    break
                if photo.endswith("LFR"):
                    LFR_counter += 1
                    final_path = os.path.join(end_directory_path, photo)
                    base_path = "adb pull {dcf}/{pic_id} ".format(dcf=dcf_path, pic_id=photo)
                    pull_cmd = shlex.split(base_path)
                    pull_cmd.append(final_path)
                    if sys.platform == 'win32':
                        [(item.replace("\\", "\\\\")) for item in pull_cmd]

                    print "downloading {photo} to {path}".format(photo=photo, path=os.path.dirname(final_path))
                    try:
                        #Handle Ctr + Z interrupt
                        try:
                            signal.signal(signal.SIGTSTP, functools.partial(self.handler, final_path))
                        #Windows does not recognize SIGTSP and will throw an AtributeError
                        except AttributeError:
                            pass
                        out = subprocess.Popen(pull_cmd, stdout=subprocess.PIPE)
                        #Make this call blocking
                        out.communicate()[0]

                    #Handle Ctr + C interrupt
                    except KeyboardInterrupt:
                        self.remove_file(final_path)
                        print "Cancelling import on {}".format(final_path)
                        try:
                            sys.exit(0)
                        except SystemExit:
                            os._exit(0)

        self.set_timeout(self.get_entry_from_json("sleep_timeout"), True)
        self.disable_virtual_cable(True)


    def remove_file(self, path):
        try:
            os.remove(path)
        except OSError:
            print "Invalid Path"


    def get_entry_from_json(self, key):
        with open(os.path.join(self.real_path, "args.json"), 'r') as args_json:
            capture_args = json.loads(args_json.read())
            entry = capture_args[key]
            args_json.close()
            return entry

    def get_pictures_remaining(self, adb_state=False):
        self.check_if_running_adb(adb_state)
        out = self.get_output("state get shotsremaining")
        return int((re.findall(r'\d+', out))[0])

    def is_adb_running(self):
        output = subprocess.check_output(["adb", "devices"])
        #If the output contains digits, it found the serial number which means adb is running.
        if any(char.isdigit() for char in output):
            return True
        else:
            return False

    def handle_if_adb_not_running(self):
        if not self.is_adb_running():
            print "\nERROR: ADB NOT RUNNING. Please check the following and try again."
            print "\n-Make sure camera is properly connected via USB"
            print "\n-Make sure ADB is activated. To activate ADB press and hold 'AEL' + 'Lytro' Button while " \
                  "booting camera\n"
            sys.exit()

    def login_as_root_if_necessary(self):
        if not self.running_as_root():
            print "\nLogging as root"
            self.send_cmd("adb root")
            raw_input("\nDisconnect and reconnect USB cable. Press ENTER to continue")
            time.sleep(2)

    def running_as_root(self):
        uid_output = subprocess.check_output(["adb", "shell", "id", "-u"])
        if "uid=0" in uid_output:
            return True
        else:
            return False


    def higher_dcf_path_exists(self):
        output = subprocess.check_output(["adb", "shell", "storage/sdcard1/DCIM/200PHOTO/"])
        if "Is a directory" in output:
            return True
        else:
            return False

    def press_power(self, repeat=1, sleep=1, adb_state=False):
        self.check_if_running_adb(adb_state)
        for i in range(repeat):
            self.send_cmd("{}sendevent /dev/input/event1 1 356 1".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event1 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event1 1 356 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event1 0 0 0".format(self.prefix), 0)
            time.sleep(sleep)


    def press_shutter(self, repeat=1, sleep=1, adb_state=False):
        self.check_if_running_adb(adb_state)
        for i in range(repeat):
            self.send_cmd("{}sendevent /dev/input/event2 1 528 1".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 766 1".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 766 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 528 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            time.sleep(sleep)

    def press_half_shutter(self, repeat=1, sleep=1, adb_state=False):
        self.check_if_running_adb(adb_state)
        for i in range(repeat):
            self.send_cmd("{}sendevent /dev/input/event2 1 528 1".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 528 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            time.sleep(sleep)

    def press_lytro(self, repeat=1, sleep=1, adb_state=False):
        self.check_if_running_adb(adb_state)
        for i in range(repeat):
            self.send_cmd("{}sendevent /dev/input/event2 1 555 1".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 554 1".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 554 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 555 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            time.sleep(sleep)

    def press_ael(self, repeat=1, sleep=1, adb_state=False):
        self.check_if_running_adb(adb_state)
        for i in range(repeat):
            self.send_cmd("{}sendevent /dev/input/event2 1 556 1".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 556 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            time.sleep(sleep)


    def press_fn(self, repeat=1, sleep=1, adb_state=False):
        self.check_if_running_adb(adb_state)
        for i in range(repeat):
            self.send_cmd("{}sendevent /dev/input/event2 1 557 1".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 557 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            time.sleep(sleep)

    def press_hyperfocal(self, repeat=1, sleep=1, adb_state=False):
        self.check_if_running_adb(adb_state)
        for i in range(repeat):
            self.send_cmd("{}sendevent /dev/input/event2 1 558 1".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 558 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            time.sleep(sleep)

    def press_af(self, repeat=1, sleep=1, adb_state=False):
        self.check_if_running_adb(adb_state)
        for i in range(repeat):
            self.send_cmd("{}sendevent /dev/input/event2 1 559 1".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 1 559 0".format(self.prefix), 0)
            self.send_cmd("{}sendevent /dev/input/event2 0 0 0".format(self.prefix), 0)
            time.sleep(sleep)
