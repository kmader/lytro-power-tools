# -*- coding: utf-8 -*-
"""Lytro Power Tools - utilities package - shared calculation utilities"""

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

import pytweening
import collections
import numpy as np

from scipy import interpolate

from lpt.utils.utils import Utils
from lpt.utils.msgutils import ToolError

utils = Utils()
od = collections.OrderedDict
interp1d = interpolate.interp1d


class CalcUtils(object):
    """various math related functions and utilities"""

    print_help = object
    _ease_function = pytweening.linear

    def set_print_help(self, print_help):
        """sets `argparse` help menu for current command

        :param print_help: `object`, passed to ToolError for command help menu
        """

        self.print_help = print_help
        utils.set_print_help(print_help)

    @staticmethod
    def four_d_coord(row, column, pitch=14, norm=.5):
        """calculates standardized lightfield 4D coordinates


        :param pitch: `int`, lenslet pitch (ILLUM/Gen. 2 LDK == 14)
        :param norm: `float`, coordinate normalization (ILLUM/Gen. 2 LDK == .5)
        :param column: `int`, column of standardized lightfield to calculate
        :param row: `int`, row of standardized lightfield to calculate
        :return: calculated coordinate
        """

        def uv(i): return (i % pitch + norm) / pitch - norm
        x = column / pitch
        y = row / pitch
        u = round(uv(column), 3)
        v = round(uv(row), 3)
        return {'y': y, 'x': x, 'u': u, 'v': v}

    def min_distance(self, array, number):
        """given a list of numbers and a target value, find the closest value

        array most contain unique values

        :param array: `list`, list of numbers to parse through
        :param number: `float`/`int`, target value
        :return: closest value found in lst
        :raise: `ToolError` if array contains non-unique values
        """

        e = "array contains non-unique values"
        assert len(array) == len(set(array)), ToolError(e, self.print_help)

        array = self._array(array)
        value = min(array, key=lambda x: abs(x - number))
        index = np.where(array == value)[0][0]
        return index, value

    @staticmethod
    def _array(array, type_=float):
        """converts lst to numpy.array"""

        return np.array([type_(x) for x in array])

    def interp(self, x, y, num=None, **kwargs):
        """interpolates a list of numbers

        :param x: `iter`, list of x-coordinates
        :param y: `iter`, list of y-coordinates
        :param num: `int`, number of steps to generate
        :param kwargs: `dict`, keyword arguments passed to scipy.interpolate
        :return: interpolated list of x/y points
        """

        x = self._array(x)
        y = self._array(y)
        a = x[0]
        b = x[-1]
        num = num or len(x)
        interp = interp1d(x, y, **kwargs)
        x_new = np.linspace(a, b, num)
        y_new = interp(x_new)
        return x_new, y_new

    def normalize(self, array, a=0, b=None):
        """multiplies a list of numbers while keeping same shape

        :param array: `list`, list of numbers to normalize
        :param a: `float`, interpolate start value (optional)
        :param b: `float`, interpolate end value (optional)
        :return: normalized list
        """

        array = self._array(array)
        any_ = utils.any_
        norm = array / array[-1]

        def lerp(x, y, t): return (1 - t) * x + t * y

        if any_(b):
            norm = self._array([lerp(a, b, i) for i in norm])

        return norm

    def scale(self, array, a=0, b=1):
        """scales a list of numbers, maintaining ratio between objects

        :param array: `iter`, list of numbers to scale
        :param a: `float`, new start value
        :param b: `float`, new end value
        :return: scaled list of numbers
        """

        x = array[0]
        y = array[-1]
        old = y - x
        new = b - a
        return self._array([(((i - x) * new) / old) + a for i in array])

    def tween(self, a=0, b=1, num=100, func=_ease_function):
        """tweens between two given values based off of a given function

        :param a: `float`, start point
        :param b: `float`, end point
        :param num: `int`, number of steps to generate
        :param func: `object`, function to apply against a/b line
        :return: tweened x/y points
        """

        x_line = np.linspace(a, b, num)
        y_line = self._array([func(n) for n in x_line])
        return x_line, y_line
