# -*- coding: utf-8 -*-
"""Lytro Power Tools - recipe package - common functions to make recipes"""

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

import collections
import os
import re
import tempfile
import numpy as np

from functools import partial
from collections import deque

from lpt.lfp.tnt import Tnt
from lpt.lfp.tool import Tool
from lpt.recipe import config
from lpt.recipe.params import Params
from lpt.recipe.recipe import Recipe
from lpt.utils.argutils import ArgUtils
from lpt.utils.calcutils import CalcUtils
from lpt.utils.jsonutils import JsonUtils
from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.utils.utils import Utils

argutils = ArgUtils()
utils = Utils()
jsonutils = JsonUtils()
msgutils = MsgUtils()
params = Params()
tool = Tool()
calcutils = CalcUtils()

od = collections.OrderedDict
any_ = partial(utils.any_, iter_=False)
all_ = partial(utils.all_, iter_=False)


class Make(object):
    """various functions for making recipe files"""

    _version = config.db['recipe_version']
    _view_pattern = re.compile('view[A-Za-z]+([0-9]+)?')
    _auto_ease = config.db['auto_ease']
    _auto_shape = config.db['auto_shape']
    _auto_steps = config.db['auto_steps']
    _auto_buffer = config.auto_buffer
    _auto_duration = config.db['auto_duration']

    print_help = object

    def _set_print_help(self, args):
        """sets `argparse` help menu for current command"""

        self.print_help = args.print_help
        tool.set_print_help(args.print_help)
        utils.set_print_help(args.print_help)
        argutils.set_print_help(args.print_help)
        calcutils.set_print_help(args.print_help)
        params.set_global_help(args.print_help)

    @staticmethod
    def _anim_param(param):
        """converts view property name to animation property name"""

        a = 'Animation'
        return param if param.endswith(a) else param + a

    @staticmethod
    def _apt_params(pattern=None, lst=(), bool_=True, **kwargs):
        """filters through parameters for applicable key/value pairs"""

        if pattern:
            def is_apt(x): return re.match(pattern, x)
        elif lst:
            def is_apt(x): return x in lst
        else:
            def is_apt(x): return x

        items = kwargs.items()
        return {k: v for k, v in items if is_apt(k) and any_(v, bool_=bool_)}

    @staticmethod
    def _anim_props(times=(), values=(), dt0=(), dt1=(), dv0=(), dv1=(),
                    initial_value=None):
        """flattens provided animation properties (removes non-values)"""

        return utils.flatten({
            'times': times,
            'values': values,
            'initial_value': initial_value,
            'dt0': dt0,
            'dt1': dt1,
            'dv0': dv0,
            'dv1': dv1}, iter_=False)

    def _assert_points(self, points, param):
        """checks if a animation line contains enough data for a given task

        :raise: `ToolError` if no or bad amount of animation data points found
        """

        e = param + ": missing animation data"
        assert points, ToolError(e, self.print_help)

    def _assert_t0_lt_t1(self, t0, t1, param=''):
        """checks if t0 value is less than t1 value

        :raise: `ToolError` if t0 greater than t1
        """

        param = "{}: ".format(param) if param else ""

        if any_(t1):
            t0 = t0 if any_(t0) else self._auto_buffer
            e = param + "t0/t1 duration is less than .5 seconds; "
            e += "t0={}, t1={}".format(t0, t1)
            assert t0 + .5 < t1, ToolError(e, self.print_help)

    @staticmethod
    def _auto_props(t0=None, v0=None, t1=None, v1=None):
        """flattens provided auto animation properties (removes non-values)"""

        props = {'t0': t0,
                 't1': t1,
                 'v0': v0,
                 'v1': v1}
        return utils.flatten(props)

    @staticmethod
    def _ease_props(auto_ease=None, auto_shape=None, auto_steps=None):
        """flattens provided easing properties (removes non-values)"""

        props = {'ease': auto_ease,
                 'shape': auto_shape,
                 'steps': auto_steps}
        return utils.flatten(props)

    @staticmethod
    def _recipe(recipe):
        """instantiates a Recipe instance if not already a Recipe object"""

        return recipe if isinstance(recipe, Recipe) else Recipe(recipe)

    @staticmethod
    def _scale_props(time, value):
        """flattens provided scaling properties (removes non-values)"""

        return utils.flatten({'scale_time': time, 'scale_value': value})

    def anim_auto(self, recipe, param, t0=None, v0=None, t1=None, v1=None,
                  ease=_auto_ease, shape=_auto_shape, steps=_auto_steps):
        """generates automatic animation values

        :param recipe: `str`,/<Recipe> recipe file or recipe.Recipe instance
        :param param: `str`, animation parameter to perform function on
        :param t0: `int`/`float`, start time, in seconds
        :param v0: `int`/`float`, start value
        :param t1: `int`/`float`, end time, in seconds
        :param v1: `int`/`float`, end value
        :param ease: `str`, easing acceleration to apply
        :param shape: `str`, easing shape to apply
        :param steps: `int`, easing steps to apply
        :raise: `ToolError` if --v1 not provided
        """

        e = "argument --v1 is required"
        assert any_(v1), ToolError(e, self.print_help)

        recipe = self._recipe(recipe)
        cls = recipe[param]

        initial_value = cls.initial_value.store
        view_value = cls.view.store
        default_value = cls.meta.default_value

        hand_time = None
        hand_value = None
        hand_dt1 = None
        hand_dv1 = None

        values = cls.values.store
        times = cls.times.store
        dt1 = cls.handle_pairs.dt1.store
        dv1 = cls.handle_pairs.dv1.store

        if any_(values):
            hand_value = values.pop()
        if any_(times):
            hand_time = times.pop()
        if any_(dt1):
            hand_dt1 = dt1.pop()
        if any_(dv1):
            hand_dv1 = dv1.pop()

        t0, v0 = self.append(
            param,
            time=hand_time,
            value=hand_value,
            initial_value=initial_value,
            default_value=default_value,
            view=view_value,
            dt1=hand_dt1,
            dv1=hand_dv1,
            t0=t0,
            v0=v0)

        if not any_(t1):
            t1 = t0 + self._auto_duration

        while steps % 3:
            steps += 1

        self.auto_keyframes(
            recipe, param,
            t0=t0, v0=v0, t1=t1, v1=v1,
            ease=ease,
            shape=shape,
            steps=steps)

    def anim_manual(self, recipe, param, **anim_kwargs):
        """manual animation handler

        :param recipe: `str`,/<Recipe> recipe file or `recipe.Recipe` instance
        :param param: `str`, animation parameter to perform function on
        :param anim_kwargs: animation keyword args passed to `self.anim_props`:
                            times, values, dt0, dt1, dv0, dv1, initial_value,
                            handle_pairs
        """

        recipe = self._recipe(recipe)
        props = self.anim_props(**anim_kwargs)
        cls = recipe[param]
        cls(props)

    def anim_params(self, **kwargs):
        """parses through kwargs for, and formats, animation parameters

        :param kwargs: keyword arguments passed to `self._apt_params`
        :return: formatted animation parameters dict
        """

        pattern = self._view_pattern
        view = self._apt_params(pattern=pattern, bool_=False, **kwargs)

        return [self._anim_param(x) for x in view]

    def anim_props(self, values=(), times=(), dt0=(), dt1=(), dv0=(),
                   dv1=(), initial_value=None, handle_pairs=()):
        """formats a single animation parameter dictionary

        :param dt0: `list`, preceding time handle pair values
        :param dt1: `list`, succeeding time handle pair values
        :param dv0: `list`, preceding value handle pair values
        :param dv1: `list`, succeeding value handle pair values
        :param values: `list`, animation parameter values
        :param times: `list`, animation times to apply values
        :param handle_pairs: `list`, time/value handle pairs
        :param initial_value: `int`/`float`, initial value of animation
        :return: formatted animation view parameter
        """

        pairs = handle_pairs or self.handle_pairs(dt0, dt1, dv0, dv1)
        properties = {
            'times': times,
            'values': values,
            'handlePairs': pairs,
            'initialValue': initial_value}

        return utils.flatten(properties, bool_=False, iter_=False)

    def anim_scale(self, recipe, param, scale_time=None, scale_value=None):
        """generates scaled values for provided time and/or value

        :param recipe: `str`,/<Recipe> recipe file or recipe.Recipe instance
        :param param: `str`, animation parameter to perform function on
        :param scale_time: `tuple`, new start/end times
        :param scale_value: `tuple`, new start/end values
        """

        recipe = self._recipe(recipe)
        cls = recipe[param]
        points = cls.points

        self._assert_points(points, param)
        times, values = zip(*points)

        if scale_time:
            a, b = scale_time
            times = calcutils.scale(times, float(a), float(b))

        if scale_value:
            a, b = scale_value
            values = calcutils.scale(values, float(a), float(b))

        points = zip(times, values)
        cls.times.delete()
        cls.values.delete()
        cls.handle_pairs.delete()
        self.keyframe_calc(recipe, param, points)

    def append(self, param, time=None, value=None, dt1=None, dv1=None, t0=None,
               v0=None, view=None, initial_value=None, default_value=None):
        """given available parameters, determine the next best value to append

        :param param: `str`, animation parameter to perform function on
        :param time: `float`, moment in time to apply value
        :param value: `float`/`int`, parameter value to apply
        :param dt1: `list`, succeeding time handle pair values
        :param dv1: `list`, succeeding value handle pair values
        :param t0: `int`/`float`, start time, in seconds
        :param v0: `int`/`float`, start value
        :param view: the recipe's view parameter value for the corresponding
                     animation parameter
        :param initial_value: the starting value of the animation parameter
        :param default_value: the default value of the parameter defined in
                              the LFP schema
        :return: best guessed t0/v0 values
        :raise: `ToolError` if no appropriate start value found
        """

        if not any_(t0):

            t0 = self._auto_buffer

            if any_(dt1) and any_(time):
                t0 += time - dt1
            elif any_(time):
                t0 += time

        if not any_(v0):

            if any_(dv1) and any_(value):
                v0 = value - dv1
            elif any_(value):
                v0 = value
            elif any_(initial_value):
                v0 = initial_value
            elif any_(view):
                v0 = view
            elif any_(default_value):
                v0 = default_value
            else:
                e = param + ": no starting value found; specify --v0"
                ToolError(e, self.print_help)

        return t0, v0

    def auto_keyframes(self, recipe, param, t0, v0, t1, v1, ease=_auto_ease,
                       shape=_auto_shape, steps=_auto_steps):
        """auto generate recipe keyframe data

        :param recipe: `str`,/<Recipe> recipe file or recipe.Recipe instance
        :param param: `str`, animation parameter to perform function on
        :param t0: `int`/`float`, start time, in seconds
        :param v0: `int`/`float`, start value
        :param t1: `int`/`float`, end time, in seconds
        :param v1: `int`/`float`, end value
        :param ease: `str`, easing acceleration to apply
        :param shape: `str`, easing shape to apply
        :param steps: `int`, easing steps to apply
        """

        recipe = self._recipe(recipe)
        cls = recipe[param]
        anim = cls.meta.animation
        x0 = anim.times.type_t0(t0)
        y0 = anim.values.type_v0(v0)
        x1 = anim.times.type_t1(t1)
        y1 = anim.values.type_v1(v1)

        func = argutils.ease_function(ease, shape)
        x_line, y_line = calcutils.tween(num=steps, func=func)

        x_line = calcutils.normalize(x_line, a=x0, b=x1)
        y_line = calcutils.normalize(y_line, a=y0, b=y1)

        points = zip(x_line, y_line)
        self.keyframe_calc(recipe, param, points)

    def control_points(self, x_lst, y_lst):
        """formats controlPoint objects for recipe

        :param x_lst: `iter`, x control point list
        :param y_lst: `iter`, y control point list
        :return: properly formatted value
        """

        argutils.lens_match(x=x_lst, y=y_lst)
        zipped = zip(x_lst, y_lst)
        sets = [self.control_points_obj(*set_) for set_ in zipped]
        return sets

    @staticmethod
    def control_points_obj(x, y):
        """formats x/y coordinates of a control point

        :param x: `float`, control point x value
        :param y: `float`, control point y value
        """

        points = argutils.all_or_none(x=x, y=y)
        return points

    def crop(self, angle=None, top=None, left=None, bottom=None, right=None):
        """formats crop parameters

        :param angle: `float`, angle at which to crop an image at
        :param top: `float`, crop coordinate from top
        :param left: `float`, crop coordinate from left
        :param bottom: `float`, crop coordinate from bottom
        :param right: `float`, crop coordinate from right
        :return: formatted crop parameters dict
        """

        apt_params = self._apt_params(
            angle=angle,
            top=top,
            left=left,
            bottom=bottom,
            right=right)

        return apt_params

    def get_lfp_recipe(self, lfp_in):
        """generates a recipe class from a given LFP

        :param lfp_in: `str`, path to LFP to generate recipe from
        :return: instantiated recipe class
        """

        recipe_out = tempfile.NamedTemporaryFile().name
        Tnt().lfp_in(lfp_in).recipe_out(recipe_out).execute()
        recipe = Recipe(recipe_out, self.print_help)
        return recipe

    def handle_pairs(self, dt0=(), dt1=(), dv0=(), dv1=()):
        """formats a list of time/value handle pairs

        :param dt0: `list`, preceding time handle pair values
        :param dt1: `list`, succeeding time handle pair values
        :param dv0: `list`, preceding value handle pair values
        :param dv1: `list`, succeeding value handle pair values
        :return:
        """

        argutils.lens_match(dt0=dt0, dt1=dt1, dv0=dv0, dv1=dv1)
        zipped = zip(dt0, dt1, dv0, dv1)
        sets = [self.handle_pairs_obj(*set_) for set_ in zipped]
        return sets

    @staticmethod
    def handle_pairs_obj(dt0, dt1, dv0, dv1):
        """formats a single time/value handle pair

        :param dt0: `list`, preceding time handle pair values
        :param dt1: `list`, succeeding time handle pair values
        :param dv0: `list`, preceding value handle pair values
        :param dv1: `list`, succeeding value handle pair values
        :return: formatted handle pair dict
        """

        pairs = argutils.all_or_none(dt0=dt0, dt1=dt1, dv0=dv0, dv1=dv1)
        return pairs

    def keyframe_adjust(self, recipe, param, index, **props):
        """modify a recipe animation parameter by keyframe index

        :param recipe: `str`/`Recipe` recipe file or `recipe.Recipe` instance
        :param param: `str`, animation parameter to perform function on
        :param index: `int`, keyframe index to perform function on
        :param props: keyword arguments -- times, values, handle_pairs,
                      dt0, dt1, dv0, dv1 -- passed to `self.keyframe_props`
                      to generate a formatted adjustment
        """

        recipe = self._recipe(recipe)
        argutils.assert_len(props)
        props = {k: v[0] for k, v in props.items()}
        props = self.keyframe_props(**props)
        keyframe = recipe[param].keyframes[index]
        keyframe(props)

    def keyframe_calc(self, recipe, param, points=()):
        """using animation x, y coordinates, generate animation keyframes

        :param recipe: `str`,/<Recipe> recipe file or recipe.Recipe instance
        :param param: `str`, animation parameter to perform function on
        :param points: `list`, x/y coordinates (tuples) of an animation line
        """

        points = deque(points)
        recipe = self._recipe(recipe)
        param = self._anim_param(param)
        cls = recipe[param]
        keyframes = []

        while len(points) % 3:
            points.append(points[-1])

        while points:
            keyframe = [points.popleft() for _ in xrange(3)]
            keyframes.append(keyframe)

        for keyframe in keyframes:

            [(dt0, dv0), (time, value), (dt1, dv1)] = keyframe

            cls.times(time)
            cls.values(value)
            cls.dt0(time - dt0)
            cls.dt1(time - dt1)
            cls.dv0(value - dv0)
            cls.dv1(value - dv1)

    def keyframe_destroy(self, recipe, param, index):
        """destroy an animation keyframe by index

        :param recipe: `str`,/<Recipe> recipe file or recipe.Recipe instance
        :param param: `str`, animation parameter to perform function on
        :param index: `int`, keyframe index to perform function on
        """

        recipe = self._recipe(recipe)
        recipe[param].keyframes[index].delete()

    def info_points(self, recipe, param, index):
        """print out an animation keyframe by index as an x/y line

        :param recipe: `str`,/<Recipe> recipe file or recipe.Recipe instance
        :param param: `str`, animation parameter to perform function on
        :param index: `int`, keyframe index to perform function on
        """

        recipe = self._recipe(recipe)
        cls = recipe[param]

        if index == 'x':
            points = cls.x_points
        elif index == 'y':
            points = cls.y_points
        else:
            points = cls.points

        if index in ('points', 'x', 'y'):
            i = 0, None, 1
            i = slice(*i)
        else:
            i = index

        points = enumerate(points[i])

        if index in ('x', 'y'):
            out = od([(index, od([(i, z) for i, z in points]))])
        elif isinstance(i, slice):
            out = od([(i, od([('x', x), ('y', y)])) for i, (x, y) in points])
        else:
            out = [z[1] for z in points]
            out = od([('x', out[0]), ('y', out[1])])

        msgutils.dumps(out, sort_keys=False)

    def info_keyframes(self, recipe, param, index):
        """print out an animation keyframe by index

        :param recipe: `str`,/<Recipe> recipe file or recipe.Recipe instance
        :param param: `str`, animation parameter to perform function on
        :param index: `int`, keyframe index to perform function on
        """

        recipe = self._recipe(recipe)
        keyframes = recipe[param].keyframes[index]

        if isinstance(index, slice):
            keyframes = od([(x.index, x.store) for x in keyframes])
        else:
            keyframes = keyframes.store

        msgutils.dumps(keyframes, sort_keys=False)

    @staticmethod
    def keyframe_props(values=None, times=None, dt0=None, dt1=None, dv0=None,
                       dv1=None):
        """flattens provided keyframe properties (removes non-values)

        :param values: `list`, animation parameter values
        :param times: `list`, animation times to apply values
        :param dt0: `list`, preceding time handle pair values
        :param dt1: `list`, succeeding time handle pair values
        :param dv0: `list`, preceding value handle pair values
        :param dv1: `list`, succeeding value handle pair values
        :return: properly format keyframe object
        """

        keyframe = {
            'times': times,
            'values': values,
            'dt0': dt0,
            'dt1': dt1,
            'dv0': dv0,
            'dv1': dv1}

        return utils.flatten(keyframe, bool_=False, iter_=False)

    def merge_animation(self, recipe, steps=_auto_steps, **master):
        """merges src file view parameters into dest file's animation

        :param recipe: `str`, path to file to write animation values to
        :param steps: `int`, number of steps to generate for merge
        :param master: `dict`, keyword arguments in the following format:
                       viewParameter={
                           "t0": start_time,
                           "t1": end_time,
                           "ease": easing_acceleration,
                           "shape": easing_shape,
                           "values": merge_values
                        }
        """

        recipe = self._recipe(recipe)
        t_ones = [x['t1'] for x in master.values()]
        duration = max(t_ones)
        time_line = np.linspace(self._auto_buffer, duration, steps)

        type_t0 = params.animation.times.type_t0
        type_t1 = params.animation.times.type_t1
        min_dist = calcutils.min_distance

        for param, merge in master.items():

            t0 = merge['t0']
            t1 = merge['t1']
            ease = merge['ease']
            shape = merge['shape']
            values = merge['values']
            count = len(values) - 1
            t0 = type_t0(t0)
            t1 = type_t1(t1)
            timeline0, _ = min_dist(time_line, t0)
            timeline1, _ = min_dist(time_line, t1)
            param_steps = timeline1 - timeline0
            duration = t1 - t0

            spans = 0
            for i, v in enumerate(values):
                p = values[i - 1]
                if i != 0 and p != v:
                    spans += 1

            sub_steps = param_steps / count
            span = duration / spans
            index_t0 = t0

            for index, v1 in enumerate(values):

                v0 = values[index - 1]
                if index == 0:
                    continue

                if index == count:
                    index_t1 = t1
                    sub_steps += param_steps % spans
                else:
                    index_t1 = index_t0 + span - self._auto_buffer

                if v0 == v1:
                    continue

                self.auto_keyframes(
                    recipe=recipe, param=param, t0=index_t0, t1=index_t1,
                    v0=v0, v1=v1, ease=ease, shape=shape, steps=sub_steps)

                index_t0 += span

    def search(self, paths):
        """search a file or directory for recipe files

        :param paths:  `list`, list of files or directories to search
        :yield: valid recipe files
        :raise: `ToolError` if a specified path is invalid
        """

        paths = utils.make_iter(paths)
        msg = "searching for valid v{} recipe files".format(self._version)
        isdir = os.path.isdir
        isfile = os.path.isfile

        for i, path in enumerate(paths, start=1):

            msgutils.status(msg, src=path, count=i)
            path = os.path.expanduser(path)

            e = "not a valid file or directory : " + path
            assert (isdir(path) or isfile(path)), ToolError(e, self.print_help)

            if os.path.isfile(path) and self.verify(path):
                yield os.path.abspath(path)

            elif os.path.isdir(path):
                file_paths = utils.walk_path(path, ext='json')

                for file_path in file_paths:
                    if self.verify(file_path):
                        yield os.path.abspath(file_path)

    def verify(self, path):
        """verifies that a inputted file is a valid LFP recipe file

        :param path: `str`, input path to check
        :return: True/False if path is valid or not
        :raise: `ToolError` if exception occurs when JSON data is loaded
        """

        try:
            data = jsonutils.data(path)
        except Exception as e:
            raise ToolError(e, self.print_help)
        else:
            if data is False:
                return False
            keys = data.keys()
            dests = params.dests(meta=True, include_animation=True)
            return all(k in dests for k in keys)

    def view_params(self, **kwargs):
        """parses through kwargs for, and formats, view parameters

        :param kwargs: standard python convention
        :return: formatted view parameters dict
        """

        return self._apt_params(pattern=self._view_pattern, **kwargs)


