# -*- coding: utf-8 -*-
"""Lytro Power Tools - recipe package - view parameter classes"""

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
import functools

from lpt.recipe import config
from lpt.utils.argutils import ArgUtils
from lpt.utils.msgutils import MsgUtils

argutils = ArgUtils()
msgutils = MsgUtils()

od = collections.OrderedDict

choice = argutils.choice
number = argutils.number
boolean = argutils.boolean
in_range = argutils.in_range
type_type = argutils.type_type
float_meta = argutils.float_meta
meta_range = argutils.meta_range
arg_format = argutils.arg_format
negative_meta = argutils.negative_meta
positive_meta = argutils.positive_meta
unsigned_number = argutils.unsigned_number

negative = (None, 0.0)
positive = (0.0, None)
signed_5 = (-5.0, 5.0)
signed_int_100 = (-100, 100)
signed_int_150 = (-150, 150)
unsigned_10 = (0.0, 10.0)
unsigned_int_100 = (0, 100)
unsigned_int_150 = (0, 150)

signed_5_meta = meta_range(signed_5)
signed_int_100_meta = meta_range(signed_int_100)
signed_int_150_meta = meta_range(signed_int_150)

unsigned_10_meta = meta_range(unsigned_10)
unsigned_int_100_meta = meta_range(unsigned_int_100)
unsigned_int_150_meta = meta_range(unsigned_int_150)

print_help_obj = object


class BaseView(object):
    """base parser object for adding view parameters as subparsers"""

    group = 'meta'
    versions = config.recipe_versions

    cmd = None
    unique = False
    depends = []
    min_items = 0
    max_items = False
    default_value = None
    enabled = True
    ver = False
    alt = None
    range_ = ()

    dt0 = None
    dt1 = None
    dv0 = None
    dv1 = None
    times = None
    values = None
    initial_value = None

    action = None
    choices = []
    const = None
    default = None
    dest = ''
    help_ = None
    metavar = None
    nargs = None
    required = None
    type_ = None

    animation = {}
    crop = {}
    luminance_tone_curve = {}
    fx = {}

    def _key(self, **kw):
        return arg_format(self.dest, camel=True, rm='view', ver=self.ver, **kw)

    @property
    def key_arg(self):
        """`self.dest` in argument format: ``--view-parameter``

        :return: formatted string
        """

        return self._key(join='-', pre='--')

    @property
    def key_cls(self):
        """`self.dest` in class format: ``view_parameter``

        :return: formatted string
        """

        return self._key(join='_')

    @property
    def key_parser(self):
        """`self.dest` in parser format: ``view-parameter``

        :return: formatted string
        """

        return self._key(join='-')

    @property
    def key_title(self):
        """`self.dest` in title format: ``View Parameter``

        :return: formatted string
        """

        return self._key(join=' ').title()


class _Partial(functools.partial):
    """functools partial repr override"""
    def __repr__(self):
        return '\b'


class _Animation(collections.MutableMapping, BaseView):
    """animation specific properties

    parameter   : n/a
    properties  : times, values, handlePairs, initialValue
    type        : float

    times
        default : []
        min     : 0
        max     : n/a
        unique  : true

    values
        default : []
        min     : parameter dependent
        max     : parameter dependent

    handlePairs
        default : []

        dt0
            min : 0
            max : n/a
        dt1
            min : 0
            max : n/a
        dv0
            min : parameter dependent
            max : parameter dependent
        dv1
            min : parameter dependent
            max : parameter dependent

    initialValue
        default : null
        min     : parameter dependent
        max     : parameter dependent

    :param type_: `object`, animation value type
    :param metavar: `str`, argument menu metavar
    :print range_: `tuple`, start/end of range, if applicable
    """

    help_ = __doc__
    versions = [1, 2, 3, 4, 5]
    group = 'animation'
    default_value = []

    def __init__(self, type_, metavar, range_=()):
        collections.MutableMapping.__init__(self)
        BaseView.__init__(self)

        self.dt0 = _Dt0()
        self.dt1 = _Dt1()
        self.dv0 = _Dv0(metavar, type_, range_)
        self.dv1 = _Dv1(metavar, type_, range_)
        self.times = _Times()
        self.values = _Values(metavar, type_, range_)
        self.initial_value = _InitialValue(metavar, type_, range_)

        self.handle_pairs = _HandlePairs(self.dt0, self.dt1,
                                         self.dv0, self.dv1)

        self.classes = od([
            ('times', self.times),
            ('values', self.values),
            ('initialValue', self.initial_value),
            ('dt0', self.dt0),
            ('dt1', self.dt1),
            ('dv0', self.dv0),
            ('dv1', self.dv1)])

    def __getitem__(self, item):
        return self.classes[item]

    def __repr__(self):
        return str(self.classes)

    def __len__(self):
        return len(self.classes)

    def __delitem__(self, key):
        del self.classes[key]

    def __iter__(self):
        return iter(self.classes)

    def __setitem__(self, key, value):
        self.classes[key] = value


