# -*- coding: utf-8 -*-
"""Lytro Power Tools - recipe package - core recipetool commands"""

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

import random
import collections

from functools import partial

import dictdiffer

from lpt.lfp.tnt import Tnt
from lpt.lfp.tool import Tool
from lpt.recipe.make import Make
from lpt.recipe.params import Params
from lpt.recipe.recipe import Recipe
from lpt.utils.argutils import ArgUtils
from lpt.utils.calcutils import CalcUtils
from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.utils.msgutils import ToolWarn
from lpt.utils.utils import Utils

tool = Tool()
msgutils = MsgUtils()
utils = Utils()
argutils = ArgUtils()
calcutils = CalcUtils()
view_params = Params()

od = collections.OrderedDict
any_ = partial(utils.any_, iter_=False)
mutual = argutils.mutual


class Cmds(Make):
    """core Recipe Tool commands"""

    def __init__(self):
        Make.__init__(self)

    def anim(self, args, recipe, status):
        """animation command; handles manual/auto/keyframe/scaling functions

        :param args: `argparse.Namespace`, input arguments from recipe
        :param recipe: `recipe.Recipe`, current working recipe
        :param status: `msgutils.MsgUtils.status`, partial object passed to
                       write out current status
        :raise: `ToolError` if incompatible arguments called
        """

        self._set_print_help(args)
        self.view(args, recipe, status)

        param = self._anim_param(args.param)

        anim_props = (args.times, args.values, args.dt0, args.dt1,
                      args.dv0, args.dv1, args.initial_value)

        scale_props = args.scale_time, args.scale_value
        ease_props = args.auto_ease, args.auto_shape, args.auto_steps

        self._assert_t0_lt_t1(args.t0, args.t1)
        auto = self._auto_props(t0=args.t0, t1=args.t1, v0=args.v0, v1=args.v1)
        anim = self._anim_props(*anim_props)
        ease = self._ease_props(*ease_props)
        scale = self._scale_props(*scale_props)

        if args.store:

            mutual(args.store, **anim)
            mutual(args.store, **scale)
            mutual(args.store, **auto)
            mutual(args.store, adjust=args.adjust, destroy=args.destroy)
            param = args.param if args.store == 'show' else param

            status("displaying {} parameter".format(param))

            if args.store == 'show':
                store = recipe[param].store
                msgutils.dumps({param: store})

            elif args.store == 'show_animation':
                store = recipe[param].store
                msgutils.dumps(store)

            else:
                action, index = args.store

                if action == 'points':
                    self.info_points(recipe, param, index)
                elif action == 'keyframes':
                    self.info_keyframes(recipe, param, index)

        if anim or scale or auto:

            [mutual(x, **anim) for x in scale.keys()]
            [mutual(x, **auto) for x in scale.keys()]
            [mutual(x, **anim) for x in auto.keys()]

            status("setting {} properties".format(param))

            if anim:
                self.anim_manual(recipe, param, **anim)
            if scale:
                self.anim_scale(recipe, param, **scale)
            if auto:
                auto.update(**ease)
                self.anim_auto(recipe, param, **auto)

        if args.adjust or args.destroy:
            keyframe = args.adjust or args.destroy
            action = 'adjust' if keyframe == args.adjust else 'destroy'

            status(action + "ing {} keyframe data".format(param))
            mutual(action, **scale)
            mutual(action, **auto)

            if action == 'adjust':

                mutual('adjust', initial_value=args.initial_value)
                e = "--adjust was called but no adjustments were provided"
                assert anim, ToolError(e, self.print_help)
                self.keyframe_adjust(recipe, param, keyframe, **anim)

            elif action == 'destroy':

                mutual('destroy', **anim)
                self.keyframe_destroy(recipe, param, keyframe)

    def current(self, args):
        """primary recipe command

        mediates destroy/info/view/plot/validate
        opens & writes recipe, creates status function

        :param args: `argparse.Namespace`, input arguments from recipe
        :raise: `ToolError` if no valid files processed
        """

        self._set_print_help(args)
        recipe_files = self.search(args.paths)

        i = 0
        for i, recipe_file in enumerate(recipe_files, start=1):

            status = partial(msgutils.status, src=recipe_file, count=i)

            meta = msgutils.msg_meta()[0]
            read = meta + status("reading recipe data", answer=True)

            with msgutils.msg_indicator(read):
                recipe = Recipe(recipe_file, args.print_help)
                before = recipe.store if args.verbose else {}

            args.action(args, recipe, status)

            if args.verbose:
                after = recipe.store
                diff = list(dictdiffer.diff(before, after))
                msgutils.dumps(diff)

            recipe.flush()

        e = "no valid input files found : " + ', '.join(args.paths)
        assert i, ToolError(e, self.print_help)
        count = str(i).zfill(4)
        msgutils.msg("({}) file(s) completed processing".format(count))

    def destroy(self, args, recipe, status):
        """destroy command -- destroys view parameters

        :param args: `argparse.Namespace`, input arguments from recipe
        :param recipe: `recipe.Recipe`, current working recipe
        :param status: `msgutils.MsgUtils.status`, partial object passed to
                       write out current status
        """

        self._set_print_help(args)
        type_ = 'animation' if args.animation else 'view'
        status("destroying {} parameters".format(type_))

        if args.view_all:
            if args.animation:
                store = recipe.animation_store
            else:
                store = recipe.view_store
            keys = store.keys()

        else:
            params = self.view_params(**args.__dict__)
            keys = [k for k, v in params.items() if v]

            if args.animation:
                keys = [self._anim_param(p) for p in keys]

        rjust = msgutils.rjust(alt=keys)

        def item(x): return msgutils.item(x, value=False, rjust=rjust)

        [msgutils.msg(item(k), indent=True) for k in keys if recipe[k].active]
        [recipe[p].delete() for p in keys if recipe[p].active]

    def info(self, args, recipe, status):
        """info command -- displays parameter specific values

        :param args: `argparse.Namespace`, input arguments from recipe
        :param recipe: `recipe.Recipe`, current working recipe
        :param status: `msgutils.MsgUtils.status`, partial object passed to
                       write out current status
        """

        self._set_print_help(args)

        params = self.view_params(**args.__dict__)
        custom = [k for k, v in params.items() if v]
        args.store = args.store if args.store else 'show'
        view = args.store == 'show'
        keys = custom or params.keys()

        if not view:
            _keys = []
            invalid = []

            for param in keys:
                if recipe[param].meta.animation:
                    _keys.append(param)
                else:
                    invalid.append(param)

            if invalid and custom:
                for key in invalid:
                    w = "not an animatable parameter, skipping: " + key
                    ToolWarn(w)

            keys = [p + 'Animation' for p in _keys]

        if isinstance(args.store, tuple):
            action, index = args.store

            status("showing recipe animation " + action)

            for param in keys:

                cls = recipe[param]
                if not cls.active:
                    if custom:
                        msgutils.dumps({param: {}})
                    continue

                status(param)
                if action == 'keyframes':
                    self.info_keyframes(recipe, param, index)
                elif action == 'points':
                    self.info_points(recipe, param, index)

        else:

            if view:
                out = recipe.view_store
                type_ = "view parameters"

                def param(): return p

            else:
                out = recipe.animation_store
                type_ = "animation data"

                def param(): return p + "Animation"

            [out.update({param(): {}}) for p in custom if param() not in out]
            status("showing recipe " + type_)
            results = [{p: out[p]} for p in keys if p in out]
            msgutils.dumps(results)

    def merge(self, args):
        """merge command -- merges recipes into one

        :param args: `argparse.Namespace`, input arguments from recipe
        :raise: `ToolError` if invalid arguments/files specified
        """

        self._set_print_help(args)
        merge_list = args.merge_list
        items = args.__dict__.items()
        avail = []
        shape = args.t0, args.t1, args.auto_ease, args.auto_shape
        eases = {k: shape for k in merge_list}
        custom = {k: v for k, v in items if k in eases and v}
        status = msgutils.status

        self._assert_t0_lt_t1(args.t0, args.t1)

        if args.select:
            e = "--select: at least one view parameter selection is required"
            assert custom, ToolError(e, self.print_help)

            for k, v in eases.items():
                if k not in custom:
                    del eases[k]
                    continue
                if any(custom[k]):
                    eases[k] = custom[k]
        else:
            eases.update(custom)

        for param, attrs in eases.items():
            t0, t1, ease, shape = attrs
            self._assert_t0_lt_t1(t0, t1, param)
            if not any_(t0):
                t0 = self._auto_buffer
            if not any_(t1):
                t1 = t0 + self._auto_duration
            if not ease:
                ease = self._auto_ease
            if not shape:
                shape = self._auto_shape
            eases[param] = t0, t1, ease, shape

        recipes = []
        status("reading recipes", src=args.merge_in, count=0)

        for index, obj in enumerate(args.merge_in):

            if self.verify(obj):
                recipe = Recipe(obj, self.print_help)
            elif tool.valid_lfp_file(obj, warp=True):
                recipe = self.get_lfp_recipe(obj)
            else:
                e = "not a valid file for merging: {}".format(obj)
                raise ToolError(e, self.print_help)

            for param in recipe:
                cls = recipe[param]
                if param in avail or param.endswith('Animation'):
                    continue
                if cls.meta.animation:
                    avail.append(param)

            if custom:
                for param in custom:
                    e = ("cannot merge; {} does not contain a {} value"
                         .format(obj, param))
                    assert recipe[param].active, ToolError(e, self.print_help)

            recipes.append(recipe)

        [eases.__delitem__(p) for p in merge_list if p not in avail]

        values = od([])

        for param in avail:
            skip_param = "skipping {} merge:".format(param)

            for recipe in recipes:
                if custom and param not in custom:
                    continue

                value = recipe[param].store
                not_found = msgutils.item("no value found", recipe.path)

                if not any_(value):
                    ToolWarn(skip_param)
                    msgutils.msg(not_found, indent=True)
                    del eases[param]
                    break

                if param not in values:
                    values[param] = []
                values[param].append(value)

        merge = od([(k, v) for k, v in values.items() if len(set(v)) > 1])

        for param, values in merge.items():
            t0, t1, ease, shape = eases[param]
            merge[param] = {'t0': t0, 't1': t1, 'ease': ease,
                            'shape': shape, 'values': values}

        w = ("nothing to merge into an animation, no "
             "value changes found for selected view parameters")

        if args.verbose:
            msgutils.status("parameters to merge", count=0)
            msgutils.dumps(merge)

        for i, file_path in enumerate(args.paths, start=1):

            recipe_out = utils.sanitize_path(file_path)
            recipe = Recipe(recipe_out, self.print_help)
            status = partial(msgutils.status, dest=recipe_out, count=i)

            meta = msgutils.msg_meta()[0]
            read = meta + status("merging recipe data", count=i, answer=True)

            with msgutils.msg_indicator(read):
                views = recipes[0].view_store
                recipe(views)
                self.merge_animation(recipe, args.auto_steps, **merge)

            if i == 1 and args.verbose:
                status("recipe view parameters")
                msgutils.dumps(recipe.view_store)

                status("recipe animation parameters")
                msgutils.dumps(recipe.animation_store)

            if not recipe.animation_store:
                ToolWarn(w)

            status("writing to new recipe file")
            recipe.flush()

    def new(self, args):
        """new command -- creates new recipes

        :param args: `argparse.Namespace`, input arguments from recipe
        """

        self._set_print_help(args)

        for i, file_path in enumerate(args.paths, start=1):
            recipe_out = utils.sanitize_path(file_path)
            msgutils.status("generating new recipe file",
                            count=i, dest=recipe_out)
            Tnt(recipe_out=recipe_out).execute()
            recipe = Recipe(recipe_out, self.print_help)
            recipe.flush()

    def plot(self, args, recipe, status):
        """plot command -- graphs out animation parameter values

        :param args: `argparse.Namespace`, input arguments from recipe
        :param recipe: `recipe.Recipe`, current working recipe
        :param status: `msgutils.MsgUtils.status`, partial object passed to
                       write out current status
        :raise: `ToolError` if matplotlib not found or no animation data found
        """

        self._set_print_help(args)

        try:
            # noinspection PyUnresolvedReferences,PyPackageRequirements
            import matplotlib.pyplot as plt
            # noinspection PyUnresolvedReferences,PyPackageRequirements
            import matplotlib.pylab as pylab
        except ImportError as e:
            raise ToolError(e, args.print_help)

        custom = self.anim_params(**args.__dict__)
        params = custom or recipe.animation_store

        e = "no animation data found: {}".format(recipe.path)
        assert params, ToolError(e, self.print_help)

        p = len(params)
        r = 4
        c = p / r + (1 if p % r else 0)

        plt.figure(figsize=(12, 12), dpi=80)
        plt.subplots_adjust(wspace=.9, hspace=.5,
                            top=.9, left=.1,
                            bottom=.1, right=.9)

        plt.suptitle(recipe.path)

        if args.save:
            png = recipe.path.replace('json', 'png')
            png = utils.sanitize_path(png)
        else:
            png = None

        plot = None
        meta = msgutils.msg_meta()[0]
        read = meta + status("plotting animation", answer=True)

        with msgutils.msg_indicator(read):

            for i, param in enumerate(params, start=1):

                cls = recipe[param]
                pts = cls.points
                name = cls.view.name
                self._assert_points(pts, param)
                x_pts, y_pts = zip(*pts)

                if not pts and custom:
                    status(param + ": no animation found", indent=True)
                    continue

                if args.verbose:
                    msgutils.dumps({param: pts})

                if len(params) > 1:
                    pylab.subplot(r, c + 1, i, aspect='auto')

                plot = True
                pylab.title(name)
                pylab.xlabel('time')
                pylab.ylabel('value')
                color = random.choice('rgbcmyk')
                plt.plot(x_pts, y_pts, color=color)

        if not plot:
            plt.close()
            return

        if args.save:
            status("writing to file", dest=png)
            plt.savefig(png, orientation='landscape')
        else:
            plt.show()

        plt.close()

    def validate(self, args, recipe, status):
        """validate command -- validates recipe against LFP schema

        :param args: `argparse.Namespace`, input arguments from recipe
        :param recipe: `recipe.Recipe`, current working recipe
        :param status: `msgutils.MsgUtils.status`, partial object passed to
                       write out current status
        """

        self._set_print_help(args)
        status("validating recipe schema")
        recipe.validate()

    def view(self, args, recipe, status):
        """view command -- modifies/add view parameter values

        :param args: `argparse.Namespace`, input arguments from recipe
        :param recipe: `recipe.Recipe`, current working recipe
        :param status: `msgutils.MsgUtils.status`, partial object passed to
                       write out current status
        """

        self._set_print_help(args)
        params = self.view_params(**args.__dict__)

        if params:
            status("adjusting view parameters")

        for param, value in params.items():
            cls = recipe[param]
            cls(value)

    def view_ccm(self, args, recipe, status):
        """ccm command -- modifies/add ccm values

        :param args: `argparse.Namespace`, input arguments from recipe
        :param recipe: `recipe.Recipe`, current working recipe
        :param status: `msgutils.MsgUtils.status`, partial object passed to
                       write out current status
        """

        self._set_print_help(args)
        view = args.__dict__['viewCcm']

        if view:
            mutual('view', show=args.store)
            mutual('view', index=args.index)
            recipe.ccm.delete()
            self.view(args, recipe, status)

        elif args.store:

            mutual(args.store, index=args.index)
            status("showing viewCcm properties")
            msgutils.dumps({args.param: recipe[args.param].store})

        elif args.index:

            index, value = args.index
            index = int(index)

            status("modifying viewCcm index")
            recipe.ccm[index](value)

    def view_crop(self, args, recipe, status):
        """crop command -- modifies/add crop parameter values

        :param args: `argparse.Namespace`, input arguments from recipe
        :param recipe: `recipe.Recipe`, current working recipe
        :param status: `msgutils.MsgUtils.status`, partial object passed to
                       write out current status
        """

        self._set_print_help(args)
        params = self.crop(
            angle=args.angle,
            top=args.top,
            right=args.right,
            bottom=args.bottom,
            left=args.left)

        crop = recipe[args.param]

        if args.store:
            mutual(args.store, **params)
            status("showing viewCrop properties")
            msgutils.dumps({args.param: crop.store})
        else:
            status("adjusting viewCrop properties")
            crop(params)

    def view_luminance(self, args, recipe, status):
        """luminance command -- modifies/add luminance tone curve values

        :param args: `argparse.Namespace`, input arguments from recipe
        :param recipe: `recipe.Recipe`, current working recipe
        :param status: `msgutils.MsgUtils.status`, partial object passed to
                       write out current status
        """

        self._set_print_help(args)
        tone_curve = recipe.luminance_tone_curve

        def _status(x): return status(x + " viewLuminanceToneCurve properties")

        if args.store:
            _status("showing")
            msgutils.dumps({args.param: tone_curve.store})

        else:
            _status("adjusting")
            points = self.control_points(args.x, args.y)
            control_points = tone_curve.control_points

            if args.index:
                mutual('index', view=args.param)
                argutils.assert_len({'x': args.x, 'y': args.y})
                index = control_points[args.index]
                index(points[0])
            else:
                control_points(points)
