# -*- coding: utf-8 -*-
"""Lytro Power Tools - lfp package - tools for interacting with LFP files"""

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
import re
import functools
import multiprocessing

from lpt.lfp import config
from lpt.lfp.lfp import Lfp
from lpt.utils.argutils import ArgUtils
from lpt.utils.jsonutils import JsonUtils
from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.utils.msgutils import ToolWarn
from lpt.utils.utils import Utils

utils = Utils()
msgutils = MsgUtils()
argutils = ArgUtils()
jsonutils = JsonUtils()


class Tool(object):
    """various functions for interacting with LFP files"""

    lfp_pattern = re.compile('^.+\.lf[prcx]$', flags=re.IGNORECASE)
    raw_pattern = re.compile('^.+\.(raw|exr)$', flags=re.IGNORECASE)
    _file_pattern = config.file_pattern
    _schema_dir = config.dir_schema
    _validate = config.db['validate']

    print_help = object

    def set_print_help(self, print_help):
        """sets `argparse` help menu for current command

        :param print_help: `object`, passed to ToolError for command help menu
        """

        self.print_help = print_help
        utils.set_print_help(print_help)
        argutils.set_print_help(print_help)
        jsonutils.set_print_help(print_help)

    def _lfp_in(self, lfp_in):
        """verifies that `lfp_in` is a `Lfp` object"""

        if isinstance(lfp_in, Lfp):
            return lfp_in
        else:
            return Lfp(lfp_in, self.print_help)

    def _schema_path(self, url):
        """parses LFP schema URL into local path"""

        relpath = str(url).replace('http://schema.lytro.com/', '')
        path = os.path.join(self._schema_dir, relpath)
        return path if url and os.path.isfile(path) else ''

    def dimensions_ratio(self, lfp_in, height=None, width=None):
        """calculates new image dimensions from provided height or width

        reads lfp_in for raw or image dimensions, calculates the ratio,
        and returns a matching ratio to the provided height or width value

        :param lfp_in: <Lfp>/`str`, LFP to gather ratio from
        :param height: `int`, desired height in pixels
        :param width: `int`, desired width in pixels
        :return: ratioed height/width
        """

        lfp_in = self._lfp_in(lfp_in)
        images = lfp_in.images
        raw_dimensions = lfp_in.raw_dimensions

        h = w = 0

        if images:
            heights = utils.search_dict(images, 'height')
            widths = utils.search_dict(images, 'width')

            if heights:
                h = heights[0][1]
            if widths:
                w = widths[0][1]

        if not h or not w:
            if raw_dimensions:
                h, w = raw_dimensions[0]
            else:
                raise argutils.all_or_none(height=height, width=width)

        ratio = float(w) / float(h)

        if height and width:
            pass
        elif width:
            height = width / ratio
            height = int(round(height))
        elif height:
            width = height * ratio
            width = int(round(width))

        return height, width

    def image_paths(self, lfp_in):
        """queries LFP metadata for image paths

        :param lfp_in: `str`,/<Lfp> path or Lfp object to query
        :return: absolute paths to all referenced images
        :raise: `ToolError` if LFP file does not contain unpacked images
        """

        lfp_in = self._lfp_in(lfp_in)
        root, _ = os.path.split(lfp_in.path)

        e = "invalid unpacked warp LFP"
        assert lfp_in.has_unpacked, ToolError(e, self.print_help)

        image_items = utils.search_dict(lfp_in.picture, 'imagePath')
        image_paths = [item[1] for item in image_items]
        image_paths = [utils.join_abspath(root, i) for i in image_paths]

        return image_paths

    def search(self, paths, raw=None, xraw=None, warp=None, unpacked=None,
               compressed=None, v2=None, validate=_validate, file_range=(0, 0),
               file_pattern=_file_pattern, processors=1, mute=False):
        """searches for valid LFP files from a list of files or directories

        optional LFP types can be filtered for or out

        criterion for LFP types:
            True: filter for LFP file type
            False: filter out LFP file type
            None: neither True or False, no preference

        :param paths: `str`/`iter`, files/directories to search in
        :param raw: `bool`, filter out or for raw LFP files
        :param xraw: `bool`, filter out or for xraw LFP files
        :param warp: `bool`, filter out or for warp LFP files
        :param unpacked: `bool`, filter out or for unpacked LFP files
        :param compressed: `bool`, filter out or for compressed LFP files
        :param v2: `bool`, check if LFP is v2 LFP (keep True)
        :param validate: `bool`, enable/disable lfp schema validation
        :param mute: `bool`, mute messaging system when searching for LFP files
        :param file_pattern: passed to utils.utils.Utils.file_filter
        :param file_range: passed to utils.utils.Utils.file_filter
        :param processors: `int`, amount of processors to use for analyzing
        :yield: applicable LFP file data
        :raise: `ToolError` if invalid file or directory specified
        """

        if raw is False:
            xraw = False
            compressed = False

        file_filter = functools.partial(utils.file_filter,
                                        file_pattern=file_pattern,
                                        file_range=file_range)

        valid = dict(compressed=compressed,
                     raw=raw,
                     validate=validate,
                     unpacked=unpacked,
                     v2=v2,
                     warp=warp,
                     xraw=xraw)

        master = []
        paths = utils.make_iter(paths)

        if not mute:
            msgutils.status("checking for valid LFP content", src=paths)

        for path in paths:
            path = utils.full_path(path)
            e = "not a valid file or directory : {}".format(path)
            is_file_or_dir = os.path.isdir(path) or os.path.isfile(path)
            assert is_file_or_dir, ToolError(e, self.print_help)

            if os.path.isfile(path) and file_filter(path):
                master.append(path)

            elif os.path.isdir(path):
                file_paths = utils.walk_path(path, pattern=self.lfp_pattern)
                master.extend(fp for fp in file_paths if file_filter(fp))

        master = [(i, path) for i, path in enumerate(master, start=1)]

        def _search():
            queue = multiprocessing.Queue()
            done = multiprocessing.JoinableQueue()
            results = []
            procs = []
            [queue.put(x) for x in master]

            args = queue, done, valid

            for _ in range(processors):
                p = multiprocessing.Process(target=_search_worker, args=args)
                p.daemon = True
                p.start()
                procs.append(p)

            for _ in range(len(master)):
                results.append(done.get())
                done.task_done()

            for _ in range(processors):
                queue.put('STOP')

            done.join()
            queue.close()
            done.close()

            results = [x for x in results if x]
            results.sort(key=lambda obj: obj.path)
            return results

        if mute:
            return _search()
        else:
            meta = msgutils.msg_meta()[0]
            data_status = meta + msgutils.item("analyzing LFPs")

            with msgutils.msg_indicator(data_status):
                return _search()

    def search_raw(self, paths):
        """searches for RAW file types from a list of files or directories

        :param paths: `str`/`iter`, files/directories to search in; if `str`,,
                      the object is auto converted to a list
        :yield: applicable RAW files
        :raise: `ToolError` if invalid file or directory specified
        """

        paths = utils.make_iter(paths)

        def valid(p): return re.match(self.raw_pattern, p)

        for i, path in enumerate(paths, start=1):
            path = utils.full_path(path)

            is_file_or_dir = os.path.isdir(path) or os.path.isfile(path)
            e = "not a valid file or directory : " + path
            assert is_file_or_dir, ToolError(e, self.print_help)

            msg = "checking for RAW image data"
            msgutils.status(msg, src=path, count=i)

            if os.path.isfile(path) and valid(path):
                yield path

            elif os.path.isdir(path):
                file_paths = utils.walk_path(path, pattern=self.raw_pattern)

                for file_path in file_paths:
                    yield file_path

    def validate(self, lfp_in):
        """LFP schema validation against Lytro's LFP specifications.

        occurs during warp packing process if schema validation is enabled
        in the configuration

        :param lfp_in: `str`,/<Lfp> path or Lfp object to verify
        """

        lfp_in = self._lfp_in(lfp_in)
        picture = self._schema_path(lfp_in.picture_schema)
        private = [self._schema_path(p) for p in lfp_in.private_schema]
        public = [self._schema_path(p) for p in lfp_in.public_schema]

        picture_md = lfp_in.picture
        private_md = lfp_in.private
        public_md = lfp_in.public

        if picture:
            jsonutils.validate(picture_md, picture)

        for md, schema in [(public_md, public), (private_md, private)]:

            for i, frame in enumerate(md):
                if not frame:
                    continue
                if not schema or len(schema) < i:
                    continue
                schema_file = schema[i]
                if schema_file:
                    jsonutils.validate(frame, schema_file)

    def valid_lfp_file(self, lfp_path, compressed=None, raw=None, xraw=None,
                       unpacked=None, v2=None, validate=_validate, warp=None):
        """verify that a file is a valid LFP

        optional LFP types can be filtered for or out

        criterion for LFP types:
            True: filter for LFP file type
            False: filter out LFP file type
            None: neither True or False, no preference

        :param lfp_path: `str`, path to check
        :param v2: `bool`, check if LFP is v2 LFP (keep True)
        :param raw: `bool`, check if LFP is raw
        :param xraw: `bool`, check if LFP is xraw
        :param warp: `bool`, check if LFP is warp
        :param unpacked: `bool`, check if LFP is unpacked
        :param compressed: `bool`, check if LFP is compressed
        :param validate: `bool`, enable/disable lfp schema validation
        :return: True if path is a valid LFP and all criteria was matched
        """

        if not re.match(self.lfp_pattern, lfp_path):
            return False

        try:
            lfp = Lfp(lfp_path, self.print_help)
        except MemoryError:
            return False
        except Exception as e:
            w = "corrupt file: {}; {}".format(lfp_path, e)
            ToolWarn(w)
            return False

        if validate:
            self.validate(lfp)

        for criteria, actual in [(v2, lfp.is_v2),
                                 (raw, lfp.has_raw),
                                 (xraw, lfp.has_xraw),
                                 (warp, lfp.has_warp),
                                 (unpacked, lfp.has_unpacked),
                                 (compressed, lfp.has_compressed)]:

            if criteria is None:
                continue
            if criteria != actual:
                return False

        return lfp

    def verify_image_paths(self, lfp_path, image_paths):
        """verifies all images referenced in an unpacked LFP are present

        :param lfp_path: `str`, lfp_path being checked
        :param image_paths: `list`, absolute paths to images
        :raise: `ToolError` if any LFP image file is missing
        """

        for path in image_paths:
            e = "missing {} to pack LFP file {}".format(path, lfp_path)
            assert os.path.isfile(path), ToolError(e, self.print_help)


def _search_worker(q, done_q, types):
    """Tool.search multiprocessing worker"""

    tool = Tool()
    for item in iter(q.get, 'STOP'):
        index, file_path = item
        valid_lfp = tool.valid_lfp_file(file_path, **types)
        done_q.put(valid_lfp if valid_lfp else None)