class _Dt0(BaseView):
    """animation handle pair time offset 0"""

    dest = 'dt0'
    help_ = __doc__
    metavar = positive_meta
    type_ = _Partial(in_range, arg=dest, range_=positive, type_=float)
    versions = [1, 2, 3, 4, 5]
    default_value = []
    nargs = '+'
    depends = ['dt1', 'dv0', 'dv1']


class _Dt1(BaseView):
    """animation handle pair time offset 1"""

    dest = 'dt1'
    help_ = __doc__
    metavar = negative_meta
    type_ = _Partial(in_range, arg=dest, range_=negative, type_=float)
    versions = [1, 2, 3, 4, 5]
    default_value = []
    nargs = '+'
    depends = ['dt0', 'dv0', 'dv1']


class _Dv0(BaseView):
    """animation handle pair value offset 0"""

    dest = 'dv0'
    help_ = __doc__.split('\n')[0]
    nargs = '+'
    default_value = []
    depends = ['dt0', 'dt1', 'dv1']

    def __init__(self, metavar, type_=in_range, range_=()):
        BaseView.__init__(self)
        self.metavar = metavar
        self.type_ = _Partial(type_, arg=self.dest)

        if range_:
            delta = range_[1] - range_[0]
            self.range_ = 0, delta
            self.type_.keywords['range_'] = self.range_


class _Dv1(BaseView):
    """animation handle pair value offset 1"""

    dest = 'dv1'
    help_ = __doc__.split('\n')[0]
    nargs = '+'
    default_value = []
    depends = ['dt0', 'dt1', 'dv0']

    def __init__(self, metavar, type_=in_range, range_=()):
        BaseView.__init__(self)
        self.metavar = metavar
        self.type_ = _Partial(type_, arg=self.dest)

        if range_:
            delta = range_[1] - range_[0]
            self.range_ = -delta, 0
            self.type_.keywords['range_'] = self.range_


class _HandlePairs(BaseView):
    """animation handle pairs

    :param dt0: `_Dt0` instantiated object
    :param dt1: `_Dt1` instantiated object
    :param dv0: `_Dv0` instantiated object
    :param dv1: `_Dv1` instantiated object
    """

    dest = 'handlePairs'
    default_value = []

    def __init__(self, dt0, dt1, dv0, dv1):
        BaseView.__init__(self)
        self.dt0 = dt0
        self.dt1 = dt1
        self.dv0 = dv0
        self.dv1 = dv1


class _InitialValue(BaseView):
    """animation initial value at t=0.0"""

    dest = 'initialValue'
    help_ = __doc__.split('\n')[0]
    alt = 'I'

    def __init__(self, metavar, type_=in_range, range_=()):
        BaseView.__init__(self)
        self.metavar = metavar
        self.range_ = range_
        self.type_ = _Partial(type_, arg=self.dest)
        if range_:
            self.type_.keywords['range_'] = range_


class _Times(BaseView):
    """animation times omitting t=0.0 """

    dest = 'times'
    help_ = __doc__
    metavar = positive_meta
    versions = [1, 2, 3, 4, 5]
    unique = True
    default_value = []
    alt = 'T'
    nargs = '+'

    type_ = _Partial(unsigned_number, arg=dest)
    type_t0 = _Partial(type_, arg='t0')
    type_t1 = _Partial(type_, arg='t1')
    type_scale = _Partial(type_, arg='scale_time')


class _Values(BaseView):
    """animation values omitting t=0.0"""

    dest = 'values'
    help_ = __doc__.split('\n')[0]
    nargs = '+'
    alt = 'V'
    default_value = []

    def __init__(self, metavar, type_=in_range, range_=()):
        BaseView.__init__(self)
        self.metavar = metavar
        self.range_ = range_

        self.type_ = _Partial(type_, arg=self.dest)
        self.type_v0 = _Partial(type_, arg='v0')
        self.type_v1 = _Partial(type_, arg='v1')
        self.type_scale = _Partial(type_, arg='scale_value')

        if range_:
            self.type_.keywords['range_'] = range_
            self.type_v0.keywords['range_'] = range_
            self.type_v1.keywords['range_'] = range_
            self.type_scale.keywords['range_'] = range_


class ViewAperture(BaseView):
    """image depth of field, specified as normalized aperture diameter

    parameter   : viewAperture
    type        : float
    min         : n/a
    max         : n/a
    default     : 1.0
    """

    dest = 'viewAperture'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = '4D-to-2D'
    default_value = 1.0
    animation = _Animation(type_, metavar)
    doc = __doc__


