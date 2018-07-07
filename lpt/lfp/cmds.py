# -*- coding: utf-8 -*-
"""Lytro Power Tools - lfp package - core lfptool commands"""

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
import multiprocessing
import numpy as np

from pprint import pprint
from functools import partial
from copy import copy

from lpt.lfp.tnt import Tnt
from lpt.lfp.tntcommon import TntCommon
from lpt.lfp.tool import Tool
from lpt.recipe.make import Generator
from lpt.recipe.make import Make
from lpt.utils.argutils import ArgUtils
from lpt.utils.calcutils import CalcUtils
from lpt.utils.jsonutils import JsonUtils
from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.utils.msgutils import ToolWarn
from lpt.utils.utils import Utils

tnt = Tnt()
make = Make()
tool = Tool()
utils = Utils()
argutils = ArgUtils()
msgutils = MsgUtils()
calcutils = CalcUtils()
jsonutils = JsonUtils()

od = collections.OrderedDict
all_or_none = argutils.all_or_none
arg_format = argutils.arg_format
any_ = utils.any_
_verbose = False


class Cmds(TntCommon):
    """core LFP Tool commands

    :param kwargs: `dict`, keyword arguments passed to parent class `TntCommon`
    """

    def __init__(self, **kwargs):
        TntCommon.__init__(self, **kwargs)

    def _set_print_help(self, args):
        """sets `argparse` help menu for current command"""

        self.print_help = args.print_help
        tnt.set_print_help(args.print_help)
        tool.set_print_help(args.print_help)
        utils.set_print_help(args.print_help)
        argutils.set_print_help(args.print_help)
        jsonutils.set_print_help(args.print_help)
        calcutils.set_print_help(args.print_help)

    def _assert_src(self, src, paths, cmd, raw_in=False, range_=(0, 0)):
        """:raise: `ToolError`, if no valid LFPs found for current command"""

        s = 'RAW' if raw_in else 'LFP'
        e = cmd + ": no valid {} files found".format(s)

        if range_[1]:
            a, b = range_
            e += " with range: {} - {}".format(a, b)

        e += ": " + ','.join(paths)
        assert src, ToolError(e, self.print_help)

    def _multiprocess(self, worker, master, processors=1, **kwargs):
        """multiprocessing handler for commands"""

        lock = multiprocessing.Lock() if processors > 1 else None
        queue = multiprocessing.JoinableQueue()
        procs = []
        args = queue, kwargs, lock, self.verbose

        for _ in range(processors):
            procs.append(multiprocessing.Process(target=worker, args=args))
            procs[-1].daemon = True
            procs[-1].start()

        [queue.put(x) for x in master]
        queue.join()

        [queue.put('STOP') for _ in procs]
        queue.join()

        [p.join() for p in procs]

    @staticmethod
    def _mutual(args, action):
        """checks for conflicting tnt arguments; warns if conflict present"""

        def arg(a): return arg_format(a, split='_', join='-', pre='--')
        dests = tnt.dests(combine=False)
        items = args.__dict__.items()
        act = getattr(tnt, action)
        act_arg = act.arg_alt or act.arg

        for key, value in items:
            if not any_(value, iter_=False):
                continue
            if key not in dests:
                continue
            if key == 'calibration_in':
                continue

            cls = getattr(tnt, key)
            nix = [x for x in tnt.actions if x not in cls.actions]
            if action not in nix:
                continue

            w = act_arg + ": ignoring incompatibility: " + cls.arg
            ToolWarn(w)

        if hasattr(args, 'recipe_in') and args.recipe_in:
            overrides = tnt.recipe_in.overrides
            for obj in overrides:
                if args.__dict__[obj]:
                    w = "using --recipe-in overrides " + arg(obj)
                    ToolWarn(w)

    def _rep_sanity(self, action, rep, rep_type, options):
        """checks imagerep/depthrep compatibility with the chosen action

        :raise: `ToolError` if representation not in available options
        """

        arg = '--' + action.replace('_', '-')
        opt = ', '.join(options)

        e = ("{}: invalid {} choice: {} (choose from {})"
             .format(arg, rep_type, rep, opt))

        assert rep in options, ToolError(e, self.print_help)

    def batch(self, args):
        """LFP Tool batch raw processing command

        :param args: `argparse.Namespace`, input arguments from LFP Tool
        """

        if self.debug:
            pprint(vars(args))

        self._set_print_help(args)

        msg = msgutils.msg
        status = partial(msgutils.status, answer=True)

        def msg_item(a, b):
            msg(msgutils.item(a, b, rjust=17), indent=True)

        dir_out = self._check_dir(args.dir_out) if args.dir_out else None
        imagerep = args.imagerep or self._db['imagerep_raw_image_out']

        src = tool.search(args.paths, raw=True,
                          file_pattern=args.file_pattern,
                          file_range=args.file_range,
                          processors=args.processors)

        self._assert_src(src, args.paths, 'batch', range_=args.file_range)
        paths = [x.path for x in src]
        s_total = len(paths)

        def meta(): return msgutils.msg_meta()[0]
        read = meta() + status("reading recipe", count=0)

        gen = Generator(args.recipe_in, total=s_total)

        with msgutils.msg_indicator(read):
            gen.init()
            start, end = gen.recipe_in.duration

        if args.per_lfp:
            lin = np.linspace(0, end, args.per_lfp)
            per_range = range(args.per_lfp)
            cfg_queue = [(p, lin[i]) for p in paths for i in per_range]

        else:
            lin = np.linspace(0, end, s_total)
            cfg_queue = [(p, lin[i]) for i, p in enumerate(paths)]

        pers_u = args.perspective_u
        pers_v = args.perspective_v
        argutils.lens_match(perspective_u=pers_u, perspective_v=pers_v)

        if pers_u and pers_v:
            uv_pairs = [(u, pers_v[i]) for i, u in enumerate(pers_u)]
        else:
            uv_pairs = [(None, None)]

        master = []
        count = 0
        per_lfp_index = []

        for q in cfg_queue:
            q = list(q)
            for u, v in uv_pairs:
                count += 1

                if args.per_lfp:
                    path, index = q
                    per_lfp_index.append(path)
                    per_count = per_lfp_index.count(path)
                    master.append([per_count, u, v, path, index])

                else:
                    master.append([count, u, v] + q)

        uvs = len(uv_pairs)
        pad = len(str(len(master)))
        batch_id = partial(self._batch_id, count=uvs, end=end, pad=pad)

        read = meta() + status("making recipes", count=0)

        process_queue = []
        with msgutils.msg_indicator(read):

            for item in master:

                i, u, v, lfp, mark = item
                dir_, base, ext = self._split_path(lfp)
                name = batch_id(base, time=mark, i=i, u=u, v=v)

                image_out = self.image_out(dir_out or dir_, name, imagerep)
                image_out = utils.sanitize_path(image_out)

                dir_, base, ext = self._split_path(image_out)
                recipe_out = os.path.join(dir_, base + '.json')

                if any_(u) and any_(v):
                    gen.recipe_out['viewPerspectiveU'](u)
                    gen.recipe_out['viewPerspectiveV'](v)

                if gen.recipe_out.view_store_no_zulu:
                    recipe_in = gen(mark, recipe_out=recipe_out)
                else:
                    recipe_in = None

                process_queue.append((i, lfp, image_out, recipe_in))

        total = len(process_queue)

        msg("totals:")
        msg_item("LFPs", s_total)
        msg_item("perspectives", len(uv_pairs))
        msg_item("per LFP", args.per_lfp)
        msg_item("rendered images", total)

        if self.verbose:
            marks = [cfg[1] for cfg in cfg_queue]
            review = gen.review(marks)
            msg("perspective u/v:")
            msgutils.dumps(uv_pairs)
            msg("recipe:")
            msgutils.dumps(review)

        self._multiprocess(
            worker=_batch_worker,
            master=process_queue,
            processors=args.processors,
            threads=args.threads,
            depth_in=args.depth_in,
            height=args.height,
            imagerep=args.imagerep,
            width=args.width,
            calibration_in=args.calibration_in)

    def four_d(self, args):
        """LFP Tool 4D coordinate calculation command

        calculates x/y/u/v coordinates for given lightfield row/column

        :param args: `argparse.Namespace`, input arguments from LFP Tool
        """

        if self.debug:
            pprint(vars(args))

        self._set_print_help(args)

        msgutils.status("calculating 4d coordinates (row {r} : column {c})"
                        .format(r=args.row, c=args.column))

        coords = calcutils.four_d_coord(args.row, args.column).items()
        coords = od(sorted(coords))
        msgutils.dumps(coords)

    def info(self, args):
        """LFP Tool LFP file information command

        outputs (to screen) or writes (to disk) LFP file:
            master metadata
            recipe view parameters metadata
            extended metadata

        provides json metadata property search

        :param args: `argparse.Namespace`, input arguments from LFP Tool
        """

        if self.debug:
            pprint(vars(args))

        self._set_print_help(args)

        msg = "{} LFP file information"
        src = tool.search(args.paths,
                          file_pattern=args.file_pattern,
                          file_range=args.file_range,
                          processors=args.processors)

        self._assert_src(src, args.paths, 'info', range_=args.file_range)
        search_dict = partial(utils.search_dict, exact=args.exact, join='::')

        for i, lfp in enumerate(src, start=1):

            basedir, basename, ext = self._split_path(lfp.path)

            def json_out(x=''): return self.output_json(basedir, basename + x)

            status = partial(msgutils.status, src=lfp.path, count=i)

            picture = lfp.picture
            private = lfp.private
            public = lfp.public

            data = {
                'picture': picture,
                'private': private,
                'public': public}

            if args.property:

                def search(f): return search_dict(obj=data, field=f)

                data = lfp.master
                status(msg.format("querying"))
                result = {p: search(p) for p in args.property}
                msgutils.status("results found", count=i)
                msgutils.dumps(result)

            elif args.json_out:

                picture_out = json_out()
                private_out = json_out('_private')
                public_out = json_out('_public')

                picture_out = utils.sanitize_path(picture_out)
                private_out = utils.sanitize_path(private_out)
                public_out = utils.sanitize_path(public_out)

                status(msg.format("writing"))
                status(src=None, dest=picture_out)
                status(src=None, dest=private_out)
                status(src=None, dest=public_out)

                utils.write(picture_out, picture)
                utils.write(private_out, private)
                utils.write(public_out, public)

            elif args.validate:

                status(msg.format("validating"))
                tool.validate(lfp)

            else:

                status(msg.format("displaying"))
                msgutils.dumps(data, indent=False)

    def raw(self, args):
        """LFP Tool raw processing command

        outputs:
            standard/lightfield/depth map image
            warp LFP files
            unpacked warp LFP images and metadata
            base recipe metadata from raw LFP files

        :param args: `argparse.Namespace`, input arguments from LFP Tool
        """

        if self.debug:
            pprint(vars(args))

        self._set_print_help(args)
        self._mutual(args, args.raw_action)
        raw_in = args.raw_action == 'raw2lfp'

        image = []

        if args.raw_action == 'depth_out':
            depth = tnt.depthrep_depth.choices
        else:
            depth = tnt.depthrep.choices

        if args.raw_action in ('lfp_out', 'unpack'):
            image = tnt.imagerep_lfp.choices
        elif args.raw_action == 'image_out':
            image = tnt.imagerep.choices
        elif args.raw_action == 'eslf_out':
            image = tnt.imagerep_eslf.choices

        if image and args.imagerep:
            _args = args.raw_action, args.imagerep, 'imagerep', image
            self._rep_sanity(*_args)

        if args.depthrep:
            _args = args.raw_action, args.depthrep, 'depthrep', depth
            self._rep_sanity(*_args)

        if raw_in:
            src = tool.search_raw(args.paths)
            src = [x for x in src]
        else:
            src = tool.search(args.paths, raw=True,
                              file_range=args.file_range,
                              file_pattern=args.file_pattern,
                              processors=args.processors)

        self._assert_src(src, args.paths, 'raw',
                         raw_in=raw_in,
                         range_=args.file_range)

        argutils.lens_match(perspective_u=args.perspective_u,
                            perspective_v=args.perspective_v)

        dir_out = self._check_dir(args.dir_out)
        args.recipe_in = self.set_recipe_in(args.recipe_in)

        kwds = {}
        if args.raw_action == 'image_out':
            kwds = dict(threads=args.threads,
                        calibration_in=args.calibration_in,
                        depth_in=args.depth_in,
                        dir_out=dir_out,
                        focus=args.focus,
                        height=args.height,
                        imagerep=args.imagerep,
                        orientation=args.orientation,
                        perspective_u=args.perspective_u,
                        perspective_v=args.perspective_v,
                        recipe_in=args.recipe_in,
                        width=args.width)

        elif args.raw_action == 'lfp_out':
            kwds = dict(threads=args.threads,
                        calibration_in=args.calibration_in,
                        depth_in=args.depth_in,
                        depthrep=args.depthrep,
                        dir_out=dir_out,
                        height=args.height,
                        imagerep=args.imagerep,
                        orientation=args.orientation,
                        perspective_u=args.perspective_u,
                        perspective_v=args.perspective_v,
                        recipe_in=args.recipe_in,
                        width=args.width)

        elif args.raw_action == 'transcode':
            kwds = dict(threads=args.threads)

        elif args.raw_action == 'depth_out':
            kwds = dict(threads=args.threads,
                        dir_out=dir_out,
                        imagerep=args.imagerep,
                        depthrep=args.depthrep,
                        depth_in=args.depth_in,
                        orientation=args.orientation,
                        calibration_in=args.calibration_in)

        elif args.raw_action == 'eslf_out':
            kwds = dict(threads=args.threads,
                        calibration_in=args.calibration_in,
                        dir_out=dir_out,
                        imagerep=args.imagerep)

        elif args.raw_action == 'recipe_out':
            kwds = dict(threads=args.threads,
                        dir_out=dir_out)

        elif args.raw_action == 'unpack':
            kwds = dict(threads=args.threads,
                        calibration_in=args.calibration_in,
                        depth_in=args.depth_in,
                        depthrep=args.depthrep,
                        dir_out=dir_out,
                        height=args.height,
                        imagerep=args.imagerep,
                        orientation=args.orientation,
                        perspective_u=args.perspective_u,
                        perspective_v=args.perspective_v,
                        recipe_in=args.recipe_in,
                        width=args.width)

        elif args.raw_action == 'lfr2xraw':
            kwds = dict(threads=args.threads,
                        calibration_in=args.calibration_in,
                        dir_out=dir_out)

        elif args.raw_action == 'lfp2raw':
            kwds = dict(threads=args.threads,
                        dir_out=dir_out)

        elif args.raw_action == 'raw2lfp':
            kwds = dict(threads=args.threads,
                        dir_out=dir_out)

        def path(): return x, y if raw_in else y.path

        paths = [path() for x, y in enumerate(src, start=1)]

        kwds['action'] = args.raw_action

        self._multiprocess(
            worker=_raw_worker,
            master=paths,
            processors=args.processors, **kwds)

    def warp(self, args):
        """LFP Tool warp processing command

        outputs:
            packed warp LFP files from unpacked warp LFP file
            unpacked warp LFP file from packed warp LFP

        :param args: `argparse.Namespace`, input arguments from LFP Tool
        """

        if self.debug:
            pprint(vars(args))

        self._set_print_help(args)
        self._mutual(args, args.warp_action)

        if args.warp_action == 'pack':
            unpacked = True
        elif args.warp_action == 'unpack':
            unpacked = False
        else:
            unpacked = None

        src = tool.search(args.paths, warp=True, unpacked=unpacked,
                          file_pattern=args.file_pattern,
                          file_range=args.file_range,
                          processors=args.processors)

        self._assert_src(src, args.paths, 'warp', range_=args.file_range)

        kwds = {}
        if args.warp_action == 'pack':
            kwds = dict(threads=args.threads,
                        depthrep=args.depthrep,
                        dir_out=args.dir_out,
                        height=args.height,
                        imagerep=args.imagerep,
                        width=args.width)

        elif args.warp_action == 'transcode':
            kwds = dict(threads=args.threads)

        elif args.warp_action == 'unpack':
            kwds = dict(threads=args.threads,
                        depthrep=args.depthrep,
                        dir_out=args.dir_out,
                        height=args.height,
                        imagerep=args.imagerep,
                        width=args.width)

        elif args.warp_action == 'recipe_out':
            kwds = dict(threads=args.threads,
                        dir_out=args.dir_out)

        kwds['action'] = args.warp_action
        paths = [(x, y.path) for x, y in enumerate(src, start=1)]

        self._multiprocess(
            worker=_warp_worker,
            master=paths,
            processors=args.processors,
            **kwds)


