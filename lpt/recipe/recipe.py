# -*- coding: utf-8 -*-
"""Lytro Power Tools - recipe package - recipe file modifier"""

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
import copy
from functools import partial

from lpt.recipe import config
from lpt.recipe.params import Params
from lpt.utils.argutils import ArgUtils
from lpt.utils.jsonutils import JsonUtils
from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.utils.msgutils import ToolWarn
from lpt.utils.utils import Utils

utils = Utils()
params = Params()
argutils = ArgUtils()
msgutils = MsgUtils()
jsonutils = JsonUtils()

od = collections.OrderedDict
all_or_none = argutils.all_or_none
arg_format = argutils.arg_format

all_ = partial(utils.all_, iter_=False)
any_ = partial(utils.any_, iter_=False)
dumps = partial(msgutils.dumps, answer=True, sort_keys=False)
key_cls = partial(arg_format, camel=True, rm='view', join='_', ver=True)
flatten = partial(utils.flatten, iter_=False)
print_help_obj = object


class Recipe(collections.MutableMapping):
    """class for direct manipulation with LFP recipe files

    * view parameter meta information is loaded from `params.Params`; this
      meta information is used as a rule system to define `Recipe` view
      parameter objects, including:

        parameter name
        range
        value type
        dependencies
        default value
        etc...

    * each parameter is stored as a class in `self`:

        ``self.saturation``
        ``self.perspective_u``
        ``self.crop``
          etc...

    * for parameters that have sub-properties, their child properties are
      accessible as subclasses to the parent:

         ``self.crop.bottom``
         ``self.crop.angle``
           etc...

    * for parameters that can animate, an additional class is stored:

        ``self.saturation_animation``
        ``self.perspective_u_animation``
          etc...

    * all parameters that can animate have a special set of sub-properties:

        ``self.perspective_u_animation.times``
        ``self.perspective_u_animation.values``
        ``self.perspective_u_animation.initial_value``
        ``self.perspective_u_animation.handle_pairs.dt0``
        ``self.perspective_u_animation.handle_pairs.dt1``
        ``self.perspective_u_animation.handle_pairs.dv0``
        ``self.perspective_u_animation.handle_pairs.dv1``

    * a handful of notable shortcuts:

        ``self.perspective_u.anim``:
            ``self.perspective_u_animation``

        ``self.perspective_u.anim.[dt0|dt1|dv0|dv1]``:
            ``self.perspective_u_animation.handle_pairs.[dt0|dt1|dv0|dv1]``

        ``self.perspective_u.anim.[times|values]``:
            ``self.perspective_u_animation.[times|values]``

        ``self.perspective_u_animation.keyframes``:
            parameter animation data presented as keyframes

        ``self.perspective_u_animation.points``:
            parameter animation data presented as x/y (time/value) points

    * all lists and dictionaries are accessible by an index:

        ``self.perspective_u_animation['times']``
        ``self.perspective_u_animation['values']``
        ``self.perspective_u_animation['dt0']``
        ``self.perspective_u_animation.times[0]``
        ``self.perspective_u_animation.values[0]``
        ``self.perspective_u_animation.dt0[0]``
          etc...

    * to set a value, the appropriate path to that value is called:

        ``self.saturation(50)``
        ``self.saturation.anim.values(50)``
          etc...

    * in valid scenarios, values can also be set by value, list, dictionary:

        ``self.saturation.anim.times([1, 2, 3])``
        ``self.saturation.anim.values([50, 55, 60])``
        ``self.saturation.anim.values[3](40)``
        ``self.saturation.anim({'times': [1, 2, 3], 'values': [50, 55, 60]})``
          etc...

    * when a object is called with a value, the value is applied to a "store"
      in that object's class

        ``self.saturation.store``
        ``self.saturation.anim.store``
        ``self.saturation.anim.times.store``
        ``self.saturation.anim.times[1].store``
          etc...

    * the input recipe file is read and the values are loaded into their
      respective classes

    * when flushed (i.e., written to disk), all view parameter stores are read,
      validated, and written

    * !NOTE: as of release 1.0.1, the viewFx parameter is incompatible with
      Lytro Power tools; any viewFx data is stored in ``self.unsupported_data``
      until ``recipe.flush`` is called for the file to be written

    :param path: `str`, path to recipe file
    :param print_help: `object`, passed to ToolError for command help menu
    """

    _parameters = sorted(params.dests(meta=True))
    _schema_dummy = config.schema_dummy
    _schema_file = config.schema_file

    _version = config.db['recipe_version']
    _ver_str = '' if _version == 1 else str(_version)
    _recipe_key = 'recipe{}'.format(_ver_str)

    def __init__(self, path=None, print_help=object):

        self._special = {
            'viewCrop': _DictCrop,
            'viewLuminanceToneCurve': _DictLuminanceToneCurve,
            'viewPriorities': _ListPriorities,
            'viewCcm': _ListCcm,
            'zuluTime': _ObjZuluTime}

        self._unsupported = ['viewFx']
        self.unsupported_data = od([])

        self.set_global_help(print_help)
        self.path = path
        self._anim_store = od()
        self._raw_copy = od()
        self._store = od()
        self.raw_data = od()

        self.init()

        if path:
            self.import_(path)
            self.load()

        self.zulu_time = getattr(self, 'zulu_time', lambda: utils.zulu_time())

    def __call__(self, data=None, recipe_file=None, animate=False):
        """:raise: `ToolError` if invalid view parameter is found in data"""

        _data = {}
        if recipe_file:
            _data.update(jsonutils.data(recipe_file))
        if data:
            _data.update(data)

        for param, value in _data.items():

            if param in self._unsupported:
                self.unsupported_data[param] = value
                continue

            name = key_cls(param)
            e = "invalid parameter: " + param
            assert hasattr(self, name), ToolError(e, print_help_obj)

            cls = getattr(self, name)

            if animate:
                if not cls.animation:
                    continue
                cls = cls.anim

            cls(value)

    def __delitem__(self, index):
        self._store[index].delete()

    def __getitem__(self, index):
        return self._store[index]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def __repr__(self):
        return dumps(self.store)

    def __setitem__(self, key, value):
        self.__call__({key: value})

    @staticmethod
    def set_global_help(print_help):
        """sets global lpt argparse help menu for current command

        :param print_help: `object`, passed to ToolError for command help menu
        """

        global print_help_obj
        print_help_obj = print_help

        argutils.set_print_help(print_help)
        utils.set_print_help(print_help)
        jsonutils.set_print_help(print_help)
        params.set_global_help(print_help)

    def _delete(self):
        """deletes all present parameters"""

        [v.delete() for v in self._store.values()]

    def _get_store(self, animation=None, zulu=True):
        """:return: all present parameters"""

        store = od()
        for param, view in self.items():

            if not view.active:
                continue
            if param is 'zuluTime' and not zulu:
                continue

            anim = param.endswith('Animation')

            if animation is False and anim:
                continue
            elif animation is True and not anim:
                continue
            store[param] = view.store

        return od(sorted(store.items()))

    @property
    def animation_store(self):
        """:return: all present animation parameters"""

        return self._get_store(animation=True)

    def dependencies(self):
        """dependency check for all present parameters

        :raise: `ToolError` if dependencies not met
        """

        for name, dependents in params.dependencies:

            view = getattr(self, name)

            if not view.active:
                continue

            for depend in dependents:
                dep_name = key_cls(depend)
                e = "'{}' depends on '{}'".format(name, dep_name)
                assert self[depend].active, ToolError(e, print_help_obj)

            view.dependencies(name)

    @property
    def duration(self):
        """:return: total length of time for the loaded recipe"""

        values = sum(self.points.values(), [])
        min_ = min([t[0] for t in values]) if values else 0
        max_ = max([t[0] for t in values]) if values else 0
        return min_, max_

    def flush(self):
        """validates loaded recipe and writes recipe file to disk

        :raise: `ToolError` if `self.path` is not set"""

        self.dependencies()
        self.validate()
        self.zulu_time()
        e = "recipe output file not set"
        assert self.path, ToolError(e, print_help_obj)
        store = self.store
        store.update(self.unsupported_data)
        utils.write(self.path, od(sorted(store.items())))

    def import_(self, recipe_file):
        """reads input recipe file and loads raw data into `self`

        :param recipe_file: `str`, path to recipe file
        """

        raw_data = jsonutils.data(recipe_file, valid=True)
        self.validate(data=raw_data)
        self.raw_data = raw_data
        self._raw_copy = copy.deepcopy(raw_data)
        self.path = recipe_file

    def init(self):
        """reads view parameter classes and load properties into `self`"""

        for param in self._parameters:
            name = key_cls(param)
            meta = getattr(params, name)

            if param in self._special:
                cls = self._special[param]
                view = cls()
            elif param in self._unsupported:
                continue
            else:
                view = _Obj(meta)

            setattr(self, name, view)
            self._store[param] = view
            view.name = name

            if not meta.animation:
                continue

            anim = _DictAnimation(meta)
            param += 'Animation'
            name = key_cls(param)
            self._store[param] = anim
            self._anim_store[param] = anim
            setattr(self, name, anim)

            view.anim = anim
            anim.view = view
            anim.dt0 = anim.handle_pairs.dt0
            anim.dt1 = anim.handle_pairs.dt1
            anim.dv0 = anim.handle_pairs.dv0
            anim.dv1 = anim.handle_pairs.dv1

    @property
    def keyframes(self):
        """:return: all present animation times/values as keyframes"""

        items = self._anim_store.items()
        return od([(k, v.keyframes) for k, v in items if v.keyframes])

    def load(self):
        """loads imported raw recipe file data into `self`"""

        self.__call__(self.raw_data)

    @property
    def points(self):
        """:return: all present animation times/values as x/y coordinates"""

        items = self._anim_store.items()
        return od([(k, v.points) for k, v in items if v.active])

    @property
    def store(self):
        """:return: all present view and animation parameters"""

        return self._get_store()

    def validate(self, data=()):
        """validates that the recipe being written to file matches Lytro's
        LFP spec for recipe data

        :param data: `dict`, alt data to validate in place of current recipe
        """

        data = data or self.store
        dummy = jsonutils.data(self._schema_dummy)
        dummy['views'][0][self._recipe_key] = data
        jsonutils.validate(dummy, self._schema_file, raise_=True)

    @property
    def view_store(self):
        """:return: all present view parameters"""

        return self._get_store(animation=False)

    @property
    def view_store_no_zulu(self):
        """:return: all present view parameters sans zuluTime"""

        return self._get_store(animation=False, zulu=False)