class ViewBlacks(BaseView):
    """corresponds to crs:Blacks2012

    parameter   : viewBlacks
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewBlacks'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2]
    group = 'basicTone'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewBlacks2(BaseView):
    """corresponds to crs:Blacks2012

    parameter   : viewBlacks2
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewBlacks2'
    versions = [3, 4, 5]
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    group = 'basicTone'
    default_value = 0
    ver = True
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewCcm(BaseView):
    """row major; if not specified, a system-computed ccm is used

    parameter   : viewCcm
    type        : float
    min         : n/a
    max         : n/a
    default     : null
    min items   : 9
    max items   : 9
    """

    dest = 'viewCcm'
    help_ = __doc__
    nargs = 9
    min_items = 9
    max_items = 9
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [4, 5]
    group = 'ccm'
    default_value = None


class ViewColorNoiseReduction(BaseView):
    """corresponds to crs:ColorNoiseReduction

    parameter   : viewColorNoiseReduction
    type        : integer
    min         : 0
    max         : +100
    default     : 50
    """

    dest = 'viewColorNoiseReduction'
    help_ = __doc__
    range_ = unsigned_int_100
    metavar = unsigned_int_100_meta
    versions = [1, 2, 3, 4, 5]
    group = '2D-denoise'
    default_value = 50
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewContrast(BaseView):
    """corresponds to crs:Contrast2012

    parameter   : viewContrast
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewContrast'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2, 3, 4, 5]
    group = 'contrast'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewCrop(BaseView):
    """corresponds to crs:HasCrop

    parameter   : viewCrop
    properties  : angle, top, left, bottom, right
    type        : float

    angle
        default : 0.0
        min     : -45.0
        max     : +45.0

    top, left
        default : 0.0
        min     : n/a
        max     : n/a

    bottom, right
        default : 1.0
        min     : n/a
        max     : n/a
    """

    dest = 'viewCrop'
    help_ = __doc__
    _Partial(number, arg=dest)
    metavar = float_meta
    versions = [1, 2, 3, 4, 5]
    group = 'crop'

    class Angle(BaseView):
        """corresponds to crs:CropAngle"""
        dest = 'angle'
        range_ = (-45.0, 45.0)
        metavar = meta_range(range_)
        help_ = __doc__
        default_value = 0.0
        type_ = _Partial(in_range, arg=dest, range_=range_, type_=float)

    class Crop(BaseView):
        """corresponds to crs:Crop

        :param dest: `str`, property name
        :param dest: `float`, default property value
        """

        def __init__(self, dest, default=0.0):
            BaseView.__init__(self)
            self.type_ = _Partial(number, arg=dest)
            self.help_ = self.__doc__ + dest.title()
            self.dest = dest
            self.default_value = default

    angle = Angle()
    top = Crop('top')
    left = Crop('left')
    bottom = Crop('bottom', default=1.0)
    right = Crop('right', default=1.0)
    crop = od([
        ('angle', angle),
        ('top', top),
        ('left', left),
        ('bottom', bottom),
        ('right', right)])


class ViewDefringe(BaseView):
    """enable reduction in fringe artifacts

    parameter   : viewDefringe
    type        : bool
    min         : false
    max         : true
    default     : false
    """

    dest = 'viewDefringe'
    help_ = __doc__
    action = 'store_true'
    type_ = _Partial(boolean, arg=dest)
    versions = [4, 5]
    default_value = False
    group = 'defringe'


class ViewDefringeRadius(BaseView):
    """pixel radius of fringe-reduction region

    parameter   : viewDefringeRadius
    type        : float
    min         : 0.0
    max         : 10.0
    default     : 5.5
    """

    dest = 'viewDefringeRadius'
    help_ = __doc__
    metavar = unsigned_10_meta
    range_ = unsigned_10
    versions = [4, 5]
    group = 'defringe'
    default_value = 5.5
    type_ = _Partial(in_range, arg=dest, range_=range_, type_=float)
    animation = _Animation(type_, metavar, range_)


class ViewDefringeThreshold(BaseView):
    """threshold at which fringe reduction begins

    parameter   : viewDefringeThreshold
    type        : int
    min         : 0
    max         : +100
    default     : 50
    """

    dest = 'viewDefringeThreshold'
    help_ = __doc__
    range_ = unsigned_int_100
    metavar = unsigned_int_100_meta
    versions = [4, 5]
    group = 'defringe'
    default_value = 50
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewExposure(BaseView):
    """corresponds to crs:Exposure2012

    parameter   : viewExposure
    type        : float
    min         : -5.0
    max         : +5.0
    default     : 0.0
    """

    dest = 'viewExposure'
    help_ = __doc__
    range_ = signed_5
    metavar = signed_5_meta
    versions = [1, 2, 3, 4, 5]
    group = 'exposure'
    default_value = 0.0
    type_ = _Partial(in_range, arg=dest, range_=range_, type_=float)
    animation = _Animation(type_, metavar, range_)


class ViewFilterEffect(BaseView):
    """Lytro-specific living filters, no correspondence to crs

    !NOTE: DEFINED IN LFP SCHEMA BUT NOT CURRENTLY IN USE;
    USING THIS PARAMETER WILL HAVE NO AFFECT ON IMAGE OUTPUT

    parameter   : viewFilterEffect
    choices     : none, Mosaic, Glass, Carnival, Line Art, Crayon, Blur+,
                  Pop, Film Noir, 8-Track
    default     : null
    """

    choices = ['none', 'Mosaic', 'Glass', 'Carnival', 'Line Art',
               'Crayon', 'Blur+', 'Pop', 'Film Noir', '8-Track']
    dest = 'viewFilterEffect'
    help_ = __doc__
    type_ = _Partial(choice, choices=choices, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = 'effect'
    default_value = 'none'
    enabled = False


class ViewFocus(BaseView):
    """adjust picture focus; depth of focal plane at FNC [0.5, 0.5]

    parameter   : viewFocus
    type        : float
    min         : n/a
    max         : n/a
    default     : 0.0
    """

    dest = 'viewFocus'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = '4D-to-2D'
    animation = _Animation(type_, metavar)
    default_value = 0.0


class ViewFocusSpread(BaseView):
    """spread image depth of field, as lambda added both near and far

    parameter   : viewFocusSpread
    type        : float
    min         : n/a
    max         : n/a
    default     : 0.0
    """

    dest = 'viewFocusSpread'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = '4D-to-2D'
    default_value = 0.0
    animation = _Animation(type_, metavar)


class ViewFocusX(BaseView):
    """x coordinate in FNC of the location for which viewFocus is specified

    parameter   : viewFocusX
    type        : float
    depends     : viewFocusY
    min         : n/a
    max         : n/a
    default     : 0.5
    """

    dest = 'viewFocusX'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [4, 5]
    group = '4D-to-2D'
    animation = _Animation(type_, metavar)
    depends = ['viewFocusY']
    default_value = 0.5


class ViewFocusY(BaseView):
    """y coordinate in FNC of the location for which viewFocus is specified

    parameter   : viewFocusY
    type        : float
    depends     : viewFocusX
    min         : n/a
    max         : n/a
    default     : 0.5
    """

    dest = 'viewFocusY'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [4, 5]
    group = '4D-to-2D'
    animation = _Animation(type_, metavar)
    depends = ['viewFocusX']
    default_value = 0.5


class ViewFx(BaseView):
    """effects applied after most other view parameters have been processed

    !NOTE: DEFINED IN LFP SCHEMA BUT CURRENTLY NOT COMPATIBLE WITH
    LYTRO POWER TOOLS.

    parameter   : viewFx
    default     : null
    """

    dest = 'viewFx'
    help_ = __doc__
    versions = [5]
    group = 'effects'
    default_value = {'fxEnable': True, 'fxContainerSequence': []}
    enabled = False
    type_ = type_type


class ViewHighlights(BaseView):
    """corresponds to crs:Highlights2012

    parameter   : viewHighlights
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewHighlights'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2]
    group = 'basicTone'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewHighlights2(BaseView):
    """corresponds to crs:Highlights2012

    parameter   : viewHighlights2
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewHighlights2'
    versions = [3, 4, 5]
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    group = 'basicTone'
    default_value = 0
    ver = True
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewLuminanceNoiseReduction(BaseView):
    """corresponds to crs:LuminanceSmoothing

    parameter   : viewLuminanceNoiseReduction
    type        : integer
    min         : 0
    max         : +100
    default     : 50
    """

    dest = 'viewLuminanceNoiseReduction'
    help_ = __doc__
    range_ = unsigned_int_100
    metavar = unsigned_int_100_meta
    versions = [1, 2, 3, 4, 5]
    group = '2D-denoise'
    default_value = 50
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewLuminanceToneCurve(BaseView):
    """array of x/y points defining a tone curve

    parameter   : viewLuminanceToneCurve
    properties  : controlPoint
    type        : float

    controlPoint
        default : []

        x, y
            default : null
            min     : n/a
            max     : n/a

    """

    dest = 'viewLuminanceToneCurve'
    help_ = __doc__
    versions = [1, 2, 3, 4, 5]
    group = 'contrast'

    class Point(BaseView):
        """luminance tone curve array point """

        def __init__(self, dest, depends):
            BaseView.__init__(self)
            self.help_ = self.__doc__ + dest.title()
            self.required = True
            self.nargs = '+'
            self.type_ = _Partial(number, arg=dest)
            self.dest = dest
            self.depends = depends
            self.enabled = False
            self.default = ()

    class ControlPoint(BaseView):
        """luminance tone curve control point sub-property"""
        dest = 'controlPoint'
        enabled = False

    x = Point('x', ['y'])
    y = Point('y', ['x'])
    control_point = ControlPoint()
    luminance_tone_curve = od([('x', x), ('y', y)])
    default_value = [{'x': 0.0, 'y': 0.0}, {'x': 1.0, 'y': 1.0}]
    enabled = False


class ViewOrientation(BaseView):
    """standard EXIF rotations and reflections

    parameter   : viewOrientation
    type        : integer
    choices     : 1, 2, 3, 4, 5, 6, 7, 8
    default     : 1
    """

    choices = range(1, 9)
    dest = 'viewOrientation'
    help_ = __doc__
    metavar = meta_range((1, 8))
    type_ = _Partial(choice, choices=choices, arg=dest, convert=int)
    versions = [1, 2, 3, 4, 5]
    group = 'reorient'
    default_value = 1


class ViewPanX(BaseView):
    """position in RNC of the center of the window

    parameter   : viewPanX
    type        : float
    depends     : viewPanY
    min         : n/a
    max         : n/a
    default     : 0.5
    """

    dest = 'viewPanX'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = 'window'
    default_value = 0.5
    animation = _Animation(type_, metavar)
    depends = ['viewPanY']


class ViewPanY(BaseView):
    """position in RNC of the center of the window

    parameter   : viewPanY
    type        : float
    depends     : viewPanX
    min         : n/a
    max         : n/a
    default     : 0.5
    """

    dest = 'viewPanY'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = 'window'
    default_value = 0.5
    animation = _Animation(type_, metavar)
    depends = ['viewPanX']


class ViewParametricDarks(BaseView):
    """corresponds to crs:ParametricDarks

    !NOTE: DEFINED IN LFP SCHEMA BUT NOT CURRENTLY IN USE;
    USING THIS PARAMETER WILL HAVE NO AFFECT ON IMAGE OUTPUT

    parameter   : viewParametricDarks
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewParametricDarks'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2, 3, 4, 5]
    group = 'parametricTone'
    default_value = 0
    enabled = False
    type_ = _Partial(in_range, arg=dest, range_=range_)


