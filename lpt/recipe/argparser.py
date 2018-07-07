# -*- coding: utf-8 -*-
"""Lytro Power Tools - recipe package - recipetool argument parsing"""

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

import argparse
import functools
from copy import deepcopy

from lpt.recipe import config
from lpt.recipe.cmds import Cmds
from lpt.recipe.make import Make
from lpt.recipe.params import BaseView
from lpt.recipe.params import Params
from lpt.utils.argutils import ArgUtils
from lpt.utils.argutils import StoreWithConst
from lpt.utils.calcutils import CalcUtils
from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.utils.utils import Utils

cmds = Cmds()
make = Make()
utils = Utils()
params = Params()
argutils = ArgUtils()
msgutils = MsgUtils()
calcutils = CalcUtils()

dflt = argutils.arg_default
choices = argutils.arg_choices


class ArgParser(BaseView):
    """base parser object for adding view parameters as subparsers"""

    _auto_ease = config.db['auto_ease']
    _auto_shape = config.db['auto_shape']
    _auto_steps = config.db['auto_steps']
    _auto_buffer = config.auto_buffer
    _auto_duration = config.db['auto_duration']
    _auto_eases, _auto_shapes = argutils.easers

    def _cls_vals(self, **kwargs):
        """flattens arguments passed to argparse.add_parser"""

        if kwargs:
            cls_vals = {k.rstrip('_'): v for k, v in kwargs.items()}
        else:
            cls_vals = dict(
                action=self.action,
                choices=self.choices,
                const=self.const,
                default=self.default,
                dest=self.dest,
                help=self.help_,
                metavar=self.metavar,
                nargs=self.nargs,
                type=self.type_,
                required=self.required)

        if 'help' in cls_vals:
            help_ = cls_vals['help']
            if isinstance(help_, str):
                help_ = help_.split('\n')[0]
            cls_vals['help'] = help_

        return utils.flatten(cls_vals, bool_=False, iter_=False)

    @staticmethod
    def _flag_desc(flags):
        """pretties a list of argument flags into two columns"""

        flag_half = len(flags) / 2
        flags_desc = ''

        for a, b in zip(flags[:flag_half], flags[flag_half:]):
            flags_desc += '{:<30}{:<}\n'.format(a, b)

        return flags_desc

    def _init(self, properties):

        self.cmd = None
        self.unique = False
        self.depends = []
        self.min_items = 0
        self.max_items = False
        self.default_value = None
        self.enabled = True
        self.ver = False
        self.alt = None
        self.range_ = ()

        self.action = None
        self.choices = []
        self.const = None
        self.default = None
        self.dest = ''
        self.help_ = None
        self.metavar = None
        self.type_ = None
        self.nargs = None
        self.required = None

        self.animation = {}
        self.crop = {}
        self.luminance_tone_curve = {}
        self.__dict__.update(properties.__class__.__dict__)

        self.type_ = deepcopy(self.type_)
        if self.range_:
            self.type_.keywords['clip'] = False
        if self.type_:
            self.type_.keywords['arg'] = self.key_arg

    def add_parser(self, properties, subparsers, view):
        """creates a subparser based off of view parameter class properties

        :param properties: `params.Param`, view parameter class properties
        :param subparsers: subparsers to add argument properties
        :param view: `argparse.Namespace`, argparse group used for special
                     argparse parameter functions
        """

        self._init(properties)

        epilog = "Lytro Power Tools - Recipe Tool - " + self.key_title

        desc = self.help_
        help_ = desc.split('\n')[0]

        parser = subparsers.add_parser(
            self.key_parser,
            description=desc,
            help=help_,
            epilog=epilog,
            formatter_class=argutils.formatter_class())

        self.arg_recipe_in(parser)

        if self.crop:
            action = cmds.view_crop
            self.args_crop(parser)

        elif self.luminance_tone_curve:
            action = cmds.view_luminance
            self.args_luminance(parser)

        elif self.dest == 'viewCcm':
            action = cmds.view_ccm
            self.args_view(view, parser)

        else:
            action = cmds.view
            self.args_view(view, parser)

        if self.animation:
            action = cmds.anim
            self.args_animation(parser)
            anim = True
        else:
            anim = False

        self.args_store(parser, animation=anim)

        parser.set_defaults(
            action=action,
            func=cmds.current,
            keyframe=None,
            param=self.dest,
            print_help=parser.print_help)

    @staticmethod
    def arg_animation_store_true(parser):
        """adds argument to use animation parameter in place of view parameter

        used with destroy, info

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        parser.add_argument(
            '-A', '--animation',
            default=False,
            action='store_true',
            help="use animation parameter in place of view parameter",
            dest='animation')

    @staticmethod
    def arg_destroy_all(parser):
        """adds an argument to destroy all parameters

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        parser.add_argument(
            '--all',
            default=False,
            action='store_true',
            help="destroy all view parameters",
            dest='view_all')

    @staticmethod
    def arg_recipe_in(parser):
        """adds recipe input argument to given parser

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        title = "input arguments"
        desc = utils.dedent('''
        -i, --recipe-in [<PATH> ...]    execute operation on input recipe
                                        files or scanned directories
        ''')

        recipe = parser.add_argument_group(title=title, description=desc)
        recipe.add_argument(
            '-i', '--recipe-in',
            nargs='+',
            required=True,
            dest='paths',
            help=argparse.SUPPRESS)

    @staticmethod
    def arg_recipe_out(parser):
        """adds recipe output argument to given parser

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        title = "output arguments"
        desc = utils.dedent('''
        -o, --recipe-out [<PATH> ...]   recipe output file path(s)
        ''')

        parser.add_argument_group(title=title, description=desc)
        parser.add_argument(
            '-o', '--recipe-out',
            default=[config.recipe_json],
            nargs='*',
            dest='paths',
            help=argparse.SUPPRESS)

    @staticmethod
    def arg_select(parser):
        """select argument

        :param parser: `argparse.Namespace`, parser to add argument to
        """

        parser.add_argument(
            '--select',
            action='store_true',
            default=False,
            help=argparse.SUPPRESS)

    def arg_view_store_true(self, parser, arg=None, dest=None, suppress=True):
        """argparse ``store_bool`` action using `self` view argument

        :param arg: `str`, argument string, defaults to `self.key_arg`
        :param dest: `str`, string to use for `argparse.Namespace` destination

        :param parser: `argparse.Namespace`, parser to add arguments to
        :param suppress: `bool`, suppress argparse help
        """

        help_ = argparse.SUPPRESS if suppress else self.help_.split('\n')[0]
        arg = arg or self.key_arg
        dest = dest or self.dest

        parser.add_argument(
            arg,
            help=help_,
            default=False,
            dest=dest,
            action='store_true')

    def args_animation(self, parser):
        """adds animation specific argparse parameters

        uses current `self` class properties

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        self.args_auto(parser)
        anim = params.animation

        def doc(x): return getattr(anim, x).__doc__.lstrip('animation')

        dv0 = self.animation['dv0']
        dv1 = self.animation['dv1']

        if dv0.range_:
            dv0_min = dv0.range_[0]
            dv0_max = dv0.range_[1]
            dv1_min = dv1.range_[0]
            dv1_max = dv1.range_[1]
        else:
            dv0_min = dv0_max = dv1_min = dv1_max = 'n/a'

        dv0_meta = argutils.min_max.format(min_=dv0_min, max_=dv0_max)
        dv1_meta = argutils.min_max.format(min_=dv1_min, max_=dv1_max)

        desc = utils.dedent('''
        -T, --times  [<TIME> ...]      {times}
        -V, --values [<VALUE> ...]     {values}
        -I, --initial-value <VALUE>    {initial_value}
            --dt0 [<(-T) OFFSET> ...]  {dt0} (positive float)
            --dt1 [<(+T) OFFSET> ...]  {dt1} (negative float)
            --dv0 [<(-V) OFFSET> ...]  {dv0} {dv0_meta}
            --dv1 [<(+V) OFFSET> ...]  {dv1} {dv1_meta}
        '''.format(
            initial_value=doc('initial_value'),
            times=doc('times'),
            values=doc('values'),
            dt0=doc('dt0'),
            dt1=doc('dt1'),
            dv0=doc('dv0'),
            dv1=doc('dv1'),
            dv0_meta=dv0_meta,
            dv1_meta=dv1_meta))

        anim_group = parser.add_argument_group(
            title="manual animation arguments",
            description=desc)

        add_arg = anim_group.add_argument

        for arg, cls in self.animation.items():

            type_ = deepcopy(cls.type_)
            type_.keywords['arg'] = cls.key_arg
            if cls.range_:
                type_.keywords['clip'] = False

            cls_vals = {
                'dest': cls.key_cls,
                'metavar': cls.metavar,
                'type': type_,
                'help': argparse.SUPPRESS,
                'nargs': cls.nargs}

            cls_vals = self._cls_vals(**cls_vals)

            if cls.alt:
                args = '-' + cls.alt, cls.key_arg
            else:
                args = cls.key_arg,

            add_arg(*args, **cls_vals)

        self.args_keyframe(parser)
        self.args_scale(parser)

    def args_auto(self, parser):
        """adds auto animation specific argparse parameters

        uses current `self` class properties

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        shape = dflt(self._auto_shape)
        ease = dflt(self._auto_ease)
        steps = dflt(self._auto_steps)

        desc = utils.dedent('''
        * start time & value priority:
            time:  inputted t0 time  -> preceding keyframe's time  -> t={buff}
            value: inputted v0 value -> preceding keyframe's value ->
                   initial value -> view parameter -> parameter default ({n})
        * end time & value priority:
            time:  inputted t1 time -> a duration of {dur} seconds is applied
            value: inputted v1 value (required)
        * arguments:
            --t0       <TIME>           start time
            --v0       <VALUE>          start value
            --t1       <TIME>           end time
            --v1       <VALUE>          end value

        -e, --ease     <ACCEL>          ease acceleration {eases}
                                                          {ease}
        -f, --shape    <SHAPE>          ease shape        [choices: {shape0}
                                                                    {shape1}
                                                          {shape}
        -n, --steps    <STEPS>          ease steps        {steps}
        '''.format(buff=self._auto_buffer,
                   dur=self._auto_duration,
                   ease=ease,
                   eases=choices(self._auto_eases),
                   shape=shape,
                   shape0=','.join(self._auto_shapes[::2]),
                   shape1=','.join(self._auto_shapes[1::2]),
                   n=self.default_value,
                   param=self.dest,
                   steps=steps))

        group = parser.add_argument_group(
            title='auto animation arguments',
            description=desc)

        self.args_t(group)
        self.args_v(group)
        self.args_easing(group)

    def args_crop(self, parser):
        """adds crop specific argparse parameters

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        desc = utils.dedent('''
        -a, --angle  <FLOAT>            corresponds to crs:CropAngle
        -t, --top    <FLOAT>            corresponds to crs:CropTop
        -l, --left   <FLOAT>            corresponds to crs:CropLeft
        -b, --bottom <FLOAT>            corresponds to crs:CropBottom
        -r, --right  <FLOAT>            corresponds to crs:CropRight
        ''')

        crop = parser.add_argument_group(
            title='crop arguments',
            description=desc)

        cls_vals = self._cls_vals()

        for arg, cls in self.crop.items():
            s = arg[0]
            cls_vals['dest'] = arg
            cls_vals['help'] = argparse.SUPPRESS
            cls_vals['type'] = cls.type_
            crop.add_argument('-' + s, cls.key_arg, **cls_vals)

    def args_easing(self, parser):
        """adds animation easing specific arguments

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        parser.add_argument(
            '-e', '--ease',
            dest='auto_ease',
            default=self._auto_ease,
            choices=self._auto_eases,
            help=argparse.SUPPRESS)

        parser.add_argument(
            '-f', '--shape',
            dest='auto_shape',
            default=self._auto_shape,
            choices=self._auto_shapes,
            help=argparse.SUPPRESS)

        parser.add_argument(
            '-n', '--steps',
            dest='auto_steps',
            default=self._auto_steps,
            type=int,
            help=argparse.SUPPRESS)

    @staticmethod
    def args_keyframe(parser):
        """adds animation keyframe specific argparse parameters

        uses current `self` class properties

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        desc = utils.dedent('''
        -a, --adjust  <KEYFRAME>        adjust animation keyframe
        -d, --destroy <KEYFRAME>        destroy animation keyframe
        ''')

        keyframe = parser.add_argument_group(
            title='animation keyframe arguments',
            description=desc)
        keyframe = keyframe.add_mutually_exclusive_group()

        keyframe.add_argument(
            '-a', '--adjust',
            default=None,
            help=argparse.SUPPRESS,
            type=int)

        keyframe.add_argument(
            '-d', '--destroy',
            default=None,
            help=argparse.SUPPRESS,
            type=int)

    @staticmethod
    def args_store(parser, info=False, animation=True):
        """adds animation store specific argparse parameters

        uses current `self` class properties

        :param parser: `argparse.Namespace`, parser to add arguments to
        :param info: `bool`, `parser` is ``info`` subcommand
        :param animation: `bool`, add animation specific arguments
        """

        desc = utils.dedent('''
        -S, --show                      show view parameter value {}
        '''.format("(default)" if info else ""))

        if animation:
            desc += utils.dedent('''
        -A, --show-animation            show animation data
        -K, --keyframes [<index>]       show animation data as keyframes
                                         index : display only specified index
        -P, --points    [<index>/x/y/]  show animation data as x/y points:
                                             x : time data points
                                             y : value data points
                                         index : x/y points for specified index
                                          none : all x/y data points
            ''')

        store = parser.add_argument_group(
            title='info arguments',
            description=desc)

        store = store.add_mutually_exclusive_group()

        store.add_argument(
            '-S', '--show',
            const='show',
            default=None,
            action='store_const',
            help=argparse.SUPPRESS,
            dest='store')

        if not animation:
            return

        store.add_argument(
            '-A', '--show-animation',
            const='show_animation',
            default=None,
            action='store_const',
            help=argparse.SUPPRESS,
            dest='store')

        store.add_argument(
            '-K', '--keyframes',
            const='keyframes',
            default=None,
            dest='store',
            nargs='?',
            type=functools.partial(argutils.show_keyframe, arg='keyframes'),
            action=StoreWithConst,
            help=argparse.SUPPRESS)

        store.add_argument(
            '-P', '--points',
            const='points',
            default=None,
            dest='store',
            nargs='?',
            type=functools.partial(argutils.show_xy, arg='points'),
            action=StoreWithConst,
            help=argparse.SUPPRESS)

    def args_luminance(self, parser):
        """adds luminance specific argparse parameters

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        title = "luminance tone curve arguments"
        desc = utils.dedent('''
        -x [<POINT> ...]                x axis points (min: 2)
        -y [<POINT> ...]                y axis points (min: 2)
        --index <INDEX>                 modify an existing pair of points
        ''')

        x = self.luminance_tone_curve['x']
        y = self.luminance_tone_curve['y']

        luminance = parser.add_argument_group(title, description=desc)
        luminance.add_argument(
            '-x',
            action=x.action,
            nargs=x.nargs,
            dest=x.dest,
            help=argparse.SUPPRESS,
            default=x.default,
            type=x.type_)

        luminance.add_argument(
            '-y',
            action=y.action,
            nargs=y.nargs,
            dest=y.dest,
            default=y.default,
            help=argparse.SUPPRESS,
            type=y.type_)

        luminance.add_argument(
            '--index',
            help=argparse.SUPPRESS,
            type=int,
            default=None)

    def args_merge(self, parser, groups):
        """adds merge `argparse` parameters

        uses current `self` class properties

        :param parser: `argparse.Namespace`, parser to add arguments to
        :param groups: `dict`, grouped view parameters
        """

        shape = dflt(self._auto_shape)
        ease = dflt(self._auto_ease)
        steps = dflt(self._auto_steps)

        anim_args = []

        for group, props in groups.items():
            props = [p for p in props if p.animation]
            for prop in props:
                anim_args.append((prop.key_arg, prop.dest))

        anim_args.sort()
        flags, merge_list = zip(*anim_args)
        flags_desc = self._flag_desc(flags)

        input_desc = utils.dedent('''
        -i, --merge-in  [<PATH> ...]    source recipe OR warp LFP files
        ''')

        merge_desc = utils.dedent('''
        -s, --select                    merge only selected parameter arguments
        -n, --steps      <STEPS>        max number of steps to generate {steps}
        -e, --ease       <ACCEL>        easing acceleration {ease}
                                                            {eases}
        -f, --shape      <SHAPE>        easing shape        {shape}
                                                            [choices: {shape0}
                                                                      {shape1}]
            --t0         <SECOND>       start time          {start}
            --t1         <SECOND>       end time            {end}

        '''.format(
            start=dflt("{} seconds".format(self._auto_buffer)),
            end=dflt("start time + {} seconds".format(self._auto_duration)),
            shape0=','.join(self._auto_shapes[::2]),
            shape1=','.join(self._auto_shapes[1::2]),
            eases=choices(self._auto_eases),
            ease=ease,
            shape=shape,
            steps=steps))

        param_desc = utils.dedent('''
        comma separated overrides for t0, t1, function & method; missing
        sub-arguments will default to the global argument value;

        using desired sub-arguments, strings must match the following format:

              --param option=value
        e.g.: --param t0=5,t1=15,function=cubic,method=in_out

        available parameters:

        ''') + flags_desc

        input_ = parser.add_argument_group(
            title='input arguments',
            description=input_desc)

        merge = parser.add_argument_group(
            title='merge arguments',
            description=merge_desc)

        parser.add_argument_group(
            title='parameter arguments',
            description=param_desc)

        merge.set_defaults(merge_list=merge_list)
        input_.add_argument(
            '-i', '--merge-in',
            help=argparse.SUPPRESS,
            nargs='+',
            required=True,
            dest='merge_in')

        self.args_t(merge)
        self.args_easing(merge)
        self.arg_select(merge)

        for arg, dest in anim_args:
            parser.add_argument(
                arg,
                help=argparse.SUPPRESS,
                default='',
                nargs='?',
                dest=dest,
                action=_Merge)

    @staticmethod
    def args_plot(parser):
        """arguments specific to plot

        :param parser: `argparse.Namespace`, parser to add argument to
        """
        parser.add_argument(
            '-S', '--save',
            action='store_true',
            default=False,
            help="save graph to disk (do not display)")

    def args_scale(self, parser):
        """adds animation scaling specific `argparse` parameters

        uses current `self` class properties

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        title = "scaling arguments"
        desc = utils.dedent('''
        --scale-time  <START> <END>     scale animation time to new start/end
        --scale-value <START> <END>     scale animation value to new start/end
        ''')

        times = self.animation['times']
        values = self.animation['values']

        scale = parser.add_argument_group(title, description=desc)
        scale.add_argument(
            '--scale-time',
            help=argparse.SUPPRESS,
            type=times.type_scale,
            nargs=2)

        scale.add_argument(
            '--scale-value',
            help=argparse.SUPPRESS,
            type=values.type_scale,
            nargs=2)

    def args_t(self, parser):
        """adds time start/end specific arguments

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        times = self.animation['times']

        parser.add_argument(
            '--t0',
            dest='t0',
            default=None,
            type=times.type_t0,
            help=argparse.SUPPRESS)

        parser.add_argument(
            '--t1',
            dest='t1',
            default=None,
            type=times.type_t1,
            help=argparse.SUPPRESS)

    def args_v(self, parser):
        """adds value start/end specific arguments

        :param parser: `argparse.Namespace`, parser to add arguments to
        """

        values = self.animation['values']

        parser.add_argument(
            '--v0',
            dest='v0',
            type=values.type_v0,
            help=argparse.SUPPRESS)

        parser.add_argument(
            '--v1',
            dest='v1',
            type=values.type_v1,
            help=argparse.SUPPRESS)

    def args_view(self, view_parser=None, cmd_parser=None):
        """adds view parameter arguments to specified parser

        :param view_parser: `argparse.Namespace`, add view parameter
                            arguments to view subparser
        :param cmd_parser: `argparse.Namespace`, add arguments for view
                           parameter subparsers
        """

        cls_vals = self._cls_vals()
        store_bool = self.action in ('store_true', 'store_false')
        view_arg = self.key_arg

        if store_bool:
            cls_vals['default'] = None
            del cls_vals['type']

        if view_parser:
            view_parser.add_argument(view_arg, **cls_vals)
        if not cmd_parser:
            return

        if store_bool:
            desc = utils.dedent('''
            -t, --true
            -f, --false
            ''')

            t_vals = deepcopy(cls_vals)
            f_vals = deepcopy(cls_vals)
            t_vals['action'] = 'store_true'
            f_vals['action'] = 'store_false'

            arg_sets = [
                (('-t', '--true'), t_vals),
                (('-f', '--false'), f_vals)]

        else:

            if self.metavar:
                meta = '<{}>'.format(self.metavar)
            else:
                str_ = ','.join([str(x) for x in self.choices])
                meta = '[{}]'.format(str_)

            arg_sets = [(('-v', '--view'), cls_vals)]

            if self.dest == 'viewCcm':

                index = {'nargs': 2, 'default': None}
                arg_sets.append((('-I', '--index',), index))
                mod = "modify existing value by index".rjust(35)
                descs = ['-v, --view [9 <VALUES>]' + meta.rjust(16),
                         '-I, --index <INDEX> <VALUE>' + mod]
                desc = utils.dedent('\n'.join(descs))

            else:
                desc = utils.dedent('-v, --view <VALUE>' + meta.rjust(21))

        group = cmd_parser.add_argument_group(
            title="view arguments",
            description=desc)

        if store_bool:
            group = group.add_mutually_exclusive_group()

        for args, vals in arg_sets:

            vals['help'] = argparse.SUPPRESS
            group.add_argument(*args, **vals)

    def args_view_store_true(self, parser, groups):

        """`argparse` ``store_bool`` action using `self` view argument

        :param parser: `argparse.Namespace`, parser to add arguments to
        :param groups: `dict`, grouped view parameters
        """

        flags = []

        for group, props in groups.items():
            for prop in props:
                self.arg_view_store_true(parser, prop.key_arg, prop.dest)
                flags.append(prop.key_arg)

        flags.sort()
        flags_desc = self._flag_desc(flags)

        parser.add_argument_group(
            title='available view parameters',
            description=flags_desc)


class _Merge(argparse.Action):
    """`argparse.Action` converts merge sub-arguments

    :raise: `ToolError` if invalid argument specified or unrecognized format
    """

    def __call__(self, parser, namespace, values, option_string=None):

        _eases, _shapes = argutils.easers
        ease = shape = t0 = t1 = ''
        items = []

        if values:
            items = [i.split('=') for i in values.split(',')]
            valid = [len(x) == 2 for x in items]
            e = "unrecognized merge format: {}".format(values)
            assert all(valid), ToolError(e, parser.print_help)

        for key, value in items:

            if key == 't0':
                t0 = params.animation.times.type_t0(value)
            elif key == 't1':
                t1 = params.animation.times.type_t0(value)
            elif key == 'ease':
                ease = argutils.choice(value, _eases, 'ease')
            elif key == 'shape':
                shape = argutils.choice(value, _shapes, 'shape')
            else:
                e = "unknown merge option/argument: {}={}".format(key, value)
                raise ToolError(e, parser.print_help)

        setattr(namespace, self.dest, (t0, t1, ease, shape))
