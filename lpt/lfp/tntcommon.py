# -*- coding: utf-8 -*-
"""Lytro Power Tools - lfp package - common tnt tasks"""

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

import os
import glob
import re
import shutil

from lpt.lfp import config
from lpt.lfp.lfp import Lfp
from lpt.lfp.tnt import Tnt
from lpt.lfp.tool import Tool
from lpt.recipe.recipe import Recipe
from lpt.utils.argutils import ArgUtils
from lpt.utils.msgutils import MsgUtils
from lpt.utils.utils import Utils

utils = Utils()
msgutils = MsgUtils()
argutils = ArgUtils()
tool = Tool()


class TntCommon(object):
    """common TNT commands and miscellaneous related functions

    :param verbose: `bool`, increase verbosity, i.e., show TNT output
    :param debug: `bool`, turn on debug output
    """

    _eslfstr = config.eslfstr
    _depthstr = config.depthstr

    _output_lfp = config.output_lfp
    _output_lfr = config.output_lfr
    _output_xraw = config.output_xraw
    _output_raw = config.output_raw
    _output_txt = config.output_txt
    _output_jsn = config.output_jsn
    _output_unpacked = config.output_unpacked

    _recipe_file = config.recipe_json
    _output_file = config.output_json
    _lfp_pattern = tool.lfp_pattern

    _db = config.db

    print_help = object

    def __init__(self, verbose=False, debug=False):

        self.verbose = verbose
        self.debug = debug
        self.on_fail = object
        self.lock = None
        self.validate_recipe = True

    @staticmethod
    def depth_map_json(dir_out, name):
        """format depth map json file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        """

        json_out = '.'.join([name, 'jsn'])
        json_out = utils.join_abspath(dir_out, json_out)
        return json_out

    def depth_out(self, dir_out, name, ext):
        """format depth map image file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        :param ext: `str`, file extension
        """

        depth_out = '{}_{}.{}'.format(name, self._depthstr, ext)
        depth_out = utils.join_abspath(dir_out, depth_out)
        return depth_out

    def eslf_out(self, dir_out, name, ext):
        """format lightfield image file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        :param ext: `str`, file extension
        """

        eslf_out = '{}_{}.{}'.format(name, self._eslfstr, ext)
        eslf_out = utils.join_abspath(dir_out, eslf_out)
        return eslf_out

    @staticmethod
    def image_out(dir_out, name, ext):
        """format image file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        :param ext: `str`, file extension
        """

        image_out = '.'.join([name, ext])
        image_out = utils.join_abspath(dir_out, image_out)
        return image_out

    def jsn_out(self, depth_out):
        """format depth map image json file name

        :param depth_out: `str`, path to depth_out
        """

        basedir, name, ext = utils.split_path(depth_out)
        jsn_out = ''.join([name, self._output_jsn])
        jsn_out = utils.join_abspath(basedir, jsn_out)
        return jsn_out

    def lfp_out(self, dir_out, name):
        """format LFP file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        """

        lfp_out = ''.join([name, self._output_lfp])
        lfp_out = utils.join_abspath(dir_out, lfp_out)
        return lfp_out

    def lfp_out_packed(self, dir_out, name):
        """format unpacked LFP file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        """

        packed = name.replace(self._output_unpacked, '')
        lfp_out = ''.join([packed, self._output_lfp])
        lfp_out = utils.join_abspath(dir_out, lfp_out)
        lfp_out = utils.sanitize_path(lfp_out)

        return lfp_out

    def lfp_out_unpacked(self, dir_out, name):
        """format unpacked LFP file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        """

        lfp_out = ''.join([name, self._output_unpacked, self._output_lfp])
        lfp_out = utils.join_abspath(dir_out, lfp_out)
        return lfp_out

    def lfr_out(self, dir_out, name):
        """format LFR file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        """

        lfr_out = ''.join([name, self._output_lfr])
        lfr_out = utils.join_abspath(dir_out, lfr_out)
        return lfr_out

    def output_json(self, dir_out, name):
        """format LFP json output file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        """

        json_out = ''.join([name, self._output_file])
        json_out = utils.join_abspath(dir_out, json_out)
        return json_out

    def raw_out(self, dir_out, name):
        """format RAW file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        """

        raw_out = ''.join([name, self._output_raw])
        raw_out = utils.join_abspath(dir_out, raw_out)
        return raw_out

    def txt_out(self, raw_out):
        """format RAW TXT file name

        :param raw_out: `str`, raw_out path
        """

        basedir, name, ext = utils.split_path(raw_out)
        txt_out = ''.join([name, self._output_txt])
        txt_out = utils.join_abspath(basedir, txt_out)
        return txt_out

    def recipe_json(self, dir_out, name):
        """format recipe file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        """

        json_out = '_'.join([name, self._recipe_file])
        json_out = utils.join_abspath(dir_out, json_out)
        return json_out

    def xraw_out(self, dir_out, name):
        """format XRAW LFR file name

        :param dir_out: `str`, directory out
        :param name: `str`, base file name
        """

        xraw_out = ''.join([name, self._output_xraw, self._output_lfp])
        xraw_out = utils.join_abspath(dir_out, xraw_out)
        return xraw_out

    def _check_dir(self, path=None, sane=False):
        """provides various internal directory checks"""

        if not path:
            return None
        p = os.path.abspath(path)
        if os.path.exists(p) and sane:
            p = utils.sanitize_path(p)
        if not os.path.exists(p):
            p = utils.mkdir(p)
            self.on_fail = lambda: shutil.rmtree(p)
        return p

    def _execute(self, tnt):
        """ middle-man for tnt executor"""

        if self.verbose or self.lock:
            tnt.execute(failure=self.on_fail, lock=self.lock)
        else:
            meta, margin = msgutils.msg_meta()
            status = margin + msgutils.item('processing')
            with msgutils.msg_indicator(status):
                tnt.execute(failure=self.on_fail)

        self.on_fail = object

    @staticmethod
    def _batch_id(root, count=0, end=0, pad=4, time='.', i=0, u=None, v=None):
        """generates a unique identifier for ``batch`` command"""

        ids = []

        if end:
            g_len = len(str(end).split('.')[0])
            ss, ms = str(time).split('.')
            ss = ss.zfill(g_len)
            ms = ms.ljust(4, '0')[:4]
            ids.append('.'.join([ss, ms]))

        else:
            pad = pad if pad > 4 else 4
            ids.append(str(i).zfill(pad))

        def _uv_id(label, obj):
            p = len(str(count)) if count > 999 else 4
            p = '%.{}f'.format(p)

            if not (obj or obj == 0):
                return ''
            elif obj >= 0:
                id_ = '_{}'.format(p % obj)
            else:
                id_ = p % obj

            return ''.join([label, id_])

        u_id = _uv_id('u', u)
        v_id = _uv_id('v', v)

        if u_id and v_id:
            ids.append('_'.join([u_id, v_id]))

        ids.append(root)
        return '__'.join(ids)

    @staticmethod
    def _image_id(image_in, focus=None, upers=None, vpers=None):
        """makes a unique string using the parameters from focus & u/v pers"""

        def dec_len(x): return len(str(x).split('.')[-1])

        def pad_len(x): return dec_len(x) if dec_len(x) > 4 else 4

        def pad(x): return str('%.{}f'.format(pad_len(x)))

        def sign(x): return '_{}'.format(pad(x)) if x >= 0 else pad(x)

        f = 'f{}'.format(sign(focus) % focus) if focus else ''
        u = 'u{}'.format(sign(upers) % upers) if upers else ''
        v = 'v{}'.format(sign(vpers) % vpers) if vpers else ''

        basedir, name, ext = utils.split_path(image_in)
        image_out = '_'.join([s for s in name, f, u, v if s]) + ext
        image_out = utils.join_abspath(basedir, image_out)
        return image_out

    def _set_calibration_in(self, lfp_in, calibration_in):
        """intercepts LFP and determines if calibration in is required"""

        lfp = Lfp(lfp_in, self.print_help)
        return None if lfp.has_xraw else calibration_in

    @staticmethod
    def _set_height_width(lfp_in, height=None, width=None):
        """sets height/width"""

        if (height and width) or (height is None and width is None):
            return height, width
        else:
            return tool.dimensions_ratio(lfp_in, height, width)

    def set_recipe_in(self, recipe_in, i=0):
        """intercepts and validates local recipe file

        :param recipe_in: <Recipe>/`str`, recipe object/file to set
        :param i: `int`, iteration during multi file-out process
        :return: path to recipe_in
        """

        if not recipe_in:
            return None

        if isinstance(recipe_in, Recipe):
            recipe = recipe_in
        else:
            recipe = Recipe(recipe_in)

        if self.validate_recipe:
            msg = "validating recipe file"
            msgutils.status(msg, src=recipe_in, count=i)
            recipe.validate()

        return recipe.path

    def _split_path(self, path):
        """intercepts funcutil.split_path"""

        basedir, name, ext = utils.split_path(path)
        glob_pattern = os.path.join(basedir, name + '.*')
        similar = glob.glob(glob_pattern)
        similar = [x for x in similar if re.match(self._lfp_pattern, x)]

        if len(similar) > 1:
            name += ('_' + ext.lstrip('.'))

        return basedir, name, ext

    def _status(self, action_out, type_, i=0, **kwargs):
        """msgutil.status wrapper for all actions"""

        def _func():
            msg = "processing {} from {} LFP file".format(action_out, type_)
            msgutils.status(msg, count=i, **kwargs)

        if self.lock:
            with self.lock:
                _func()
        else:
            _func()

    def raw_depth_out(self, lfp_in, calibration_in=None, depth_in=None,
                      depthrep=None, dir_out=None, imagerep=None,
                      orientation=None, threads=None, i=0):
        """TNT process: raw LFR to warp depth out

        :param lfp_in: `str`, source LFP file
        :param calibration_in: `str`, calibration directory
        :param depth_in: `str`, depth map input file
        :param depthrep: `str`, depth map representation
        :param dir_out: `str`, directory out
        :param imagerep: `str`, image representation for processed LFP
        :param orientation: `int`, image orientation
        :param threads: `int`, number of processing threads to use
        :param i: `int`, iteration during multi file-out process
        """

        calibration_in = self._set_calibration_in(lfp_in, calibration_in)
        depthrep = depthrep or self._db['depthrep_raw_depth_out']
        imagerep = imagerep or self._db['imagerep_raw_depth_out']

        basedir, name, ext = self._split_path(lfp_in)
        dir_out = self._check_dir(dir_out) if dir_out else basedir
        depth_out = self.depth_out(dir_out, name, depthrep)
        image_out = self.image_out(dir_out, name, imagerep)
        depth_out = utils.sanitize_path(depth_out)
        image_out = utils.sanitize_path(image_out)
        jsn_out = self.jsn_out(image_out)
        dest = depth_out, image_out, jsn_out

        self._status("depth map", "raw", src=lfp_in, dest=dest, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.depth_out(depth_out)
        tnt.image_out(image_out)
        tnt.orientation(orientation)
        tnt.calibration_in(calibration_in)
        tnt.depth_in(depth_in)
        self._execute(tnt)

    def raw_eslf_out(self, lfp_in, calibration_in=None, dir_out=None,
                     imagerep=None, threads=None, i=0):
        """TNT process: raw LFR to lightfield image out

        :param lfp_in: `str`, source LFP file
        :param calibration_in: `str`, calibration directory
        :param dir_out: `str`, directory out
        :param imagerep: `str`, image representation for processed LFP
        :param threads: `int`, number of processing threads to use
        :param i: `int`, iteration during multi file-out process
        """

        calibration_in = self._set_calibration_in(lfp_in, calibration_in)
        imagerep = imagerep or self._db['imagerep_raw_eslf_out']

        basedir, name, ext = self._split_path(lfp_in)
        dir_out = self._check_dir(dir_out) if dir_out else basedir
        eslf_out = self.eslf_out(dir_out, name, imagerep)
        eslf_out = utils.sanitize_path(eslf_out)

        slf = "standardized lightfield image"
        self._status(slf, "raw", src=lfp_in, dest=eslf_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.eslf_out(eslf_out)
        tnt.calibration_in(calibration_in)
        self._execute(tnt)

    def raw_image_out(self, lfp_in, image_out=None, calibration_in=None,
                      depth_in=None, dir_out=None, focus=None, height=None,
                      imagerep=None, orientation=None, perspective_u=None,
                      perspective_v=None, recipe_in=None, threads=None,
                      width=None, i=0):
        """TNT process: raw LFR to image out

        :param lfp_in: `str`, source LFP file
        :param calibration_in: `str`, calibration directory
        :param depth_in: `str`, depth map input file
        :param dir_out: `str`, directory out
        :param focus: `float`, image focus point
        :param height: `int`, resolution height (in pixels)
        :param image_out: `str`, destination image file
        :param imagerep: `str`, image representation for processed LFP
        :param orientation: `int`, image orientation
        :param perspective_u: `float`, perspective u coordinate
        :param perspective_v: `float`, perspective v coordinate
        :param recipe_in: `str`, input recipe file
        :param threads: `int`, number of processing threads to use
        :param width: `int`, resolution width (in pixels)
        :param i: `int`, iteration during multi file-out process
        """

        calibration_in = self._set_calibration_in(lfp_in, calibration_in)
        imagerep = imagerep or self._db['imagerep_raw_image_out']
        height, width = self._set_height_width(lfp_in, height, width)
        u, v = perspective_u, perspective_v

        recipe_in = self.set_recipe_in(recipe_in, i)

        if not image_out:
            basedir, name, ext = self._split_path(lfp_in)
            dir_out = self._check_dir(dir_out) if dir_out else basedir
            image_out = self.image_out(dir_out, name, imagerep)
            image_out = self._image_id(image_out, focus, u, v)
            image_out = utils.sanitize_path(image_out)

        self._status("image", "raw", src=lfp_in, dest=image_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.image_out(image_out)
        tnt.calibration_in(calibration_in)
        tnt.imagerep(imagerep)
        tnt.height(height)
        tnt.width(width)
        tnt.orientation(orientation)
        tnt.depth_in(depth_in)
        tnt.recipe_in(recipe_in)
        tnt.focus(focus)
        tnt.perspective_u(u)
        tnt.perspective_v(v)

        self._execute(tnt)

    def raw_lfp_out(self, lfp_in, calibration_in=None, depth_in=None,
                    depthrep=None, dir_out=None, height=None, imagerep=None,
                    orientation=None, perspective_u=(), perspective_v=(),
                    recipe_in=None, threads=None, width=None, i=0):
        """TNT process: raw LFR to warp LFP

        :param lfp_in: `str`, source LFP file
        :param calibration_in: `str`, calibration directory
        :param depth_in: `str`, depth map input file
        :param depthrep: `str`, depth map representation
        :param dir_out: `str`, directory out
        :param height: `int`, resolution height (in pixels)
        :param imagerep: `str`, image representation for processed LFP
        :param orientation: `int`, image orientation
        :param perspective_u: `float`, perspective u coordinate
        :param perspective_v: `float`, perspective v coordinate
        :param recipe_in: `str`, input recipe file
        :param threads: `int`, number of processing threads to use
        :param width: `int`, resolution width (in pixels)
        :param i: `int`, iteration during multi file-out process
        """

        calibration_in = self._set_calibration_in(lfp_in, calibration_in)
        depthrep = depthrep or self._db['depthrep_raw_lfp_out']
        imagerep = imagerep or self._db['imagerep_raw_lfp_out']
        height, width = self._set_height_width(lfp_in, height, width)

        basedir, name, ext = self._split_path(lfp_in)
        recipe_in = self.set_recipe_in(recipe_in, i)
        dir_out = self._check_dir(dir_out) if dir_out else basedir
        lfp_out = self.lfp_out(dir_out, name)
        lfp_out = utils.sanitize_path(lfp_out)

        self._status("warp LFP", "raw", src=lfp_in, dest=lfp_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.lfp_out(lfp_out)
        tnt.imagerep(imagerep)
        tnt.depthrep(depthrep)
        tnt.height(height)
        tnt.width(width)
        tnt.orientation(orientation)
        tnt.depth_in(depth_in)
        tnt.recipe_in(recipe_in)
        tnt.calibration_in(calibration_in)
        tnt.perspective_u(perspective_u)
        tnt.perspective_v(perspective_v)
        self._execute(tnt)

    def raw_lfp2raw(self, lfp_in, dir_out=None, threads=None, i=0):
        """TNT process: unpackage RAW and corresponding TXT

        :param lfp_in: `str`, source LFP file
        :param dir_out: `str`, directory out
        :param threads: `int`, number of processing threads to use
        :param i: `int`, iteration during multi file-out process
        """

        basedir, name, ext = self._split_path(lfp_in)
        dir_out = self._check_dir(dir_out) if dir_out else basedir
        raw_out = self.raw_out(dir_out, name)
        raw_out = utils.sanitize_path(raw_out)
        txt_out = self.txt_out(raw_out)
        dest = raw_out, txt_out

        self._status("unpackaged RAW", "raw", src=lfp_in, dest=dest, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.raw_out(raw_out)
        tnt.lfp2raw()
        self._execute(tnt)

    def raw_lfr2xraw(self, lfp_in, calibration_in=None, dir_out=None,
                     threads=None, i=0):
        """TNT process: raw LFR to xraw LFR

        :param lfp_in: `str`, source LFP file
        :param calibration_in: `str`, calibration directory
        :param dir_out: `str`, directory out
        :param threads: `int`, number of processing threads to use
        :param i: `int`, iteration during multi file-out process
        """

        calibration_in = self._set_calibration_in(lfp_in, calibration_in)

        basedir, name, ext = self._split_path(lfp_in)
        dir_out = self._check_dir(dir_out) if dir_out else basedir
        xraw_out = self.xraw_out(dir_out, name)
        xraw_out = utils.sanitize_path(xraw_out)

        self._status("xraw LFR", "raw", src=lfp_in, dest=xraw_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.lfp_out(xraw_out)
        tnt.lfr2xraw()
        tnt.calibration_in(calibration_in)
        self._execute(tnt)

    def raw_raw2lfp(self, raw_in, dir_out=None, threads=None, i=0):
        """TNT process: package RAW and corresponding TXT

        :param raw_in: `str`, source RAW file
        :param dir_out: `str`, directory out
        :param threads: `int`, number of processing threads to use
        :param i: `int`, iteration during multi file-out process
        """

        basedir, name, ext = self._split_path(raw_in)
        dir_out = self._check_dir(dir_out) if dir_out else basedir
        lfp_out = self.lfr_out(dir_out, name)
        lfp_out = utils.sanitize_path(lfp_out)

        self._status("raw", "unpackaged RAW", src=raw_in, dest=lfp_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.raw_in(raw_in)
        tnt.lfp_out(lfp_out)
        tnt.raw2lfp()
        self._execute(tnt)

    def raw_transcode(self, lfp_in, lfp_out=None, threads=None, i=0):
        """TNT process: raw LFP to raw LFP

        :param lfp_in: `str`, source LFP file
        :param lfp_out: `str`, destination LFP file
        :param threads: `int`, number of processing threads to use
        :param i: `int`, iteration during multi file-out process
        """

        lfp_out = lfp_out or lfp_in

        self._status("raw LFP", "raw", src=lfp_in, dest=lfp_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.lfp_out(lfp_out)
        tnt.transcode()
        self._execute(tnt)

    def raw_unpack(self, lfp_in, calibration_in=None, depth_in=None,
                   depthrep=None, dir_out=None, height=None, imagerep=None,
                   orientation=None, perspective_u=None, perspective_v=None,
                   recipe_in=None, threads=None, width=None, i=0):
        """TNT process: raw LFR to image out

        :param lfp_in: `str`, source LFP file
        :param calibration_in: `str`, calibration directory
        :param depth_in: `str`, depth map input file
        :param depthrep: `str`, depth map representation
        :param dir_out: `str`, directory out
        :param height: `int`, resolution height (in pixels)
        :param imagerep: `str`, image representation for processed LFP
        :param orientation: `int`, image orientation
        :param perspective_u: `float`, perspective u coordinate
        :param perspective_v: `float`, perspective v coordinate
        :param recipe_in: `str`, input recipe file
        :param threads: `int`, number of processing threads to use
        :param width: `int`, resolution width (in pixels)
        :param i: `int`, iteration during multi file-out process
        """

        calibration_in = self._set_calibration_in(lfp_in, calibration_in)
        depthrep = depthrep or self._db['depthrep_raw_unpack']
        imagerep = imagerep or self._db['imagerep_raw_unpack']
        height, width = self._set_height_width(lfp_in, height, width)

        basedir, name, ext = self._split_path(lfp_in)
        recipe_in = self.set_recipe_in(recipe_in, i)
        parent_dir = self._check_dir(dir_out) if dir_out else basedir
        dir_out = os.path.join(parent_dir, name)
        dir_out = self._check_dir(dir_out, sane=True)
        lfp_out = self.lfp_out_unpacked(dir_out, name)

        self._status("unpacked warp LFP", "raw", src=lfp_in, dest=dir_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.dir_out(dir_out)
        tnt.lfp_out(lfp_out)
        tnt.unpack()
        tnt.imagerep(imagerep)
        tnt.depthrep(depthrep)
        tnt.height(height)
        tnt.width(width)
        tnt.orientation(orientation)
        tnt.depth_in(depth_in)
        tnt.recipe_in(recipe_in)
        tnt.calibration_in(calibration_in)
        tnt.perspective_u(perspective_u)
        tnt.perspective_v(perspective_v)
        self._execute(tnt)

        if os.path.exists(lfp_out):
            self.recipe_out(lfp_out, threads=threads, i=i)
            self.warp_depth_map_json_out(lfp_out, i=i)

    def recipe_out(self, lfp_in, dir_out=None, threads=None, i=0):
        """TNT process: raw LFR/warp LFP to recipe file

        :param lfp_in: `str`, source LFP file
        :param dir_out: `str`, directory out
        :param threads: `int`, number of processing threads to use
        :param i: `int`, iteration during multi file-out process
        """

        basedir, name, ext = self._split_path(lfp_in)
        dir_out = self._check_dir(dir_out) if dir_out else basedir
        recipe_out = self.recipe_json(dir_out, name)
        recipe_out = utils.sanitize_path(recipe_out)

        self._status("recipe file", "warp", src=lfp_in, dest=recipe_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.recipe_out(recipe_out)
        self._execute(tnt)

    def warp_depth_map_json_out(self, lfp_in, dir_out=None, i=0):
        """generates min/max lambda json file(s) from LFP metadata

        :param lfp_in: `str`, source LFP file
        :param dir_out: `str`, directory out
        :param i: `int`, iteration during multi file-out process
        """

        lfp = Lfp(lfp_in, self.print_help)

        depth_maps = lfp.depth_maps
        basedir, name, ext = self._split_path(lfp_in)
        dir_out = self._check_dir(dir_out) if dir_out else basedir

        for depth_map in depth_maps:

            if 'imagePath' not in depth_map:
                continue

            lambda_min = depth_map['minLambda']
            lambda_max = depth_map['maxLambda']
            data = {"LambdaMin": lambda_min, "LambdaMax": lambda_max}

            image_path = depth_map['imagePath']
            image_name, _ = os.path.splitext(image_path)

            dest = self.depth_map_json(dir_out, image_name)
            dest = utils.sanitize_path(dest)

            self._status("depth map json", "warp", src=lfp_in, dest=dest, i=i)

            utils.write(dest, data)

    def warp_pack(self, lfp_in, depthrep=None, dir_out=None, height=None,
                  imagerep=None, threads=None, width=None, i=0):
        """TNT process: unpacked warp LFP to warp LFP

        :param lfp_in: `str`, source LFP file
        :param depthrep: `str`, depth map representation
        :param dir_out: `str`, directory out
        :param height: `int`, resolution height (in pixels)
        :param imagerep: `str`, image representation for processed LFP
        :param threads: `int`, number of processing threads to use
        :param width: `int`, resolution width (in pixels)
        :param i: `int`, iteration during multi file-out process
        """

        image_paths = tool.image_paths(lfp_in)
        tool.verify_image_paths(lfp_in, image_paths)

        depthrep = depthrep or self._db['depthrep_warp_pack']
        imagerep = imagerep or self._db['imagerep_warp_pack']
        height, width = self._set_height_width(lfp_in, height, width)

        basedir, name, ext = self._split_path(lfp_in)
        dir_out = self._check_dir(dir_out) if dir_out else basedir
        lfp_out = self.lfp_out_packed(dir_out, name)

        self._status("warp LFP", "unpacked", src=lfp_in, dest=lfp_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.lfp_out(lfp_out)
        tnt.transcode()
        tnt.imagerep(imagerep)
        tnt.depthrep(depthrep)
        tnt.height(height)
        tnt.width(width)
        self._execute(tnt)

    def warp_transcode(self, lfp_in, lfp_out=None, threads=None, i=0):
        """TNT process: warp LFP to warp LFP

        :param lfp_in: `str`, source LFP file
        :param lfp_out: `str`, destination LFP file
        :param threads: `int`, number of processing threads to use
        :param i: `int`, iteration during multi file-out process
        """

        lfp_out = lfp_out or lfp_in

        self._status("warp LFP", "warp", src=lfp_in, dest=lfp_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.lfp_out(lfp_out)
        tnt.transcode()
        self._execute(tnt)

    def warp_unpack(self, lfp_in, depthrep=None, dir_out=None, height=None,
                    imagerep=None, threads=None, width=None, i=0):
        """TNT process: warp LFP to unpacked warp LFP

        :param lfp_in: `str`, source LFP file
        :param depthrep: `str`, depth map representation
        :param dir_out: `str`, directory out
        :param height: `int`, resolution height (in pixels)
        :param imagerep: `str`, image representation for processed LFP
        :param threads: `int`, number of processing threads to use
        :param width: `int`, resolution width (in pixels)
        :param i: `int`, iteration during multi file-out process
        """

        depthrep = depthrep or self._db['depthrep_warp_unpack']
        imagerep = imagerep or self._db['imagerep_warp_unpack']
        height, width = self._set_height_width(lfp_in, height, width)

        basedir, name, ext = self._split_path(lfp_in)
        dir_out = self._check_dir(dir_out) if dir_out else basedir
        lfp_out = self.lfp_out_unpacked(dir_out, name)

        self._status("unpacked LFP", "warp", src=lfp_in, dest=dir_out, i=i)

        tnt = Tnt(verbose=self.verbose)
        tnt.threads(threads)
        tnt.lfp_in(lfp_in)
        tnt.dir_out(dir_out)
        tnt.lfp_out(lfp_out)
        tnt.transcode()
        tnt.unpack()
        tnt.imagerep(imagerep)
        tnt.depthrep(depthrep)
        tnt.height(height)
        tnt.width(width)
        self._execute(tnt)

        if os.path.exists(lfp_out):
            self.recipe_out(lfp_out, threads=threads, i=i)
            self.warp_depth_map_json_out(lfp_out, i=i)