class ViewParametricHighlightSplit(BaseView):
    """corresponds to crs:ParametricHighlightSplit

    !NOTE: DEFINED IN LFP SCHEMA BUT NOT CURRENTLY IN USE;
    USING THIS PARAMETER WILL HAVE NO AFFECT ON IMAGE OUTPUT

    parameter   : viewParametricHighlightSplit
    type        : integer
    min         : +30
    max         : +90
    default     : null
    """

    dest = 'viewParametricHighlightSplit'
    help_ = __doc__
    range_ = (30, 90)
    metavar = meta_range(range_)
    versions = [1, 2, 3, 4, 5]
    group = 'parametricTone'
    default_value = None
    enabled = False
    type_ = _Partial(in_range, arg=dest, range_=range_)


class ViewParametricHighlights(BaseView):
    """corresponds to crs:ParametricHighlights

    !NOTE: DEFINED IN LFP SCHEMA BUT NOT CURRENTLY IN USE;
    USING THIS PARAMETER WILL HAVE NO AFFECT ON IMAGE OUTPUT

    parameter   : viewParametricHighlights
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewParametricHighlights'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2, 3, 4, 5]
    group = 'parametricTone'
    default_value = 0
    enabled = False
    type_ = _Partial(in_range, arg=dest, range_=range_)


class ViewParametricLights(BaseView):
    """corresponds to crs:ParametricLights

    !NOTE: DEFINED IN LFP SCHEMA BUT NOT CURRENTLY IN USE;
    USING THIS PARAMETER WILL HAVE NO AFFECT ON IMAGE OUTPUT

    parameter   : viewParametricLights
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewParametricLights'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2, 3, 4, 5]
    group = 'parametricTone'
    default_value = 0
    enabled = False
    type_ = _Partial(in_range, arg=dest, range_=range_)