class _Meta(object):
    """base meta class for pre-instantiation bring-up"""
    type_ = partial(argutils.type_type)
    min_items = 0
    max_items = None
    dest = ''


class _Dict(collections.MutableMapping):
    """dictionary-type class for Recipe

    see ``help(_Dict.meta)`` / ``help(self.meta)`` for parameter attributes

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    def __init__(self, meta=None, index=None, store=None):
        self.meta = meta or _Meta()
        self.index = index if any_(index) else meta.dest
        self._store = store or od()
        self.init()

    def __call__(self, values):

        for key, value in values.items():
            name = key_cls(key, ver=False)
            prop = getattr(self, name)
            prop(value)

    def __delitem__(self, key):
        self._store[key].delete()

    def __getitem__(self, item):
        return self._store[item]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def __repr__(self):
        return dumps(self.store)

    def __setitem__(self, key, value):
        self._store[key] = value

    @property
    def active(self):
        """:return: True if `self._store` contains any items, else False"""

        for index, prop in self._store.items():
            if prop.active:
                return True
        return False

    def arrange(self):
        """maps internal value (`self._store`) to external value (`self.store`)

        *this can be a slow operation on objects containing a lot of data*
        """

        [v.arrange() for v in self._store.values()]

    def delete(self):
        """resets current object's items to empty values"""

        [self.__delitem__(k) for k in self._store.keys()]

    def dependencies(self, parent):
        """validates that the current object's recipe dependencies are met

        :param parent: `str`,  object name containing the current _Dict
        :raise: `ToolError` if dependencies not met
        """

        def path(x): return '.'.join([parent, key_cls(x, ver=False)])

        for param, prop in self.items():
            if not prop.active:
                continue

            name = path(param)

            for depend in prop.meta.depends:
                dep_path = path(depend)
                e = "'{}' depends on '{}'".format(name, dep_path)
                assert self[depend].active, ToolError(e, print_help_obj)

            prop.dependencies(name)

    def init(self):
        """resets object's internal values"""

        for key, value in self._store.items():
            name = key_cls(key)
            setattr(self, name, value)

    @property
    def store(self):
        """:return: external/user-accessible value for the current object"""

        items = self.items()

        def key(x): return x.store if hasattr(x, 'store') else x
        return od([(key(k), v.store) for k, v in items if v.active])

    def update(*args, **kwds):
        """changes values in current dictionary

        :param args: `tuple`, positional args passed to `self.__call__`
        :param kwds: `dict`, keyword args passed to `self.__call__`
        """

        call = args[0].__call__
        [call(arg) for arg in args[1:]]
        call(kwds)


