#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lytro Power Tools - webtool script"""

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
import os
import textwrap
import pprint

try:
    import lpt
except ImportError:
    import os
    import sys

    mod_dir = os.path.dirname(os.path.realpath(__file__))
    lpt_dir = os.path.abspath(os.path.join(mod_dir, '../..'))
    sys.path.insert(0, lpt_dir)
    import lpt

from lpt.utils.argutils import ArgumentParser
from lpt.utils.argutils import ArgUtils
from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.utils.utils import Utils
from lpt.web import config
from lpt.web.cmds import Cmds
from lpt.web.handle import Handle

__prog__ = 'webtool'
__version__ = '1.1.1'

utils = Utils()
handle = Handle()
argutils = ArgUtils()
msgutils = MsgUtils()
cmds = Cmds(verbose=config.db['verbose'])


def build():
    """build function and arguments for Web Tool

    :raise: `ToolError` if invalid arguments specified
    """

    #
    #
    # WEBTOOL
    #
    #

    host = config.loc_url.replace('https://', '')
    epilog = "Lytro Power Tools - Web {} Tool"

    parser = ArgumentParser(
        prog=__prog__,
        epilog=epilog.format('Management'),
        usage=__prog__ + ' ... ',
        description=(textwrap.dedent('''
        this program supplies management for creating, updating, deleting, and
        retrieving data for, {} (user account required) living pictures and
        albums'''.format(host))),
        formatter_class=argutils.formatter_class())

    subparsers = parser.add_subparsers()
    id_meta = 'ID'

    def extant_file_type(path):
        """`argparse` type: checks if path exists on the file system

        :param path: path to check
        :return: path if exists
        :raise: `ToolError` if file does not exist
        """

        err = "file does not exist: {}".format(path)
        assert os.path.exists(path), ToolError(err, parser.print_help)
        return path

    def picture_caption_type(caption):
        """`argparse` type: checks if the picture caption is <= 140 chars

        :param caption: `str`, to check
        :return: picture caption if appropriate length
        :raise: `ToolError` if caption longer than 140 chars
        """

        err = ("picture caption too long (length: {}, max: 140): \"{}\""
               .format(len(caption), caption))

        assert len(caption) <= 140, ToolError(err, parser.print_help)
        return caption

    def album_name_type(name):
        """`argparse` type: checks if the album name is <= 140 chars

        :param name: `str`, to check
        :return: album if appropriate length
        :raise: `ToolError` if name longer than 140 chars
        """

        err = ("album name too long (length: {}, max: 140): \"{}\""
               .format(len(name), name))
        assert len(name) <= 140, ToolError(err, parser.print_help)
        return name

    def album_description_type(desc):
        """`argparse` type: checks if the album description is <= 3000 chars

        :param desc: `str`, to check
        :return: album description  if appropriate length
        :raise: `ToolError` if description longer than 3000 chars
        """

        err = ("album description too long (length: {}, max: 3000): \"{}\""
               .format(len(desc), desc))
        assert len(desc) <= 3000, ToolError(err, parser.print_help)
        return desc

    def get_user():
        """get pictures.lytro.com username from user raw input

        :return: username
        """

        msg = "enter username for {}: ".format(host)
        return msgutils.msg(msg, type_='AUTH', input_=True)

    def get_pass(username):
        """get pictures.lytro.com password from user getpass input
        :param username: pictures.lytro.com username
        :return: password
        """

        msg = "enter password for user {} on {}: ".format(username, host)
        password = msgutils.msg(msg, type_='AUTH', getpass_=True, crlf='')
        return password

    parser.args_meta(dflt_verbose=config.db['verbose'])

    #
    # WEBTOOL AUTH PARSER
    #

    auth_parser = argparse.ArgumentParser(add_help=False)

    user_auth_group = auth_parser.add_argument_group('authentication')

    user_auth_group.add_argument(
        '-u', '--username',
        help="specify username; prompt if left blank ",
        default=config.db['username'],
        dest='username')

    user_auth_group.add_argument(
        '-p', '--password',
        help="specify password; prompt if left blank ",
        default=config.db['password'],
        dest='password')

    #
    # WEBTOOL ALBUM PARSER
    #

    album_parser = argparse.ArgumentParser(add_help=False)
    album_group = album_parser.add_argument_group('album')

    album_group.add_argument(
        '-n', '--name',
        help="album name (140 chars. max, default: auto-generated)",
        default=None,
        type=album_name_type,
        dest='name')

    album_group.add_argument(
        '-d', '--description',
        help="album description (3000 chars. max, default: auto-generated)",
        default=None,
        type=album_description_type,
        dest='desc')

    #
    #
    # WEBTOOL UPLOAD
    #
    #

    upload = subparsers.add_parser(
        'upload',
        description=(textwrap.dedent('''
        upload an individual LFP file, a list of LFP files, or a directory
        containing LFP files to {url}; pictures will be uploaded to a new
        album unless an existing album ID is specified;

        NOTE: if an existing album ID is specified, and other album arguments
        are specified (-d/--description | -n/--name | --public/--unlisted), the
        specified album will be updated to reflect these arguments'''
                                     .format(url=host))),
        help="execute operation on input LFP files or scanned directories",
        epilog=epilog.format('Upload'),
        formatter_class=argutils.formatter_class(m=48),
        parents=[auth_parser, album_parser])

    upload.set_defaults(func=cmds.cmd_upload, print_help=upload.print_help)

    upload.add_argument(
        '-i', '--lfp-in',
        nargs='+',
        required=True,
        help="execute operation on input LFP files or scanned directories")

    upload.add_argument(
        '-a', '--album-id',
        help="upload to specified album",
        default=None,
        metavar=id_meta,
        dest='album_id',
        type=int)

    #
    # WEBTOOL UPLOAD - ALBUM PRIVACY
    #

    upload_privacy = upload.add_argument_group('album privacy')
    upload_privacy = upload_privacy.add_mutually_exclusive_group()

    upload_privacy.add_argument(
        '--public',
        help="toggle album privacy status to public",
        default=None,
        action='store_true',
        dest='is_public')

    upload_privacy.add_argument(
        '--unlisted',
        help="toggle album privacy status to unlisted (default option)",
        default=None,
        action='store_false',
        dest='is_public')

    #
    # WEBTOOL UPLOAD - PICTURE CAPTION
    #

    upload_caption = upload.add_argument_group('picture caption')
    upload_caption = upload_caption.add_mutually_exclusive_group()

    upload_caption.add_argument(
        '--auto-caption',
        help="auto-generates picture captions; e.g. '01/15 - test_output.lfp'",
        default=False,
        action='store_true',
        dest='auto_caption')

    upload_caption.add_argument(
        '-c', '--caption',
        help="picture caption (140 char. max, default: None)",
        default=None,
        type=picture_caption_type,
        dest='caption')

    upload_caption.add_argument(
        '--caption-file',
        help="input CSV file containing captions; format: "
             "/absolute/path/to/picture.lfp,caption)",
        default=None,
        type=extant_file_type,
        dest='captions')

    #
    #
    # WEBTOOL ALBUM
    #
    #

    album_help = "retrieve information for, update, or create albums"
    album = subparsers.add_parser(
        'album',
        description=album_help,
        help=album_help,
        epilog=epilog.format('Album'),
        formatter_class=argutils.formatter_class(m=48),
        parents=[auth_parser, album_parser])

    album.set_defaults(func=cmds.cmd_album, print_help=album.print_help)

    album.add_argument(
        '-i', '--album-id',
        help="perform action on specified album ID; required for "
             "--update/-U | --get/-G actions",
        nargs='?',
        type=int,
        metavar=id_meta,
        default=None)

    #
    # WEBTOOL ALBUM - PRIVACY
    #

    album_privacy = album.add_argument_group('album privacy')
    album_privacy = album_privacy.add_mutually_exclusive_group()

    album_privacy.add_argument(
        '--public',
        help="toggle album privacy status to public",
        default=None,
        action='store_true',
        dest='is_public')

    album_privacy.add_argument(
        '--unlisted',
        help="toggle album privacy status to unlisted (default option)",
        default=None,
        action='store_false',
        dest='is_public')

    #
    # WEBTOOL ALBUM - ACTIONS
    #

    album_acts = album.add_argument_group('album actions')
    album_acts = album_acts.add_mutually_exclusive_group(required=True)

    album_acts.add_argument(
        '--get-all',
        help="retrieve information for all available albums",
        dest='album_action',
        const='get_all',
        action='store_const')

    album_acts.add_argument(
        '-G', '--get',
        help="retrieve information for specified album and its pictures",
        dest='album_action',
        const='get',
        action='store_const')

    album_acts.add_argument(
        '-U', '--update',
        help="update information for specified album; at least one "
             "album argument is required",
        dest='album_action',
        const='update',
        action='store_const')

    album_acts.add_argument(
        '-C', '--create',
        help="create an empty album; album arguments are optional",
        dest='album_action',
        const='create',
        action='store_const')

    album_acts.add_argument(
        '-D', '--delete',
        help="delete specified album; all other arguments are ignored",
        dest='album_action',
        const='delete',
        action='store_const')

    #
    #
    # WEBTOOL PICTURE
    #
    #

    picture_help = "retrieve information for or update pictures"
    picture = subparsers.add_parser(
        'picture',
        description=picture_help,
        help=picture_help,
        formatter_class=argutils.formatter_class(m=48),
        epilog=epilog.format('Picture'),
        parents=[auth_parser])

    picture.set_defaults(func=cmds.cmd_picture, print_help=picture.print_help)

    picture.add_argument(
        '-i', '--picture-id',
        help="perform action on specified picture ID; required for "
             "--update/-U | --get/-G | --delete/-D actions",
        nargs='?',
        type=int,
        metavar=id_meta,
        default=None)

    #
    # WEBTOOL PICTURE - CAPTION
    #

    picture_caption_group = picture.add_argument_group('caption')

    picture_caption_group.add_argument(
        '-c', '--caption',
        help="picture caption (140 char. max, default: None)",
        default=None,
        type=picture_caption_type,
        dest='caption')

    #
    # WEBTOOL PICTURE - ACTIONS
    #

    picture_acts = picture.add_argument_group('picture actions')
    picture_acts = picture_acts.add_mutually_exclusive_group(required=True)

    picture_acts.add_argument(
        '--get-all',
        help="retrieve information for all available pictures",
        dest='picture_action',
        const='get_all',
        action='store_const')

    picture_acts.add_argument(
        '-G', '--get',
        help="retrieve picture information for specified picture",
        dest='picture_action',
        const='get',
        action='store_const')

    picture_acts.add_argument(
        '-U', '--update',
        help="update information for specified picture (requires --caption)",
        dest='picture_action',
        const='update',
        action='store_const')

    picture_acts.add_argument(
        '-D', '--delete',
        help="delete specified picture",
        dest='picture_action',
        const='delete',
        action='store_const')

    args = parser.parse_args()

    for hand in [cmds.get.handle,
                 cmds.post.handle,
                 cmds.put.handle,
                 cmds.delete.handle]:
        hand.verbose = args.verbose

    nothing_to_do = ("nothing to do; --update/-U argument was called "
                     "but none of the {} arguments were called")

    if args.func == cmds.cmd_album and args.album_action == 'update':

        album_args = utils.any_([args.name, args.desc, args.is_public])
        e = nothing_to_do.format('album')
        assert album_args, ToolError(e, parser.print_help)

    elif args.func == cmds.cmd_picture and args.picture_action == 'update':

        picture_args = utils.any_(args.caption)
        e = nothing_to_do.format('picture')
        assert picture_args, ToolError(e, parser.print_help)

    if config.db['user_id'] and config.db['auth_token']:
        args.user_id = config.db['user_id']
        args.auth_token = config.db['auth_token']
    else:
        args.user_id = None
        args.auth_token = None
        if not args.username:
            args.username = get_user()
        if not args.password:
            args.password = get_pass(args.username)

    if args.debug:
        pprint.pprint(vars(args))

    args.func(args)


if __name__ == '__main__':
    build()