class ViewParametricMidtoneSplit(BaseView):
    """corresponds to crs:ParametricMidtoneSplit"

    !NOTE: DEFINED IN LFP SCHEMA BUT NOT CURRENTLY IN USE;
    USING THIS PARAMETER WILL HAVE NO AFFECT ON IMAGE OUTPUT

    parameter   : viewParametricMidtoneSplit
    type        : integer
    min         : +20
    max         : +80
    default     : null
    """

    dest = 'viewParametricMidtoneSplit'
    help_ = __doc__
    range_ = (20, 80)
    metavar = meta_range(range_)
    versions = [1, 2, 3, 4, 5]
    group = 'parametricTone'
    default_value = None
    enabled = False
    type_ = _Partial(in_range, arg=dest, range_=range_)


class ViewParametricShadowSplit(BaseView):
    """corresponds to crs:ParametricShadowSplit

    !NOTE: DEFINED IN LFP SCHEMA BUT NOT CURRENTLY IN USE;
    USING THIS PARAMETER WILL HAVE NO AFFECT ON IMAGE OUTPUT

    parameter   : viewParametricShadowSplit
    type        : integer
    min         : +10
    max         : +70
    default     : null
    """

    dest = 'viewParametricShadowSplit'
    help_ = __doc__
    range_ = (10, 70)
    metavar = meta_range(range_)
    versions = [1, 2, 3, 4, 5]
    group = 'parametricTone'
    default_value = None
    enabled = False
    type_ = _Partial(in_range, arg=dest, range_=range_)


