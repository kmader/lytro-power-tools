# -*- coding: utf-8 -*-
"""Lytro Power Tools - camera package - command executor"""

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
import shlex
import time
import json
import sys
from datetime import datetime

from lytro.ui.widgets import Label, Button
from lytro.ui.gui import Gui
import camerabin


class Execution:

    def __init__(self):
        self.args = None
        self.cam = camerabin.CameraControls()
        self.show_timer = False
        self.start_time = 0


    def send_command(self, cmd):
        out = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
        #makes previous call blocking
        out.communicate()[0]

    def get_arguments_from_json(self):
        with open('storage/sdcard1/args.json', "r") as json_file:
            args = json.loads(json_file.read())
            json_file.close()
        return args

    def perform_captures(self):
        self.cam.disable_bracketing_modes()
        reps = self.args['pictures']
        add_sleep = self.args['interval']

        for i in range(reps):
            if self.low_battery():
                self.exit_script_gracefully()
            self.cam.capture_wait()
            #If its last iteration ignore sleep
            if i == reps - 1:
                time.sleep(0)
            else:
                time.sleep(add_sleep)

    def perform_cont_captures(self):
        self.cam.disable_bracketing_modes()
        reps = self.args['reps']
        cap_size = self.args['capture_size']
        add_sleep = self.args['cont_interval']

        for i in range(reps):
            if self.low_battery():
                self.exit_script_gracefully()
            #capture remaining shots
            self.cam.take_picture(False, cap_size-1, .5)
            self.cam.capture_wait()
            #Wait until buffer frees up before taking next picture

            #If it's the last iteration, then the interval is ignored
            if i == reps - 1:
                time.sleep(0)
            else:
                #Additional sleep time input by user.
                time.sleep(add_sleep)

    def perform_exp_bracketing(self):
        self.cam.enable_exp_bracketing()
        self.cam.set_exposure_bracket_offset(self.args['offset'])
        self.cam.set_exposure_bracket_size(self.args['size'])
        reps = self.args['reps']
        add_sleep = self.args['bracket_interval']

        for i in range(reps):
            if self.low_battery():
                self.exit_script_gracefully()
            self.cam.capture_wait()
            #If it's the last iteration, then the interval is ignored
            if i == reps - 1:
                time.sleep(0)
            else:
                time.sleep(add_sleep)

    def perform_focus_bracketing(self):
        self.cam.enable_focus_bracketing()
        self.cam.set_focus_bracket_offset(self.args['offset'])
        self.cam.set_focus_bracket_size(self.args['size'])
        reps = self.args['reps']
        add_sleep = self.args['bracket_interval']

        for i in range(reps):
            if self.low_battery():
                self.exit_script_gracefully()
            self.cam.capture_wait()
            #If it's the last iteration, then the interval is ignored
            if i == reps - 1:
                time.sleep(0)
            else:
                time.sleep(add_sleep)

    def perform_focus_sweep(self):
        self.cam.disable_bracketing_modes()
        add_sleep = self.args['interval']
        lowest_step = self.args['focus_range'][0]
        highest_step = self.args['focus_range'][1]
        median_step = round((highest_step - lowest_step) / (self.args['pictures'] - 1))
        picture_count = self.args['pictures']

        for i in range(picture_count):
            if self.low_battery():
                self.exit_script_gracefully()
            #the first picture is taken at MIN focus step
            if i == 0:
                print "Setting FOCUS STEP to " + str(lowest_step)
                self.cam.set_real_focus(lowest_step)
                self.cam.capture_wait()
            #The last picture is taken at MAX focus step
            elif i == (picture_count - 1):
                print "Setting FOCUS STEP to " + str(highest_step)
                self.cam.set_real_focus(highest_step)
                self.cam.capture_wait()
            else:
                increment = median_step * i
                focus_step = lowest_step + increment
                print "Setting FOCUS STEP to " + str(focus_step)
                self.cam.set_real_focus(focus_step)
                self.cam.capture_wait()

            if i == picture_count - 1:
                time.sleep(0)
            else:
                time.sleep(add_sleep)


    def perform_zoom_sweep(self):
        self.cam.disable_bracketing_modes()
        add_sleep = self.args['interval']
        lowest_step = self.args['zoom_range'][0]
        highest_step = self.args['zoom_range'][1]
        median_step = round((highest_step - lowest_step) / (self.args['pictures'] - 1))
        picture_count = self.args['pictures']

        for i in range(picture_count):
            if self.low_battery():
                self.exit_script_gracefully()
            #the first picture is taken at MIN zoom step
            if i == 0:
                print "Setting ZOOM STEP to " + str(lowest_step)
                self.cam.set_real_zoom(lowest_step)
                self.cam.capture_wait()
            #The last picture is taken at MAX zoom step
            elif i == (picture_count - 1):
                print "Setting ZOOM STEP to " + str(highest_step)
                self.cam.set_real_zoom(highest_step)
                self.cam.capture_wait()
            else:
                increment = median_step * i
                zoom_step = lowest_step + increment
                print "Setting ZOOM STEP to " + str(zoom_step)
                self.cam.set_real_zoom(zoom_step)
                self.cam.capture_wait()

            if i == picture_count - 1:
                time.sleep(0)
            else:
                time.sleep(add_sleep)


    def launch_start_screen(self):

        self.args = self.get_arguments_from_json()

        self.cam.half_press_shutter()

        g = Gui()

        def startClickHandler(button):
            button.gui.stop()
            g.mainloop()
            time.sleep(3)
            g.disableInputCapture()
            self.cam.disable_timeout()

        def quitClickHandler(button):
            button.gui.stop()
            g.mainloop()
            self.display_tip_frame()
            #Restore inactivity timeout
            self.cam.set_timeout(self.args['sleep_timeout'])
            self.cam.disable_virtual_cable()
            sys.exit()

        tool_name = str(self.args['tool_name'])
        margin = int(self.args['label_margin'])

        g.addWidget(Label(margin, 65, 80, 50, tool_name, 0xFFFFFFFF))
        g.addWidget(Button(150, 250, 50, 105, "START", startClickHandler, 0xFF00FF00))
        g.addWidget(Button(350, 250, 50, 105, "QUIT", quitClickHandler, 0xFFFF0000))

        # Remove everything in the touch queue that has been buffered while we're waiting.
        touch = True
        while touch:
            touch = g.layer.getTouchData(False)
        g.mainloop()

        self.cam.half_press_shutter()

        g.disableInputCapture()

        #EXECUTE SCRIPT
        self.start_time = datetime.now().replace(microsecond=0)
        eval(self.args['func'])

        #ON SCRIPT FINISHED
        self.record_script_duration()
        self.launch_exit_screen()

    def display_tip_frame(self):
        g = Gui()
        g.addWidget(Label(250, 50, 45, 50, "TIP", 0xFFFFFF00))
        g.addWidget(Label(18, 140, 33, 50, "You can always relaunch script menu by", 0xFFFFFFFF))
        g.addWidget(Label(18, 220, 33, 50, "pressing and holding Fn + AF Buttons", 0xFFFFFFFF))
        g.draw()
        time.sleep(5)
        g.layer.setCaptureInput(False)
        g.layer.setVisible(False)
        g.layer.relinquishOwnership()

        g.disableInputCapture()
        self.clean_up()


    def display_low_battery_frame(self):
        g = Gui()
        g.addWidget(Label(190, 70, 45, 50, "LOW BATTERY", 0xFFFFFF00))
        g.addWidget(Label(100, 150, 50, 50, "Terminating script", 0xFFFFFFFF))
        g.draw()
        time.sleep(5)
        g.layer.setCaptureInput(False)
        g.layer.setVisible(False)
        g.layer.relinquishOwnership()

        g.disableInputCapture()

    def record_script_duration(self):
        script_duration = datetime.now().replace(microsecond=0) - self.start_time
        with open("storage/sdcard1/args.json", mode='w') as args_json:
            self.args['script_duration'] = str(script_duration)
            args_json.write(json.dumps(self.args))


    def launch_exit_screen(self):

        g = Gui()

        def ackClickHandler(button):
            button.gui.stop()
            g.mainloop()
            time.sleep(3)
            g.disableInputCapture()
            self.clean_up()

        g.addWidget(Label(135, 65, 90, 50, "COMPLETE", 0xFFFFFFFF))
        g.addWidget(Button(250, 270, 50, 105, "OK", ackClickHandler, 0xFF00FF00))
        g.mainloop()

        g.disableInputCapture()


    def low_battery(self):
        if self.cam.get_battery_level() < 3:
            return True
        else:
            return False


    def clean_up(self):
        script_running = self.args['tool_name']
        if script_running == 'Focus Bracketing':
            self.cam.disable_exp_bracketing()
        elif script_running == 'Exp Bracketing':
            self.cam.disable_focus_bracketing()
        self.cam.set_timeout(self.args['sleep_timeout'])
        self.cam.disable_virtual_cable()


    def exit_script_gracefully(self):
        self.display_low_battery_frame()
        self.clean_up()
        sys.exit()


if __name__ == "__main__":

    Execution().launch_start_screen()