class _DictAnimation(_Dict):
    """dictionary type object to store animation properties

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    _od = od([
        ('times', []),
        ('values', []),
        ('handlePairs', []),
        ('initialValue', None)])

    def __init__(self, meta, index='', store=od()):
        anim = meta.animation
        _od = od(copy.deepcopy(self._od))
        _od.update(store)

        self.times = _ListTimes(
            meta=anim.times,
            store=_od['times'])

        self.values = _ListValues(
            meta=anim.values,
            store=_od['values'])

        self.initial_value = _ObjInitialValue(
            meta=anim.initial_value,
            store=_od['initialValue'])

        self.handle_pairs = _ListHandlePairs(
            meta=anim.handle_pairs,
            store=_od['handlePairs'])

        store = od([
            ('times', self.times),
            ('values', self.values),
            ('initialValue', self.initial_value),
            ('handlePairs', self.handle_pairs)])

        self.keyframes = _ListKeyframes(store, dest=meta.dest)
        self.keyframe = self.keyframes.keyframe

        _Dict.__init__(self, meta=meta, index=index, store=store)

    @property
    def points(self):
        """:return: all present animation times/values as x/y coordinates"""

        return self.keyframes.points

    @property
    def x_points(self):
        """:return: all present animation times as x coordinates"""

        return self.keyframes.x

    @property
    def y_points(self):
        """:return: all present animation values as y coordinates"""

        return self.keyframes.y


class _DictControlPoint(_Dict):
    """dictionary type object to store controlPoint properties

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = _Meta()
    _od = od([
        ('x', None),
        ('y', None)])

    def __init__(self, meta=meta, index='', store=od()):

        _od = od(copy.deepcopy(self._od))
        x, y = store if isinstance(store, tuple) else (store['x'], store['y'])

        _od['x'] = x
        _od['y'] = y
        self.x = _ObjX(store=_od['x'])
        self.y = _ObjY(store=_od['y'])

        store = od([('x', self.x), ('y', self.y)])
        _Dict.__init__(self, meta=meta, index=index, store=store)

    def __call__(self, *args, **kwargs):
        """:raise: `ToolError` if `args[0]` not a valid control point format"""

        values = args[0]
        if isinstance(values, dict):
            x = values['x']
            y = values['y']
        elif isinstance(values, tuple):
            x, y = values
        else:
            e = "invalid control point format: " + str(values)
            raise ToolError(e, print_help_obj)

        self.x(x)
        self.y(y)