class ViewParametricShadows(BaseView):
    """corresponds to crs:ParametricShadows

    !NOTE: DEFINED IN LFP SCHEMA BUT NOT CURRENTLY IN USE;
    USING THIS PARAMETER WILL HAVE NO AFFECT ON IMAGE OUTPUT

    parameter   : viewParametricParametricShadows
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewParametricShadows'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2, 3, 4, 5]
    group = 'parametricTone'
    default_value = 0
    enabled = False
    type_ = _Partial(in_range, arg=dest, range_=range_)


class ViewPerspectiveU(BaseView):
    """center-of-perspective U coordinate

    parameter   : viewPerspectiveU
    type        : float
    depends     : viewPerspectiveV
    min         : n/a
    max         : n/a
    default     : 0.0
    """

    dest = 'viewPerspectiveU'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = '4D-to-2D'
    default_value = 0.0
    animation = _Animation(type_, metavar)
    depends = ['viewPerspectiveV']


class ViewPerspectiveV(BaseView):
    """center-of-perspective V coordinate

    parameter   : viewPerspectiveV
    type        : float
    depends     : viewPerspectiveU
    min         : n/a
    max         : n/a
    default     : 0.0
    """

    dest = 'viewPerspectiveV'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = '4D-to-2D'
    default_value = 0.0
    animation = _Animation(type_, metavar)
    depends = ['viewPerspectiveU']


class ViewPivot(BaseView):
    """distance at which objects are stationary under perspective change

    parameter   : viewPivot
    type        : float
    min         : n/a
    max         : n/a
    default     : 0.0
    """

    dest = 'viewPivot'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = '4D-to-2D'
    default_value = 0.0
    animation = _Animation(type_, metavar)


class ViewPriorities(BaseView):
    """priority for players that cannot completely honor the recipe

    parameter   : viewPriorities
    :type       : list
    choices     : viewFocus, viewPerspective
    default     : ['viewFocus']
    """

    choices = ['viewFocus', 'viewPerspective']
    dest = 'viewPriorities'
    help_ = __doc__
    type_ = _Partial(choice, choices=choices, arg=dest)
    unique = True
    max_items = 2
    nargs = '+'
    versions = [1, 2, 3, 4, 5]
    group = 'priority'
    default_value = ['viewFocus']


class ViewReduceFlare(BaseView):
    """no direct crs correspondence; reduces lens flare

    !NOTE: DEFINED IN LFP SCHEMA BUT NOT CURRENTLY IN USE;
    USING THIS PARAMETER WILL HAVE NO AFFECT ON IMAGE OUTPUT

    parameter   : viewReduceFlare
    type        : bool
    min         : false
    max         : true
    default     : false
    """

    dest = 'viewReduceFlare'
    help_ = __doc__
    action = 'store_true'
    type_ = _Partial(boolean, arg=dest)
    versions = [4, 5]
    group = '4D-to-2D'
    enabled = False
    default_value = False


class ViewSaturation(BaseView):
    """corresponds to crs:Saturation

    parameter   : viewSaturation
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewSaturation'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2, 3, 4, 5]
    group = 'saturate'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewSaturationBlue(BaseView):
    """corresponds to crs:SaturationAdjustmentBlue

    parameter   : viewSaturationBlue
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewSaturationBlue'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [2, 3, 4, 5]
    group = 'saturate'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewSaturationCyan(BaseView):
    """no direct crs correspondence; candidates: orange, aqua, purple

    parameter   : viewSaturationCyan
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewSaturationCyan'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [2, 3, 4, 5]
    group = 'saturate'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewSaturationGreen(BaseView):
    """corresponds to crs:SaturationAdjustmentGreen

    parameter   : viewSaturationGreen
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewSaturationGreen'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [2, 3, 4, 5]
    group = 'saturate'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewSaturationMagenta(BaseView):
    """corresponds to crs:SaturationAdjustmentMagenta

    parameter   : viewSaturationMagenta
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewSaturationMagenta'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [2, 3, 4, 5]
    group = 'saturate'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewSaturationRed(BaseView):
    """corresponds to crs:SaturationAdjustmentRed

    parameter   : viewSaturationRed
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewSaturationRed'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [2, 3, 4, 5]
    group = 'saturate'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewSaturationYellow(BaseView):
    """corresponds to crs:SaturationAdjustmentYellow

    parameter   : viewSaturationYellow
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewSaturationYellow'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [2, 3, 4, 5]
    group = 'saturate'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewShadows(BaseView):
    """corresponds to crs:Shadows2012

    parameter   : viewShadows
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewShadows'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2]
    group = 'basicTone'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewShadows2(BaseView):
    """corresponds to crs:Shadows2012

    parameter   : viewShadows2
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewShadows2'
    versions = [3, 4, 5]
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    group = 'basicTone'
    default_value = 0
    ver = True
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewSharpenDetail(BaseView):
    """corresponds to crs:SharpenDetail

    parameter   : viewSharpenDetail
    type        : int
    min         : 0
    max         : +100
    default     : 0
    """

    dest = 'viewSharpenDetail'
    help_ = __doc__
    range_ = unsigned_int_100
    metavar = unsigned_int_100_meta
    versions = [3, 4, 5]
    group = 'sharpen'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewSharpenEdgeMasking(BaseView):
    """corresponds to crs:SharpenEdgeMasking

    parameter   : viewSharpenEdgeMasking
    type        : integer
    min         : 0
    max         : +100
    default     : 0
    """

    dest = 'viewSharpenEdgeMasking'
    help_ = __doc__
    range_ = unsigned_int_100
    metavar = unsigned_int_100_meta
    versions = [3, 4, 5]
    group = 'sharpen'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewSharpenRadius(BaseView):
    """corresponds to crs:SharpenRadius

    parameter   : viewSharpenRadius
    type        : float
    min         : +0.5
    max         : +3.0
    default     : 1.0
    """

    dest = 'viewSharpenRadius'
    help_ = __doc__
    range_ = (0.5, 3.0)
    metavar = meta_range(range_)
    versions = [1, 2, 3, 4, 5]
    group = 'sharpen'
    default_value = 1.0
    type_ = _Partial(in_range, arg=dest, range_=range_, type_=float)
    animation = _Animation(type_, metavar, range_)


