# -*- coding: utf-8 -*-
"""Lytro Power Tools - lfp package - LFP file (read) interaction"""

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

import copy
import json
import os
import re
import struct

from lpt.utils.argutils import ArgUtils
from lpt.utils.jsonutils import JsonUtils
from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.utils.utils import Utils

utils = Utils()
jsonutils = JsonUtils()
msgutils = MsgUtils()
argutils = ArgUtils()


class Lfp(object):
    """class object for reading LFP file

    :param path: `str`, path to LFP file
    :param print_help: `object`, passed to ToolError for command help menu
    :param store_raw: `bool`, store raw blob image data, WARNING: enabling
                      might cause unwanted MemoryError exceptions when working
                      with a large amount of LFP files
    :raise: `ToolError` if invalid LFP file
    """

    _file_magic_number = '\x89LFP\r\n\x1a\n'
    _master_magic_number = '\x89LFM\r\n\x1a\n'
    _chunk_magic_number = '\x89LFC\r\n\x1a\n'

    _header_struct = struct.Struct('>8sii')
    _blob_struct = struct.Struct('>8sq80s')
    _alignment = 16

    _recipe_pattern = re.compile('^recipe([0-9]+)?$')

    def __init__(self, path, print_help=object, store_raw=False):

        self.print_help = self.set_print_help(print_help)
        self.path = path
        self._store_raw = store_raw
        self.file_size = os.path.getsize(path)

        try:
            self.blobs = self._get_blobs
        except Exception as e:
            raise ToolError(e, self.print_help)
        else:
            e = "not a valid LFP file : " + self.path
            assert self.blobs, ToolError(e, self.print_help)

        self._master = {}
        self._ref_md = {}
        self.picture = {}
        self.private = []
        self.public = []
        self.master = self._get_master

    @staticmethod
    def set_print_help(print_help):
        """sets `argparse` help menu for current command
        :param print_help: `object`, passed to ToolError for command help menu
        """

        argutils.set_print_help(print_help)
        jsonutils.set_print_help(print_help)
        utils.set_print_help(print_help)
        return print_help

    @property
    def _acceleration_key(self):
        """:return: appropriate acceleration key for LFP version"""

        return self._v_key('acceleration')

    @property
    def _accelerations(self):
        """:return: LFP accelerations"""

        key = self._acceleration_key
        obj = self.picture['picture'] if self.is_v1 else self.picture
        return obj[key] if key in obj else []

    @property
    def _blobs_metadata(self):
        """:return: metadata from all blobs in LFP"""

        blobs_metadata = {}
        for ref, blob in self.blobs.items():
            blobs_metadata[ref] = blob.metadata
        return blobs_metadata

    @staticmethod
    def _check_accel(accelerations, key):
        """:return: checks LFP accelerations for specified key"""

        return [x[key] for a in accelerations for x in a if key in x]

    def _check_kinds(self, kind):
        """:return: checks LFP frame or view kinds for specified kind"""

        return any([k == kind for k in self._lfp_kinds])

    def _check_refs(self, ref):
        """:return: checks LFP frames for specified reference"""

        return any([ref in f['frame'] for f in self._frames])

    @property
    def _frame_accelerations(self):
        """:return: LFP acceleration metadata"""

        key = self._acceleration_key
        return [f[key] for f in self._frames if key in f and f[key]]

    @property
    def _frame_key(self):
        """:return: appropriate frame key for LFP version"""

        return self._v_key('frame')

    @property
    def _frame_kinds(self):
        """:return: acceleration kinds from LFP frame metadata"""

        return self._check_accel(self._frame_accelerations, 'kind')

    @property
    def _frames(self):
        """:return: LFP frame metadata"""

        key = self._frame_key
        obj = self.picture['picture'] if self.is_v1 else self.picture
        return obj[key] if key in obj else []

    @property
    def _get_blobs(self):
        """:return: decoded LFP file blob data"""

        decoder = json.JSONDecoder()
        blobs = {}

        with open(self.path, 'rb') as f:
            f.read(self._header_struct.size)

            while f.tell() < self.file_size:
                data = f.read(self._blob_struct.size)
                magic, length, ref = self._blob_struct.unpack(data)
                ref = ref.rstrip('\x00')
                blob = f.read(length)

                try:
                    json_data, end = decoder.raw_decode(blob)
                except ValueError:
                    json_data = {}
                    end = 0

                if self._store_raw:
                    blob = None if end and len(blob) == end else blob[end:]
                else:
                    del blob
                    blob = None

                encoded_ref = ref.encode('utf-8')
                blobs[encoded_ref] = _Blob(magic_number=magic,
                                           metadata=json_data,
                                           blob=blob)

                if f.tell() % self._alignment:
                    f.read(self._alignment - f.tell() % self._alignment)

        return blobs

    def _get_hashes(self, ref):
        """:return: sha hashes for provided reference from LFP metadata"""

        return [f['frame'][ref] for f in self._frames if ref in f['frame']]

    @property
    def _get_master(self):
        """:return: LFP master metadata"""

        sha1 = re.compile(r'^sha1-[0-9a-f]{40}$')
        blob_md = self._blobs_metadata
        self.picture = blob_md[self._master_sha]
        master = {'master': self.picture}
        self._master.update(copy.deepcopy(master))

        paths = utils.search_dict(master, '')
        ref_paths = [(p, v) for p, v in paths if re.match(sha1, str(v))]

        for path, sha in ref_paths:

            path = list(path)
            ref = path.pop()
            new = ref.replace('Ref', '')
            parents = [x for x in path]
            parent = utils.get_from_dict(self._master, parents)
            path.append(new)

            if sha in blob_md:
                md = blob_md[sha]

                if not md:
                    continue

                kw = {'map_list': path, 'value': md}
                utils.set_in_dict(self._master, **kw)
                self._ref_md[new] = parent[new]

                if new not in ('metadata', 'privateMetadata'):
                    continue

                if new == 'privateMetadata':
                    self.private.append(parent[new])
                if new == 'metadata':
                    self.public.append(parent[new])

                utils.set_in_dict(master, **kw)
                del parent[ref]

        return master

    @property
    def _image_accelerations(self):
        """:return: LFP acceleration metadata"""

        key = self._v_key('image')
        return [f[key] for f in self._accelerations if key in f and f[key]]

    @property
    def _image_key(self):
        """:return: appropriate image key for LFP version"""

        return 'perImage' if self.is_v2 else 'imageArray'

    @property
    def _kind_key(self):
        """:return: appropriate kind key for LFP version"""

        return 'kind' if self.is_v2 else 'type'

    @property
    def _lfp_kinds(self):
        """:return: all data kinds from LFP file"""

        return self._frame_kinds + self._view_kinds

    @property
    def _master_sha(self):
        """:return: master sha1 reference from blob data"""

        for sha, blob in self.blobs.items():
            if blob.magic_number == self._master_magic_number:
                return sha

    def _v_key(self, key):
        """:return: appropriate keyword for LFP version"""

        return key + ('s' if self.is_v2 else 'Array')

    @property
    def _view_accelerations(self):
        """:return: LFP acceleration metadata"""

        key = self._acceleration_key
        return [f[key] for f in self._views if key in f and f[key]]

    @property
    def _view_depth_maps(self):
        """:return: depth map information from LFP frame metadata"""

        return self._check_accel(self._view_accelerations, 'depthMap')

    @property
    def _view_key(self):
        """:return: appropriate view key for LFP version"""

        return self._v_key('view')

    @property
    def _view_kinds(self):
        """:return: acceleration kinds from LFP frame metadata"""

        return self._check_accel(self._view_accelerations, 'kind')

    @property
    def _views(self):
        """:return: LFP view metadata"""

        key = self._view_key
        obj = self.picture['picture'] if self.is_v1 else self.picture
        return obj[key] if key in obj else []

    @property
    def depth_maps(self):
        """LFP depth map information

        :return: all depth map meta information
        """

        if self.is_v1:
            accels = self._accelerations
        else:
            accels = sum(self._view_accelerations, [])

        return [a['depthMap'] for a in accels if 'depthMap' in a]

    @property
    def has_compressed(self):
        """:return: True if LFP contains compressed data"""

        return self._check_kinds('compressed')

    @property
    def has_focus(self):
        """:return: True if LFP contains a focus stack"""

        return self._check_kinds('focusStack')

    @property
    def has_perspective(self):
        """:return: True if LFP contains a perspective shift stack"""

        return self._check_kinds('edofPerspective')

    @property
    def has_pre_adjust(self):
        """:return: True if LFP contains pre-adjusted data"""

        return self._check_kinds('edofWarpPreAdjust')

    @property
    def has_raw(self):
        """:return: True if LFP has raw data"""

        refs = self._get_hashes('imageRef')
        return any([r for r in refs if r in self.blobs])

    @property
    def has_unpacked(self):
        """:return: True if LFP contains unpacked warp data"""

        if not self.has_warp:
            return False

        return any(['imagePath' in i for i in self._view_depth_maps])

    @property
    def has_warp(self):
        """:return: True if LFP contains a warp stack"""

        return self._check_kinds('edofWarp')

    @property
    def has_xraw(self):
        """:return: True if LFP contains xraw data"""

        return self._check_refs('modulationDataRef')

    @property
    def images(self):
        """LFP image information

        :return: all image meta information
        """

        accel_key = self._v_key('acceleration')
        image_key = self._image_key
        kind_key = self._kind_key
        h = 'height'
        w = 'width'
        t = 'type'
        master = {}

        def _kind(x): return x[kind_key] if kind_key in x else ''

        if self.is_v1:
            md = 'metadataArray'
            bi = 'blockOfImages'
            vc = 'vendorContent'

            for accel in self._accelerations:

                kind = _kind(accel)

                if vc not in accel:
                    continue

                content = accel[vc]

                if h in content and w in content:
                    items = content.items()
                    image = {k: v for k, v in items if
                             not isinstance(v, dict)}
                    image[t] = accel[t] if t in accel else ''
                    images = [image]
                elif bi in content:
                    images = content[bi][md]
                elif image_key in content:
                    images = content[image_key]
                else:
                    continue

                if kind not in master:
                    master[kind] = []

                master[kind].append(images)

        else:

            pf = 'perFrame'

            def _scrape(obj):
                if not all([image_key in obj, h in obj, w in obj]):
                    return
                scrape = {h: obj[h], w: obj[w], image_key: obj[image_key]}
                master[kind].append(scrape)

            for view in self._views:
                if accel_key not in view:
                    continue

                accels = view[accel_key]
                for accel in accels:
                    kind = _kind(accel)
                    if kind not in master:
                        master[kind] = []
                    if pf in accel:
                        [_scrape(frame) for frame in accel[pf]]
                    _scrape(accel)

        return master

    @property
    def is_v1(self):
        """:return: True if valid v1 LFP"""

        return 'picture' in self.picture

    @property
    def is_v2(self):
        """:return: True if valid v2 LFP"""

        return 'views' in self.picture

    @property
    def picture_schema(self):
        """LFP picture schema information

        :return: all picture schema paths from LFP
        """

        if self.is_v1:
            return ''
        md = self.picture
        return md['schema'] if 'schema' in md else ''

    @property
    def private_schema(self):
        """LFP private schema information

        :return: all private schema paths from LFP
        """

        if self.is_v1:
            return ''

        key = 'privateMetadataRef'
        md = self.private

        if md and key in md[0]:
            md = [x[key] for x in md]

        return [x['schema'] for x in md if x and 'schema' in x]

    @property
    def public_schema(self):
        """LFP public schema information

        :return: all public schema paths from LFP
        """

        if self.is_v1:
            return ''
        key = 'metadataRef'
        md = self.public

        if md and key in md[0]:
            md = [x[key] for x in md]

        return [x['schema'] for x in md if x and 'schema' in x]

    @property
    def raw_dimensions(self):
        """LFP raw image dimensions

        :return: all raw image dimensions
        """

        heights = []
        widths = []

        for md in self.public:
            if 'image' not in md:
                continue
            image = md['image']

            if 'height' in image and 'width' in image:
                h = image['height']
                w = image['width']
                heights.append(h)
                widths.append(w)

        return zip(heights, widths)


class _Blob(object):
    """data blobs with extracted metadata

    :param magic_number: `struct`, blob identifier
    :param metadata: `dict`, metadata for LFP blob
    :param blob: `binary`, raw LFP blob data
    """

    def __init__(self, magic_number, metadata, blob=None):
        self.magic_number = magic_number
        self.metadata = metadata
        self.raw_data = blob