class _DictControlPointLuminanceToneCurve(_DictControlPoint):
    """pass through class for viewLuminanceTone controlPoint objects"""

    meta = params.luminance_tone_curve.control_point


class _DictCrop(_Dict):
    """dictionary type object to store viewCrop properties

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.crop
    _od = od([
        ('angle', None),
        ('top', None),
        ('right', None),
        ('bottom', None),
        ('left', None)])

    def __init__(self, meta=meta, index='', store=od()):
        _od = od(copy.deepcopy(self._od))
        _od.update(store)

        self.angle = _ObjAngle(store=_od['angle'])
        self.top = _ObjTop(store=_od['top'])
        self.left = _ObjLeft(store=_od['left'])
        self.bottom = _ObjBottom(store=_od['bottom'])
        self.right = _ObjRight(store=_od['right'])

        store = od([('angle', self.angle),
                    ('top', self.top),
                    ('left', self.left),
                    ('bottom', self.bottom),
                    ('right', self.right)])
        _Dict.__init__(self, meta=meta, index=index, store=store)


class _DictHandlePair(_Dict):
    """dictionary type object to store animation handlePairs

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    _od = od([
        ('dt0', None),
        ('dt1', None),
        ('dv0', None),
        ('dv1', None)])

    def __init__(self, meta, index='', store=od()):
        _od = od(copy.deepcopy(self._od))
        _od.update(store)

        self.dt0 = _ObjDt0(meta.dt0, store=_od['dt0'])
        self.dt1 = _ObjDt1(meta.dt1, store=_od['dt1'])
        self.dv0 = _ObjDv0(meta.dv0, store=_od['dv0'])
        self.dv1 = _ObjDv1(meta.dv1, store=_od['dv1'])

        store = od([('dt0', self.dt0),
                    ('dt1', self.dt1),
                    ('dv0', self.dv0),
                    ('dv1', self.dv1)])
        _Dict.__init__(self, meta=meta, index=index, store=store)


