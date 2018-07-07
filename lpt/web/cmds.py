# -*- coding: utf-8 -*-
"""Lytro Power Tools - web package - webtool core commands"""

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

from lpt.lfp.tool import Tool
from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.web.webcommon import WebCommon

tool = Tool()
msgutils = MsgUtils()


class Cmds(WebCommon):
    """core Web Tool commands

    :param verbose: `bool`, increase verbosity for HTTP/web calls
    """

    def __init__(self, verbose=False):
        WebCommon.__init__(self, verbose=verbose)

    def _set_print_help(self, args):
        """sets `argparse` help menu for current command"""

        self.print_help = args.print_help
        tool.set_print_help(args.print_help)

    #
    # CMDS - AUTHENTICATION
    #

    def _set_auth(self, args):
        """Web Tool authentication wrapper

        uploads living pictures to pictures.lytro.com
        :param args: `argparse.Namespace`, input args from Web Tool argparse
        """

        if args.user_id and args.auth_token:
            self.user_id = args.user_id
            self.auth_token = args.auth_token
            self.get_user()
        else:
            self.post_session(args.username, args.password)

    #
    # CMDS - UPLOAD
    #

    def cmd_upload(self, args):
        """Web Tool upload command

        uploads living pictures to pictures.lytro.com
        :param args: `argparse.Namespace`, input args from Web Tool argparse
        :raise: `ToolError` if no valid LFP files in `args.lfp_in`
        """

        self._set_print_help(args)
        self._set_auth(args)

        lfps = tool.search(args.lfp_in, warp=True, unpacked=False)

        assets = [x.path for x in lfps]
        picture_count = len(assets)

        e = "no valid LFP files found: {}".format(args.lfp_in)
        assert picture_count > 0, ToolError(e, self.print_help)

        msgutils.msg("uploading {} LFP(s)".format(picture_count))

        if (args.is_public or args.name or args.desc) and args.album_id:
            self.put_album(album_id=args.album_id,
                           name=args.name,
                           description=args.desc,
                           is_public=args.is_public)

        if args.album_id:
            album_id = args.album_id
            album = self.get_album(album_id)
            token = album['token']
            is_public = album['is_public']
        else:
            album_id, token = self.post_album(
                name=args.name,
                description=args.desc,
                is_public=args.is_public)
            is_public = args.is_public

        token_str = '' if is_public else '?token={}'.format(token)
        upload_id = self.post_upload(picture_count=picture_count)
        album_url = (self.obj_url.format(host=self.loc_url,
                                         username=self.username,
                                         type_='albums',
                                         id_=album_id,
                                         token=token_str))

        msgutils.msg("album location: {}".format(album_url))

        captions = self._captions_load(args.captions) if args.captions else {}

        def pad(a, b): return str(a).zfill(b)

        for i, asset in enumerate(assets, start=1):
            count = pad(i, len(str(picture_count)))
            caption_msg = ("{i} of {t} pictures: "
                           .format(i=count, t=picture_count) + '{}')

            msgutils.msg(caption_msg.format(asset))

            if args.caption:
                caption = args.caption
            elif args.auto_caption:
                filename = os.path.basename(asset)
                caption = caption_msg.format(filename)
            elif captions:
                caption = captions[asset] if asset in captions else None
            else:
                caption = None

            picture_id = self.post_picture(album_id=album_id,
                                           upload_id=upload_id,
                                           asset=asset,
                                           caption=caption)

            picture_url = (self.obj_url.format(host=self.loc_url,
                                               username=self.username,
                                               type_='pictures',
                                               id_=picture_id,
                                               token=token_str))

            msgutils.msg("picture location: {}".format(picture_url))

    #
    # CMDS - ALBUM
    #

    def cmd_album(self, args):
        """Web Tool album commands

            get_all : gets all albums
            get     : get album
            update  : update album
            create  : create album

        :param args: `argparse.Namespace`, input args from Web Tool argparse
        """

        self._set_print_help(args)
        self._set_auth(args)

        if args.album_action == 'get_all':
            self.cmd_album_get_all()
        elif args.album_action == 'get':
            self.cmd_album_get(args)
        elif args.album_action == 'update':
            self.cmd_album_put(args)
        elif args.album_action == 'create':
            self.cmd_album_post(args)
        elif args.album_action == 'delete':
            self.cmd_album_delete(args)

    #
    # CMDS - ALBUM - SUB-COMMANDS
    #

    def cmd_album_get_all(self):
        """get all user album information"""
        albums_raw = self._page_albums(self.username)
        albums_master = []
        for album in albums_raw:
            token = album['token']
            is_public = album['is_public']
            token_str = '' if is_public else '?token={}'.format(token)
            album_url = (self.obj_url.format(host=self.loc_url,
                                             username=self.username,
                                             type_='albums',
                                             id_=album['id'],
                                             token=token_str))
            albums_master.append({album_url: album})

        total = len(albums_master)
        msgutils.msg("albums found for user {user}: {total}"
                     .format(user=self.username, total=total))
        msgutils.dumps(albums_master)

    def cmd_album_get(self, args):
        """get individual user album information

        :param args: `argparse.Namespace`, input args from Web Tool argparse
        """

        self._set_print_help(args)
        get_message = ("getting album {id_} for user {user}"
                       .format(id_=args.album_id, user=self.username))

        msgutils.msg(get_message)
        album = self.get_album(args.album_id)
        token = album['token']
        is_public = album['is_public']

        token_str = '' if is_public else '?token={}'.format(token)

        album_url = (self.obj_url.format(host=self.loc_url,
                                         username=self.username,
                                         type_='albums',
                                         id_=album['id'],
                                         token=token_str))

        pictures_raw = self._page_pictures(self.username, args.album_id)
        pictures_master = []

        for picture in pictures_raw:
            picture_url = (self.obj_url.format(host=self.loc_url,
                                               username=self.username,
                                               type_='pictures',
                                               id_=picture['id'],
                                               token=token_str))

            pictures_master.append({picture_url: picture})

        total = len(pictures_master)
        master = {'album': {album_url: album}, 'pictures': pictures_master}
        msgutils.msg("pictures found for album {id_}: {total}"
                     .format(id_=args.album_id, total=total))
        msgutils.dumps(master)

    def cmd_album_put(self, args):
        """put (update) user album information

        :param args: `argparse.Namespace`, input args from Web Tool argparse
        """

        self._set_print_help(args)
        msgutils.msg("updating information for album {}"
                     .format(args.album_id))

        before = self.get_album(args.album_id)
        msgutils.msg("before:")
        msgutils.dumps(before)

        self.put_album(album_id=args.album_id,
                       name=args.name,
                       description=args.desc,
                       is_public=args.is_public)

        after = self.get_album(args.album_id)
        msgutils.msg("after:")
        msgutils.dumps(after)

    def cmd_album_post(self, args):
        """post (create) user album

        :param args: `argparse.Namespace`, input args from Web Tool argparse
        """

        self._set_print_help(args)
        msgutils.msg("creating album for user {}".format(self.username))

        album_id, token = self.post_album(
            name=args.name,
            description=args.desc,
            is_public=args.is_public)

        token_str = '' if args.is_public else '?token={}'.format(token)

        album_url = (self.obj_url.format(host=self.loc_url,
                                         username=self.username,
                                         type_='albums',
                                         id_=album_id,
                                         token=token_str))

        album = self.get_album(album_id)
        msgutils.msg("album location: {}".format(album_url))
        msgutils.dumps(album)

    def cmd_album_delete(self, args):
        """delete user album

        :param args: `argparse.Namespace`, input args from Web Tool argparse
        """

        self._set_print_help(args)
        msgutils.msg("deleting album {}".format(args.album_id))
        self.delete_album(args.album_id)

    #
    # CMDS - PICTURE
    #

    def cmd_picture(self, args):
        """Web Tool picture commands

            get_all : gets all pictures
            get     : get picture
            update  : update album

        :param args: `argparse.Namespace`, input args from Web Tool argparse
        """

        self._set_print_help(args)
        self._set_auth(args)

        if args.picture_action == 'get_all':
            self.cmd_picture_get_all()
        elif args.picture_action == 'get':
            self.cmd_picture_get(args)
        elif args.picture_action == 'update':
            self.cmd_picture_put(args)
        elif args.picture_action == 'delete':
            self.cmd_picture_delete(args)

    #
    # CMDS - PICTURE - SUB-COMMANDS
    #

    def cmd_picture_get_all(self):
        """get all user picture information
        """

        pictures_raw = self._page_pictures(self.username)
        pictures_master = []
        for picture in pictures_raw:
            token = picture['token']
            token_str = '?token={}'.format(token) if token else ''

            picture_url = (self.obj_url.format(host=self.loc_url,
                                               username=self.username,
                                               type_='pictures',
                                               id_=picture['id'],
                                               token=token_str))
            pictures_master.append({picture_url: picture})

        total = len(pictures_master)
        message = ("pictures found for user {user}: {total}"
                   .format(user=self.username, total=total))
        msgutils.msg(message)
        msgutils.dumps(pictures_master)

    def cmd_picture_get(self, args):
        """get individual user picture information

        :param args: `argparse.Namespace`, input args from Web Tool argparse
        :raise: `ToolError` if specified picture ID failed to ``GET``
        """

        self._set_print_help(args)
        msgutils.msg("getting information for picture {}"
                     .format(args.picture_id))

        picture = self._match_album_picture(self.username, args.picture_id)

        e = "could not perform lookup for picture {}".format(args.picture_id)
        assert picture, ToolError(e, self.print_help)

        token = picture['token']
        token_str = '?token={}'.format(token) if token else ''
        picture_url = (self.obj_url.format(host=self.loc_url,
                                           username=self.username,
                                           type_='pictures',
                                           id_=picture['id'],
                                           token=token_str))
        msgutils.dumps({picture_url: picture})

    def cmd_picture_put(self, args):
        """put (update) user picture information

        :param args: `argparse.Namespace`, input args from Web Tool argparse
        :raise: `ToolError` if specified picture ID failed to ``GET``
        """

        self._set_print_help(args)
        msgutils.msg("updating information for picture {}"
                     .format(args.picture_id))

        before = self._match_album_picture(self.username, args.picture_id)

        e = "could not perform lookup for picture {}".format(args.picture_id)
        assert before, ToolError(e, self.print_help)

        msgutils.msg("before:")
        msgutils.dumps(before)

        album_id = before['album_id']

        self.put_picture(album_id=album_id,
                         picture_id=args.picture_id,
                         caption=args.caption)

        after = self.get_picture(album_id=album_id,
                                 picture_id=args.picture_id)
        msgutils.msg("after:")
        msgutils.dumps(after)

    def cmd_picture_delete(self, args):
        """delete album picture

        :param args: `argparse.Namespace`, input args from Web Tool argparse
        :raise: `ToolError` if specified picture ID failed to ``GET``
        """

        self._set_print_help(args)
        msgutils.msg("deleting picture {}".format(args.picture_id))
        picture = self._match_album_picture(self.username, args.picture_id)

        e = "could not perform lookup for picture {}".format(args.picture_id)
        assert picture, ToolError(e, self.print_help)

        album_id = picture['album_id']

        self.delete_picture(album_id=album_id,
                            picture_id=args.picture_id)