class ViewSharpness(BaseView):
    """corresponds to crs:Sharpness

    parameter   : viewSharpness
    type        : integer
    min         : 0
    max         : +150
    default     : 25
    """

    dest = 'viewSharpness'
    help_ = __doc__
    range_ = unsigned_int_150
    metavar = unsigned_int_150_meta
    versions = [1, 2]
    group = 'sharpen'
    default_value = 25
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewSharpness2(BaseView):
    """corresponds to crs:Sharpness

    parameter   : viewSharpness2
    type        : integer
    min         : 0
    max         : +150
    default     : 25
    """

    dest = 'viewSharpness2'
    versions = [3, 4, 5]
    help_ = __doc__
    range_ = unsigned_int_150
    metavar = unsigned_int_150_meta
    group = 'sharpen'
    default_value = 25
    ver = True
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewStereoBaseline(BaseView):
    """full length of stereo baseline

    parameter   : viewStereoBaseline
    type        : float
    min         : 0.0
    max         : n/a
    default     : 0.0
    """

    dest = 'viewStereoBaseline'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(unsigned_number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = '4D-to-2D'
    default_value = 0.0
    animation = _Animation(type_, metavar)


class ViewStereoPivot(BaseView):
    """stereo distance at which objects are stationary under perspective change

    parameter   : viewStereoPivot
    type        : float
    min         : n/a
    max         : n/a
    default     : 0.0
    """

    dest = 'viewStereoPivot'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = '4D-to-2D'
    default_value = 0.0
    animation = _Animation(type_, metavar)


class ViewTemperature(BaseView):
    """corresponds to crs:Temp; estimated if not specified

    parameter   : viewTemperature
    type        : integer
    min         : +2000
    max         : +50000
    default     : null
    """

    dest = 'viewTemperature'
    help_ = __doc__
    range_ = (2000, 50000)
    metavar = meta_range(range_)
    versions = [1, 2, 3, 4, 5]
    group = 'white-balance'
    default_value = None
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewTiltX(BaseView):
    """signed change in lambda from left to right image edges, in FNC

    parameter   : viewTiltX
    type        : float
    depends     : viewTiltY
    min         : n/a
    max         : n/a
    default     : 0.0
    """

    dest = 'viewTiltX'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = '4D-to-2D'
    animation = _Animation(type_, metavar)
    depends = ['viewTiltY']
    default_value = 0.0


class ViewTiltY(BaseView):
    """signed change in lambda from top to bottom image edges, in FNC

    parameter   : viewTiltY
    type        : float
    depends     : viewTiltX
    min         : n/a
    max         : n/a
    default     : 0.0
    """

    dest = 'viewTiltY'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = '4D-to-2D'
    animation = _Animation(type_, metavar)
    depends = ['viewTiltX']
    default_value = 0.0


class ViewTint(BaseView):
    """corresponds to crs:Tint

    parameter   : viewTint
    type        : integer
    min         : -150
    max         : +150
    default     : 0
    """

    dest = 'viewTint'
    help_ = __doc__
    range_ = signed_int_150
    metavar = signed_int_150_meta
    versions = [1, 2, 3, 4, 5]
    group = 'white-balance'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewVibrance(BaseView):
    """corresponds to crs:Vibrance

    parameter   : viewVibrance
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewVibrance'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2, 3, 4, 5]
    group = 'saturate'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewWhiteBalance(BaseView):
    """corresponds to crs:WhiteBalance

    parameter   : viewWhiteBalance
    choices     : as shot, auto, custom, daylight, cloudy, flash, fluorescent,
                  shade, tungsten
    default     : auto
    """

    choices = ['as shot', 'auto', 'daylight', 'cloudy', 'shade',
               'tungsten', 'fluorescent', 'flash', 'custom']
    dest = 'viewWhiteBalance'
    help_ = __doc__
    type_ = _Partial(choice, choices=choices, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = 'white-balance'
    default_value = 'auto'


class ViewWhites(BaseView):
    """corresponds to crs:Whites2012

    parameter   : viewWhites
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewWhites'
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    versions = [1, 2]
    group = 'basicTone'
    default_value = 0
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewWhites2(BaseView):
    """corresponds to crs:Whites2012

    parameter   : viewWhites2
    type        : integer
    min         : -100
    max         : +100
    default     : 0
    """

    dest = 'viewWhites2'
    versions = [3, 4, 5]
    help_ = __doc__
    range_ = signed_int_100
    metavar = signed_int_100_meta
    group = 'basicTone'
    default_value = 0
    ver = True
    type_ = _Partial(in_range, arg=dest, range_=range_)
    animation = _Animation(type_, metavar, range_)


class ViewZoom(BaseView):
    """scale factor from RNC to WNC

    parameter   : viewZoom
    type        : float
    min         : n/a
    max         : n/a
    default     : 1.0
    """

    dest = 'viewZoom'
    help_ = __doc__
    metavar = float_meta
    type_ = _Partial(number, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = 'window'
    animation = _Animation(type_, metavar)
    default_value = 1.0


class ZuluTime(BaseView):
    """time stamp for the last modification to this recipe

    parameter   : viewZoom
    type        : datetime string, '%Y-%m-%dT%H:%M:%S.%fZ'
    default     : none
    """

    dest = 'zuluTime'
    help_ = __doc__
    type_ = _Partial(argutils.zulu_time, arg=dest)
    versions = [1, 2, 3, 4, 5]
    group = 'meta'
    default_value = None


class Params(object):
    """Recipe Tool view parameters

    stores and provides parameter value meta information
    """

    _version = config.db['recipe_version']

    def __init__(self):

        self.animation = _Animation(float, positive_meta)
        self.ccm = None
        self.crop = None
        self.luminance_tone_curve = None
        self.fx = None
        self.priorities = None
        self.zulu_time = None

        [setattr(self, cls.key_cls, cls) for cls in self._globals]

    @property
    def _globals(self):
        """global params items"""

        items = globals().items()
        items.sort()

        for key, cls in items:
            if not (key.startswith('View') or key == 'ZuluTime'):
                continue
            yield cls()

    @property
    def dependencies(self):
        """yield all parameter dependencies"""

        for attr in self._globals:
            if attr.depends:
                yield attr.key_cls, attr.depends

    def dests(self, cls=False, enabled=False, exclude=(), grouped=False,
              include_animation=False, meta=False, version=_version):
        """filter for destinations in params classes

        :param cls: `bool`, return cls format for returned strings
        :param enabled: `bool`, return parameters that are enabled
        :param exclude: `iter`, list of destination names to exclude
        :param grouped: `bool`, return parameters by group type
        :param include_animation: `bool`, include animation parameter strings
        :param meta: `bool`, include meta group
        :param version: `int`, filter by recipe version
        :return: filtered destinations
        """

        _group_dests = {}

        for attr in self._globals:

            group = attr.group

            dest = attr.key_cls if cls else attr.dest
            anim = '_animation' if cls else 'Animation'

            if dest in exclude:
                continue
            if version not in attr.versions:
                continue
            if enabled and not attr.enabled:
                continue
            if not meta and group == 'meta':
                continue

            if group not in _group_dests:
                _group_dests[group] = []

            _group_dests[group].append(dest)

            if include_animation and attr.animation:
                _group_dests[group].append(dest + anim)

        items = _group_dests.items()
        values = _group_dests.values()

        [v.sort() for v in values]

        group_dests = od(sorted(items))
        all_dests = sorted([dest for group in values for dest in group])

        return group_dests if grouped else all_dests

    @staticmethod
    def set_global_auto_correct(correct=True):
        """globally set auto correct for out-of-range values

        :param correct: `bool`, enable/disable auto-correct
        """

        global auto_correct
        auto_correct = correct

    @staticmethod
    def set_global_help(print_help):
        """sets global lpt argparse help menu for current command

        :param print_help: `object`, passed to ToolError for command help menu
        """
        global print_help_obj
        print_help_obj = print_help

        argutils.set_print_help(print_help)