_work_cmds = TntCommon()


def _batch_worker(task, kwds, lock=None, verbose=False):
    """raw batch multiprocessing worker"""

    process = partial(_work_cmds.raw_image_out, **kwds)

    _work_cmds.lock = lock
    _work_cmds.verbose = verbose
    _work_cmds.validate_recipe = False

    for item in iter(task.get, 'STOP'):
        i, lfp, image, recipe = item
        process(lfp, i=i, image_out=image, recipe_in=recipe)
        task.task_done()

    task.task_done()


def _raw_worker(task, kwds, lock=None, verbose=False):

    action = kwds['action']
    del kwds['action']

    _work_cmds.lock = lock
    _work_cmds.verbose = verbose
    _work_cmds.validate_recipe = False

    for item in iter(task.get, 'STOP'):

        i, path = item
        kw = copy(kwds)

        if action == 'image_out':
            image_out = partial(_work_cmds.raw_image_out, i=i)

            pers_u = [u for u in kw['perspective_u']]
            pers_v = [v for v in kw['perspective_v']]

            del kw['perspective_u']
            del kw['perspective_v']

            if pers_u:
                for j, u in enumerate(pers_u):
                    v = pers_v[j]
                    image_out(path, perspective_u=u, perspective_v=v, **kw)
            else:
                image_out(path, **kw)

        elif action == 'lfp_out':
            _work_cmds.raw_lfp_out(path, i=i, **kw)

        elif action == 'transcode':
            _work_cmds.raw_transcode(path, i=i, **kw)

        elif action == 'depth_out':
            _work_cmds.raw_depth_out(path, i=i, **kw)

        elif action == 'eslf_out':
            _work_cmds.raw_eslf_out(path, i=i, **kw)

        elif action == 'recipe_out':
            _work_cmds.recipe_out(path, i=i, **kw)

        elif action == 'unpack':
            _work_cmds.raw_unpack(path, i=i, **kw)

        elif action == 'lfr2xraw':
            _work_cmds.raw_lfr2xraw(path, i=i, **kw)

        elif action == 'lfp2raw':
            _work_cmds.raw_lfp2raw(path, i=i, **kw)

        elif action == 'raw2lfp':
            _work_cmds.raw_raw2lfp(path, i=i, **kw)

        task.task_done()

    task.task_done()


def _warp_worker(task, kwds, lock=None, verbose=False):
    """warp multiprocessing worker"""

    action = kwds['action']
    del kwds['action']

    _work_cmds.lock = lock
    _work_cmds.verbose = verbose

    for item in iter(task.get, 'STOP'):

        i, path = item

        if action == 'pack':
            _work_cmds.warp_pack(path, i=i, **kwds)

        elif action == 'transcode':
            _work_cmds.warp_transcode(path, i=i, **kwds)

        elif action == 'unpack':
            _work_cmds.warp_unpack(path, i=i, **kwds)

        elif action == 'recipe_out':
            _work_cmds.recipe_out(path, i=i, **kwds)

        task.task_done()

    task.task_done()