class Generator(object):
    """on-the-fly recipe generator

    converts a given recipe with animation to single view parameter recipes

    :param recipe_in: `str`, input recipe file
    :param recipe_out: `str`, output recipe file
    :param total: `int`, number of steps to generate
    """

    def __init__(self, recipe_in=None, recipe_out=None, total=0):

        self.store = od()
        self.total = total
        self.recipe_in = Recipe(recipe_in)
        self.recipe_out = Recipe(recipe_out)
        self.recipe_out(self.recipe_in.view_store)

    def __call__(self, mark, recipe_out=None):

        for param, curve in self.store.items():
            cls = self.recipe_out[param].view
            _, t = calcutils.min_distance(curve.keys(), mark)
            v = curve[t]
            cls(v)

        self.recipe_out.path = recipe_out
        self.recipe_out.flush()
        return recipe_out

    def init(self):
        """generator initialization; read input recipe parameters"""

        for param, points in self.recipe_in.points.items():

            x_pts, y_pts = zip(*points)
            type_ = self.recipe_in[param].meta.type_
            curve = calcutils.interp(x_pts, y_pts, num=self.total)
            times, values = curve
            values = [type_(v) for v in values]
            zipped = zip(times, values)

            self.store[param] = {k: v for k, v in zipped}

    def review(self, times):
        """collect view parameter values at specified times

        :param times: `list`, list of times to gather values at
        :return: collected parameter values
        """

        store = od()
        for param, curve in self.store.items():
            store[param] = {}
            cls = self.recipe_out[param]
            type_ = cls.meta.type_

            for mark in times:
                _, t = calcutils.min_distance(curve.keys(), mark)
                v = curve[t]
                store[param][t] = type_(v)

        return store