class _DictKeyframe(_Dict):
    """object to access a single animation keyframe

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    _od = od([
        ('dt0', None),
        ('dv0', None),
        ('times', None),
        ('values', None),
        ('dt1', None),
        ('dv1', None)])

    def __init__(self, meta, index='', store=od()):
        _od = od(copy.deepcopy(self._od))
        _od.update(store)

        def obj(): return _Obj(meta, index)

        self.dt0 = _od['dt0']
        self.dv0 = _od['dv0']
        self.time = _od['times']
        self.value = _od['values']
        self.dt1 = _od['dt1']
        self.dv1 = _od['dv1']

        if not self.dt0:
            self.dt0 = obj()
        if not self.dv0:
            self.dv0 = obj()
        if not self.time:
            self.time = obj()
        if not self.value:
            self.value = obj()
        if not self.dt1:
            self.dt1 = obj()
        if not self.dv1:
            self.dv1 = obj()

        store = od([
            ('dt0', self.dt0),
            ('dv0', self.dv0),
            ('times', self.time),
            ('values', self.value),
            ('dt1', self.dt1),
            ('dv1', self.dv1)])

        _Dict.__init__(self, meta=meta, index=index, store=store)

    @property
    def store(self):
        """return: external/user-accessible value for the current object"""

        dt0 = self.dt0.store
        dt1 = self.dt1.store
        time = self.time.store
        value = self.value.store
        dv0 = self.dv0.store
        dv1 = self.dv1.store

        t_type = self.time.meta.type_
        v_type = self.value.meta.type_

        r_dt0 = r_dt1 = r_dv0 = r_dv1 = None

        if any_(time) and any_(dt0):
            r_dt0 = t_type(time - dt0)
        if any_(time) and any_(dt1):
            r_dt1 = t_type(time - dt1)
        if any_(value) and any_(dv0):
            r_dv0 = v_type(value - dv0)
        if any_(value) and any_(dv1):
            r_dv1 = v_type(value - dv1)

        store = od([
            ('dt0', od([('value', dt0), ('x', r_dt0)])),
            ('dv0', od([('value', dv0), ('y', r_dv0)])),
            ('times', od([('value', time), ('x', time)])),
            ('values', od([('value', value), ('y', value)])),
            ('dt1', od([('value', dt1), ('x', r_dt1)])),
            ('dv1', od([('value', dv1), ('y', r_dv1)]))])

        return store


class _DictLuminanceToneCurve(_Dict):
    """dictionary type object to store viewLuminanceToneCurve properties

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.luminance_tone_curve
    _od = od([('controlPoints', [])])

    def __init__(self, meta=meta, index='', store=od()):
        _od = od(copy.deepcopy(self._od))
        _od.update(store)

        self.control_points = _ListControlPoints(
            store=_od['controlPoints'])

        store = od([('controlPoints', self.control_points)])
        _Dict.__init__(self, meta=meta, index=index, store=store)


class _List(collections.MutableMapping):
    """list-type class for Recipe

    see ``help(_List.meta)`` / ``help(self.meta)`` for parameter attributes

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    :param obj: `object`, object type for list
    """

    def __init__(self, meta=None, index='', store=(), obj=None):
        self.meta = meta or _Meta()
        self.index = index if any_(index) else meta.dest
        self._obj = obj or _Obj
        self._null = None if isinstance(self._obj, _Obj) else od()
        self._store = []
        self._store = self._unitize(store)

    def __call__(self, *args):
        for arg in args:
            self.extend(arg) if isinstance(arg, list) else self.append(arg)

    def __delitem__(self, index):
        self._store[index].delete()

    def __getitem__(self, index):
        """:raise: `ToolError` if index is out of range of `self`"""

        stop = index.stop if isinstance(index, slice) else index

        if stop > self._len:
            if isinstance(index, slice):
                e = "list index out of range: {}".format(stop)
                raise ToolError(e, print_help_obj)
            return None

        if stop is None:
            stop = self._len
        elif stop < 0:
            stop += self._len

        if isinstance(index, slice):
            slice_ = xrange(index.start, stop, index.step or 1)
            return [self._store[s] for s in slice_]
        else:
            return self._store[stop]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def __repr__(self):
        return dumps(self.store)

    def __setitem__(self, index, value, update=False):
        if update and self._store[index].active:
            self._store[index](value)
        else:
            self._store[index] = self._unit(value)

    def _extract(self, start=0, end=None, step=1):
        """:return: extracted `self._store` values"""

        values = self._store.values()[start:end:step]
        return [v.store for v in values if v.active]

    def _init(self):
        """resets object's internal value"""

        self._store = self._od([])

    @property
    def _len(self):
        """length of current object; internal alias for `self.__len__`"""

        return self.__len__()

    def _od(self, lst):
        """wrapper for collections.OrderedDict"""

        unit = self._unit
        null = self._null
        values = self.values()

        def _store(k): return values[k]

        class _Od(collections.OrderedDict):
            # noinspection PyMethodMayBeStatic
            def __missing__(self, key):
                return _store(key) if (values and key < 0) else unit(null)

        return _Od(lst)

    def _unit(self, value):
        """creates a container for a single object in the current list"""

        return self._obj(self.meta, self._len, store=value)

    def _unitize(self, values):
        """converts a list of values to internal units"""

        return self._od([(i, self._unit(v)) for i, v in enumerate(values)])

    @property
    def active(self):
        """:return: True if `self._store` contains any items else False"""

        for prop in self.values():
            if prop.active:
                return True
        return False

    def append(self, value):
        """adds a value to the end of the current list

        :param value: `int`/`float`, value to append
        """

        self.__setitem__(self._len, value)

    def arrange(self):
        """remaps internal value to external value"""

        self._store = self._unitize(self._extract())

    def delete(self):
        """resets current object to an empty value"""

        [self.__delitem__(k) for k in self._store.keys()]

    def dependencies(self, parent):
        """validates that the current object's recipe dependencies are met

        :param parent: `str`,  object name containing the current list
        :raise: `ToolError` if `self` does not meet required length
        """

        for index, obj in self.items():
            name = '.'.join([parent, str(index)])
            obj.dependencies(name)

        min_ = self.meta.min_items
        max_ = self.meta.max_items
        name = key_cls(self.index)

        if self._store and (min_ or max_):
            e = argutils.bad_amt
            e = e.format(arg=name, obj=self._len, min_=min_, max_=max_)
            lt_gt = argutils.lt_gt(self._len, min_, max_)
            assert lt_gt, ToolError(e, print_help_obj)

    def extend(self, value):
        """adds a list of values to the end of the current list

        :param value: `iter`, values to extend
        """

        [self.append(v) for v in value]

    def get(self, index, default=None):
        """retrieves a value based on requested index

        :param index: `int`, position's value to get
        :param default: `object`, not used
        :return: requested index value
        """

        return self[index]

    def insert(self, index, *values):
        """adds a value to the current at the requested index

        *warning: slow operation*

        :param index: `int`, position to insert values at
        :param values: `iter`, values to insert
        """

        self.arrange()
        slice_ = self._extract(index)
        [self.__delitem__(i) for i in range(index, self._len)]
        [self.__setitem__(i, v) for i, v in enumerate(values, start=index)]
        [self.__setitem__(self._len, v) for v in slice_]

    def pop(self, key=-1, default=None):
        """removes and returns a value at the requested index

        *warning: slow operation*

        :param key: `int`, list position to pop
        :param default: `object`, not used
        :return: popped value
        """

        pop = self._store.values()[key]
        self._store.values()[key]()
        self.arrange()
        return pop

    @property
    def store(self):
        """:return: external/user-accessible value for the current object"""

        return self._extract()


