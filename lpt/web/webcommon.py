# -*- coding: utf-8 -*-
"""Lytro Power Tools - web package - common web functions"""

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

from functools import partial

from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.web import config
from lpt.web import controllers
from lpt.web.handle import Handle

handle = Handle()
msgutils = MsgUtils()


class WebCommon(object):
    """common Web Tool functions

    :param verbose: `bool`, increase HTTP call verbosity
    """

    api_url = config.api_url
    loc_url = config.loc_url
    base_headers = config.base_headers
    limit_default = offset_default = 25
    limit_max = 1000

    album_fields = ['active_pictures_count', 'created_at', 'deleted',
                    'description', 'is_public', 'name', 'updated_at']
    picture_fields = ['views_count', 'album_id', 'id', 'deleted', 'updated_at',
                      'likes_count', 'created_at', 'caption', 'token']

    obj_url = "{host}/{username}/{type_}/{id_}{token}"

    auth_token = None
    user_id = None
    username = None

    print_help = object

    def __init__(self, verbose=False):
        self.get = controllers.Get(
            url=self.api_url,
            base_headers=self.base_headers,
            verbose=verbose)

        self.delete = controllers.Delete(
            url=self.api_url,
            base_headers=self.base_headers,
            verbose=verbose)

        self.post = controllers.Post(
            url=self.api_url,
            base_headers=self.base_headers,
            verbose=verbose)

        self.put = controllers.Put(
            url=self.api_url,
            base_headers=self.base_headers,
            verbose=verbose)

    #
    # BASE - POST
    #

    def post_session(self, username, password):
        """posts a pictures.lytro.com session

        needed to gather user id, authentication token
        required as first action before executing other functions

        :param username: `str`, pictures.lytro.com username
        :param password: `str`, pictures.lytro.com password
        """

        response = self.post.session(
            username=username,
            password=password)

        self._assert_response(response)

        self.user_id = response['data']['user']['id']
        self.username = response['data']['user']['username']
        self.auth_token = response['data']['authentication_token']

    def post_album(self, name=None, description=None, is_public=False):
        """posts web album

        :param name: `str`, album name
        :param description: `str`, album description
        :param is_public: `bool`, album privacy setting
        :return: created album id
        """

        response = self.post.user_album(
            user_id=self.user_id,
            name=name,
            description=description,
            is_public=is_public,
            auth_token=self.auth_token)

        self._assert_response(response)
        return response['data']['album_id'], response['data']['token']

    def post_picture(self, asset, album_id=None, upload_id=None, caption=None):
        """posts album picture

        :param asset: `str`, LFP asset for upload
        :param album_id: `int`, album id to post picture to
        :param upload_id: `int`, upload identifier
        :param caption: `str`, picture caption
        :return: created picture id
        """

        if not upload_id:
            upload_id = self.post_upload()

        response = self.post.upload_picture(
            user_id=self.user_id,
            auth_token=self.auth_token,
            asset=asset,
            album_id=album_id,
            upload_id=upload_id,
            caption=caption)

        self._assert_response(response, 201)
        return response['data']['picture_id']

    def post_upload(self, picture_count=1):
        """posts upload

        :param picture_count: `int`, number of pictures in upload
        :return: `int`, created upload id
        """

        response = self.post.user_upload(
            user_id=self.user_id,
            auth_token=self.auth_token,
            picture_count=picture_count)

        self._assert_response(response, 201)
        return response['data']['upload_id']

    #
    # BASE - GET
    #

    def get_album(self, album_id):
        """gets an album

        :param album_id: `int`, album to get
        :return: album data
        """

        response = self.get.user_album(
            user_id=self.user_id,
            auth_token=self.auth_token,
            album_id=album_id,
            fields=self.album_fields)

        self._assert_response(response)
        return response['data']['album']

    def get_albums(self, limit=None, offset=None, fields=None):
        """gets user albums

        :param limit: `int`, limit amount of items to get
        :param offset: `int`, paginate results
        :param fields: `list`, album parameters to query for
        :return: album data
        """

        response = self.get.user_albums(
            user_id=self.user_id,
            auth_token=self.auth_token,
            limit=limit or self.limit_default,
            offset=offset,
            fields=fields or self.album_fields)

        self._assert_response(response)
        return response['data']['albums']

    def get_picture(self, album_id, picture_id, fields=None):
        """get a picture

        :param album_id: `int`, album id the picture belongs to
        :param picture_id: `int`, picture to get
        :param fields: `list`, picture parameters to query for
        :return: picture data
        """

        response = self.get.album_picture(
            user_id=self.user_id,
            auth_token=self.auth_token,
            album_id=album_id,
            picture_id=picture_id,
            fields=fields or self.picture_fields)

        self._assert_response(response)
        return response['data']['picture']

    def get_album_pictures(self, album_id, limit=None, offset=None):
        """get pictures belonging to an album

        :param album_id: `int`, album to get pictures from
        :param limit: `int`, limit amount of items to get
        :param offset: `int`, paginate results
        :return: picture data
        """

        response = self.get.album_pictures(
            user_id=self.user_id,
            auth_token=self.auth_token,
            album_id=album_id,
            fields=self.picture_fields,
            limit=limit or self.limit_default,
            offset=offset)

        self._assert_response(response)
        return response['data']['pictures']

    def get_user(self):
        """get basic user information

        :return: user data
        """

        response = self.get.user(
            user_id=self.user_id,
            auth_token=self.auth_token)

        self._assert_response(response)

        user = response['data']['user']
        self.user_id = user['id']
        self.username = user['username']

    def get_user_pictures(self, limit=None, offset=None):
        """get all user pictures

        :param limit: `int`, limit amount of items to get
        :param offset: `int`, paginate results
        :return: picture data
        """

        response = self.get.user_pictures(
            user_id=self.user_id,
            auth_token=self.auth_token,
            fields=self.picture_fields,
            limit=limit or self.limit_default,
            offset=offset)

        self._assert_response(response)
        return response['data']['pictures']

    #
    # BASE - DELETE
    #

    def delete_album(self, album_id):
        """delete an album

        :param album_id: `int`, album id to delete
        """

        response = self.delete.user_album(
            user_id=self.user_id,
            auth_token=self.auth_token,
            album_id=album_id)

        self._assert_response(response, 204)

    def delete_picture(self, album_id, picture_id):
        """delete a picture

        :param album_id: `int`, album id the picture belongs to
        :param picture_id: `int`, picture to delete
        :return: picture data
        """

        response = self.delete.album_picture(
            user_id=self.user_id,
            auth_token=self.auth_token,
            album_id=album_id,
            picture_id=picture_id)

        self._assert_response(response)

    #
    # BASE - PUT
    #

    def put_album(self, album_id, name=None, description=None,
                  is_public=None):
        """put (update) album data

        :param album_id: `int`, album to update
        :param name: `str`, updated album name
        :param description: `str`, updated album description
        :param is_public: `bool`, updated privacy status
        :return: album data
        """

        response = self.put.user_album(
            user_id=self.user_id,
            auth_token=self.auth_token,
            album_id=album_id,
            name=name,
            description=description,
            is_public=is_public)

        self._assert_response(response)
        return response['data']

    def put_picture(self, album_id, picture_id, caption=None):
        """put (update) picture data

        :param album_id: `int`, album id the picture belongs to
        :param picture_id: `int`, picture to update
        :param caption: `str`, updated picture caption
        :return: picture data
        """

        response = self.put.album_picture(
            user_id=self.user_id,
            auth_token=self.auth_token,
            album_id=album_id,
            picture_id=picture_id,
            caption=caption)

        self._assert_response(response)
        return response['data']

    #
    # BASE - MISC
    #

    def _assert_response(self, resp, code=200):
        """:raise: `ToolError` (w/ web msg) if unexpected web response code"""

        e = 'HTTP {} - {}'.format(resp['code'], resp['msg'])

        if 'data' in resp and 'message' in resp['data']:
            e = resp['data']['message']

        assert resp['code'] == code, ToolError(e, self.print_help)

    @staticmethod
    def _captions_load(caption_file):
        """load captions fro csv file

        file should be formatted as such:
            /absolute/path/to/file.lfp,this is the caption

        :param caption_file: `str`, caption file to read
        :return: dictionary of captions
        """

        with open(caption_file) as f:
            caption_csv = f.readlines()

        caption_csv = [line for line in caption_csv if line]
        captions = {}

        for line in caption_csv:
            path, caption = tuple(line.split(','))
            captions[path] = caption.strip()
        return captions

    def _page_albums(self, username, limit=None):
        """paginate through user albums

        :param username: `str`, album(s) owner
        :param limit: `int`, limit amount of items to get
        :return: album data
        """

        page = 1
        msg = "getting albums for user {u} (page {p})"
        msgutils.msg(msg.format(u=username, p=page))
        limit = limit or self.limit_default
        albums = self.get_albums(limit=limit)
        albums_raw = [a for a in albums]

        if len(albums) >= limit:
            while albums:
                page += 1
                msgutils.msg(msg.format(u=username, p=page), indent=True)
                offset = len(albums_raw)
                albums = self.get_albums(offset=offset, limit=limit)
                albums_raw.extend(albums)

        return albums_raw

    def _page_pictures(self, username, album_id=None, limit=None):
        """paginate through album pictures

        :param username: `str`, album owner
        :param album_id: `str`, album to page through
        :param limit: `int`, limit amount of items to get
        :return: picture data
        """

        page = 1
        msg = "getting pictures for {type_} {obj} (page {page})"

        limit = limit or self.limit_default

        if album_id:
            type_ = 'album'
            obj = album_id
            get_pictures = partial(self.get_album_pictures, album_id=album_id)
        else:
            type_ = 'user'
            obj = username
            get_pictures = self.get_user_pictures

        msgutils.msg(msg.format(type_=type_, obj=obj, page=page))
        pictures = get_pictures(limit=limit)

        pictures_raw = [p for p in pictures]

        if len(pictures) >= limit:
            while pictures:
                page += 1
                msgutils.msg(msg.format(type_=type_, obj=obj, page=page))
                offset = len(pictures_raw)
                pictures = get_pictures(offset=offset, limit=limit)
                pictures_raw.extend(pictures)

        return pictures_raw

    def _match_album_picture(self, username, picture_id):
        """matches albums to pictures

        :param username: `str`, albums owner
        :param picture_id: `int`, picture to lookup
        :return: matching result
        """

        pictures = self._page_pictures(username, limit=self.limit_max)
        lookup = [d for d in pictures if d['id'] == picture_id]
        match = lookup[0] if lookup else {}
        return match