class _ListCcm(_List):
    """container for view parameter viewCcm

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.ccm

    def __init__(self, meta=meta, index='', store=()):
        _List.__init__(self, meta=meta, index=index, store=store)


class _ListControlPoints(_List):
    """container for control points (viewLuminanceToneCurve)

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.luminance_tone_curve

    def __init__(self, meta=meta, index='', store=()):
        _List.__init__(self, meta=meta, index=index, store=store,
                       obj=_DictControlPointLuminanceToneCurve)


class _ListHandlePairCoords(collections.MutableMapping):
    """special list for parallel method of accessing handle pair coordinates

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    def __init__(self, index, store, meta):
        self.index = index
        self._store = store
        self._obj = _Obj
        self.meta = meta

    def __call__(self, *args):
        for arg in args:
            self.extend(arg) if isinstance(arg, list) else self.append(arg)

    def __delitem__(self, key):
        self._store[key][self.index].delete()

    def __getitem__(self, item):
        stop = item.stop if isinstance(item, slice) else item

        if stop > self._len:
            if isinstance(item, slice):
                e = "list index out of range: {}".format(stop)
                raise ToolError(e, print_help_obj)
            return None

        if stop is None:
            stop = self._len
        elif stop < 0:
            stop += self._len

        if isinstance(item, slice):
            slice_ = xrange(item.start, stop, item.step or 1)
            return [self._store[s][self.index] for s in slice_]
        else:
            return self._store[stop][self.index]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return dumps(self.store)

    def __setitem__(self, key, value):
        value = {self.index: value}
        self._store.__setitem__(key, value, update=True)

    @property
    def _items(self):
        """internal access to object's indices and values"""

        items = [x[self.index] for x in self._store.values() if x.active]
        return items

    @property
    def _len(self):
        """length of current object; internal alias for `self.__len__`"""

        return self.__len__()

    def _unit(self, value):
        obj = self._obj(self.meta, self._len, store=value)
        return {self.index: obj}

    def append(self, value):
        """adds a value to the end of the current list

        :param value: `int`/`float`, value to append
        """

        self.__setitem__(self._len, value)

    def arrange(self, key):
        """maps internal value (self._store) to external value (`self.store`)

        :param key: `str`, handlePair param to arrange
        """

        self._store[key].arrange()

    def delete(self):
        """resets current object's items to empty values"""

        [self.__delitem__(k) for k in self._store.keys()]

    def extend(self, value):
        """adds a list of values to the end of the current list

        :param value: `iter`, values to extend
        """

        [self.append(v) for v in value]

    @property
    def store(self):
        """:return: external/user-accessible value for the current object"""

        return [v.store for v in self._items if v.active]


class _ListHandlePairs(_List):
    """special list for parallel method of accessing handle pairs

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    def __init__(self, meta, index='', store=()):
        _List.__init__(self, meta=meta, index=index, store=store,
                       obj=_DictHandlePair)

        self.dt1 = _ListHandlePairCoords('dt1', self, meta.dt1)
        self.dt0 = _ListHandlePairCoords('dt0', self, meta.dt0)
        self.dv0 = _ListHandlePairCoords('dv0', self, meta.dv0)
        self.dv1 = _ListHandlePairCoords('dv1', self, meta.dv1)


class _ListKeyframes(collections.MutableMapping):
    """provides time/value keyframe data from an animation parameter

    :param store: `dict`, user-accessible object value
    """

    meta = params.animation

    def __init__(self, store, dest=''):
        self.meta.dest = dest
        self.times = store['times']
        self.values = store['values']
        self.handle_pairs = store['handlePairs']

        self.dt0 = self.handle_pairs.dt0
        self.dt1 = self.handle_pairs.dt1
        self.dv0 = self.handle_pairs.dv0
        self.dv1 = self.handle_pairs.dv1

        self.time = self.times
        self.value = self.values
        self.handle_pair = self.handle_pairs

    def __call__(self, **kwargs):

        time = kwargs['times'] if 'times' in kwargs else None
        value = kwargs['values'] if 'values' in kwargs else None

        hp_keys = 'dt0', 'dt1', 'dv0', 'dv1'
        hp_dict = {k: None for k in hp_keys}
        hp = {k: v for k, v in kwargs.items() if k in hp_keys}
        hp_dict.update(hp)

        self.time(time)
        self.value(value)
        self.handle_pair(hp)

    def __delitem__(self, index):
        [v.__delitem___(index) for v in self.keyframes.values()]

    def __getitem__(self, index):

        if isinstance(index, slice):
            start = index.start or 0
            end = index.stop or self.__len__()
            step = index.step or 1
            range_ = xrange(start, end, step)
            return [self.keyframe(i) for i in range_]
        else:
            return self.keyframe(index)

    def __iter__(self):
        return iter(self.keyframes.items())

    def __len__(self):
        return max([len(x) for x in self.__dict__.values()])

    def __repr__(self):
        return dumps(self.store)

    def __setitem__(self, index, value):
        return index, value

    def arrange(self):
        """re-maps internal values (`self._store`) to `self.store`

        *this can be a slow operation on objects containing a lot of data*
        """

        self.times.arrange()
        self.values.arrange()
        self.handle_pairs.arrange()

    def delete(self):
        """resets current object's items to empty values"""

        self.times.delete()
        self.values.delete()
        self.handle_pairs.delete()

    def keyframe(self, index):
        """returns a user accessible single keyframe by index number

        :param index: `int`, position of keyframe to return
        :return: requested keyframe
        """

        dt0 = self.dt0[index]
        dt1 = self.dt1[index]
        time = self.times[index]
        value = self.values[index]
        dv0 = self.dv0[index]
        dv1 = self.dv1[index]

        store = od([
            ('dt0', dt0),
            ('dt1', dt1),
            ('times', time),
            ('values', value),
            ('dv0', dv0),
            ('dv1', dv1)])

        return _DictKeyframe(self.meta, index, store)

    @property
    def keyframes(self):
        """:return: user-accessible keyframe data"""

        return od([(i, self.keyframe(i)) for i in range(self.__len__())])

    @property
    def points(self):
        """:return: all present animation times/values as x/y coordinates"""

        points = []
        items = self.keyframes.items()
        w = self.meta.dest + ": {} not set for keyframe {}, skipping"

        for i, props in items:

            def point(index, xy): return props.store[index][xy]

            def value(index): return props.store[index]['value']

            dt0 = value('dt0')
            dv0 = value('dv0')
            dt1 = value('dt1')
            dv1 = value('dv1')

            x0 = point('dt0', 'x')
            y0 = point('dv0', 'y')
            x1 = point('times', 'x')
            y1 = point('values', 'y')
            x2 = point('dt1', 'x')
            y2 = point('dv1', 'y')

            pairs = all_or_none(index=i, dt0=dt0, dt1=dt1, dv0=dv0, dv1=dv1)

            if not any_(x1):
                ToolWarn(w.format('time', i))
                continue
            if not any_(y1):
                ToolWarn(w.format('value', i))
                continue

            keyframe = []

            if pairs:
                keyframe.append((x0, y0))

            keyframe.append((x1, y1))

            if pairs:
                keyframe.append((x2, y2))

            points.extend(keyframe)

        return points

    @property
    def store(self):
        """return: external/user-accessible value for the current object"""

        return od([(k, v.store) for k, v in self.keyframes.items()])

    @property
    def x(self):
        """:return: all x coordinates (i.e., times) in animation"""

        return [p[0] for p in self.points]

    @property
    def y(self):
        """:return: all y coordinates (i.e., values) in animation"""

        return [p[1] for p in self.points]


class _ListPriorities(_List):
    """container for view parameter viewPriorities

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.priorities

    def __init__(self, meta=meta, index='', store=()):
        _List.__init__(self, meta=meta, index=index, store=store)


class _ListTimes(_List):
    """pass through class for animation times list"""


class _ListValues(_List):
    """pass through class for animation values list"""


class _Obj(object):
    """object-type class for `Recipe`

    see ``help(_Obj.meta)`` / ``help(self.meta)`` for parameter attributes

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    def __init__(self, meta=None, index=None, store=None):
        self.meta = meta or _Meta()
        self.index = index if any_(index) else self.meta.dest
        self._store = None
        self._store = self._type(store)

    def __call__(self, value=None):
        self._store = self._type(value)

    def __iter__(self):
        return [self._store]

    def __repr__(self):
        return str(self.store)

    def _init(self):
        """resets object's internal value"""

        self._store = None

    def _type(self, value):
        """pass through function for converting/validating called value"""

        if not any_(value):
            return None
        else:
            return self.meta.type_(value)

    @property
    def active(self):
        """:return: True if `self._store` is not None else False"""

        return self._store or self._store == 0

    def arrange(self):
        """maps internal value (`self._store`) to `self.store`

        has no real use in `_Obj`; used for symmetry between module classes
        """

        self.__call__(self._store)

    def delete(self):
        """resets current object to an empty value"""

        self._init()

    @staticmethod
    def dependencies(*args, **kwargs):
        """validates that the current object's recipe dependencies are met

        has no real use in _Obj; used for symmetry between module classes

        :param args: `tuple`, positional args, not used
        :param kwargs: `dict`, keyword args, not used
        :return:
        """

        return args, kwargs

    @property
    def store(self):
        """:return: external/user-accessible value for the current object"""

        return self._store

    def update(self, *args, **kwargs):
        """changes current value

        :param args: `tuple`, positional args passed to `self.__call__`
        :param kwargs: `dict`, keyword args passed to `self.__call__`
        """

        self.__call__(*args, **kwargs)


class _ObjAngle(_Obj):
    """crop angle coordinate object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.crop.angle

    def __init__(self, meta=meta, index='', store=None):
        _Obj.__init__(self, meta=meta, index=index, store=store)


class _ObjBottom(_Obj):
    """crop bottom coordinate object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.crop.bottom

    def __init__(self, meta=meta, index='', store=None):
        _Obj.__init__(self, meta=meta, index=index, store=store)


class _ObjDt0(_Obj):
    """handle pair time predecessor object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.animation.dt0

    def __init__(self, meta=meta, index='', store=None):
        _Obj.__init__(self, meta, index, store)


class _ObjDt1(_Obj):
    """handle pair time successor object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.animation.dt1

    def __init__(self, meta=meta, index='', store=None):
        _Obj.__init__(self, meta, index, store)


class _ObjDv0(_Obj):
    """handle pair value predecessor object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    def __init__(self, meta, index='', store=None):
        _Obj.__init__(self, meta, index, store)


class _ObjDv1(_Obj):
    """handle pair value successor object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    def __init__(self, meta, index='', store=None):
        _Obj.__init__(self, meta, index, store)


class _ObjInitialValue(_Obj):
    """animation initial value object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    def __init__(self, meta, index='', store=None):
        _Obj.__init__(self, meta=meta, index=index, store=store)


class _ObjLeft(_Obj):
    """crop left coordinate object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.crop.left

    def __init__(self, meta=meta, index='', store=None):
        _Obj.__init__(self, meta=meta, index=index, store=store)


class _ObjRight(_Obj):
    """crop right coordinate object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.crop.right

    def __init__(self, meta=meta, index='', store=None):
        _Obj.__init__(self, meta=meta, index=index, store=store)


class _ObjTop(_Obj):
    """crop top coordinate object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.crop.top

    def __init__(self, meta=meta, index='', store=None):
        _Obj.__init__(self, meta=meta, index=index, store=store)


class _ObjX(_Obj):
    """control point x coordinate object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.luminance_tone_curve.x

    def __init__(self, meta=meta, index='', store=None):
        _Obj.__init__(self, meta=meta, index=index, store=store)


class _ObjY(_Obj):
    """control point y coordinate object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.luminance_tone_curve.y

    def __init__(self, meta=meta, index='', store=None):
        _Obj.__init__(self, meta=meta, index=index, store=store)


class _ObjZuluTime(_Obj):
    """zulu time object

    :param meta: `params.ViewParameter`, view parameter class meta information
    :param index: `int`/`str`, index for object
    :param store: `dict`, user-accessible object value
    """

    meta = params.zulu_time

    def __init__(self, meta=meta, index='', store=None):
        _Obj.__init__(self, meta=meta, index=index, store=store)

    def __call__(self, value=utils.zulu_time()):
        self._store = value
