# -*- coding: utf-8 -*-
"""Lytro Power Tools - web package - API controllers"""

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

from lpt.web.handle import Handle


class Base(object):
    """shared base object for Lytro HTTP methods

    :param url: `str`, URL for controller endpoint
    :param base_headers: `dict`, HTTP headers
    :param method: `str`, HTTP method
    :param verbose: `bool`, increase HTTP call verbosity
    """

    def __init__(self, url, base_headers, method, verbose):
        self.handle = Handle(method, verbose=verbose)
        self.url = url
        self.base_headers = base_headers


class Get(Base):
    """Lytro HTTP GET method functions

    :param url: `str`, URL for controller endpoint
    :param base_headers: `dict`, HTTP headers
    :param verbose: `bool`, increase HTTP call verbosity
    """

    method = 'GET'
    print_help = object

    def __init__(self, url, base_headers, verbose=False):
        Base.__init__(self, url, base_headers, self.method, verbose)

    def album_picture(self, user_id, album_id, picture_id, include_likes=True,
                      auth_token=None, fields=None):
        """GET album picture end point

        :param user_id: `int`, user id
        :param album_id: `int`, album id
        :param picture_id: `int`, picture id
        :param include_likes: `bool`, include if liked by current user
        :param auth_token: `str`, authentication token
        :param fields: `list`, fields to be queried for
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'albums', album_id,
                                     'pictures', picture_id]) +
               self.handle.url_query(authentication_token=auth_token,
                                     fields=fields,
                                     include_likes=include_likes))

        return self.handle.url_request(url, headers)

    def album_pictures(self, user_id, album_id, auth_token=None, fields=None,
                       include_likes=True, limit=None, offset=None):
        """GET album pictures end point

        :param user_id: `int`, user id
        :param album_id: `int`, album id
        :param include_likes: `bool`, include if liked by current user
        :param auth_token: `str`, authentication token
        :param fields: `list`, fields to be queried for
        :param offset: `int`, paginate results to int
        :param limit: `int`, limit results to int
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'albums', album_id,
                                     'pictures']) +
               self.handle.url_query(authentication_token=auth_token,
                                     fields=fields,
                                     include_likes=include_likes,
                                     limit=limit,
                                     offset=offset))

        return self.handle.url_request(url, headers)

    def user(self, user_id=None, auth_token=None, fields=None):
        """GET user

        :param user_id: `int`, user id
        :param auth_token: `str`, authentication token
        :param fields: `list`, fields to be queried for
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id]) +
               self.handle.url_query(
                       authentication_token=auth_token,
                       fields=fields))

        return self.handle.url_request(url, headers)

    def user_album(self, user_id, album_id, auth_token=None, fields=None):
        """GET user album endpoint

        :param user_id: `int`, user id
        :param album_id: `int`, album id
        :param auth_token: `str`, authentication token
        :param fields: `list`, fields to be queried for
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'albums', album_id]) +
               self.handle.url_query(authentication_token=auth_token,
                                     fields=fields))

        return self.handle.url_request(url, headers)

    def user_albums(self, user_id, auth_token=None, count=False, fields=None,
                    limit=None, offset=None):
        """GET user albums endpoint

        :param user_id: `int`, user id
        :param auth_token: `str`, authentication token
        :param fields: `list`, fields to be queried for
        :param count: `bool`, return count of user albums
        :param offset: `int`, paginate results to int
        :param limit: `int`, limit results to int
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'albums']) +
               self.handle.url_query(authentication_token=auth_token,
                                     count=count,
                                     fields=fields,
                                     offset=offset,
                                     limit=limit))

        return self.handle.url_request(url, headers)

    def user_pictures(self, user_id, auth_token=None, include_likes=False,
                      fields=None, limit=None, offset=None, ):
        """GET user pictures endpoint

        :param user_id: `int`, user id
        :param auth_token: `str`, authentication token
        :param include_likes: `bool`, include if liked by current user
        :param fields: `list`, fields to be queried for
        :param offset: `int`, paginate results to int
        :param limit: `int`, limit results to int
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'pictures']) +
               self.handle.url_query(authentication_token=auth_token,
                                     fields=fields,
                                     limit=limit,
                                     include_likes=include_likes,
                                     offset=offset))

        return self.handle.url_request(url, headers)


class Delete(Base):
    """Lytro HTTP DELETE method functions

    :param url: `str`, URL for controller endpoint
    :param base_headers: `dict`, HTTP headers
    :param verbose: `bool`, increase HTTP call verbosity
    """

    method = 'DELETE'
    print_help = object

    def __init__(self, url, base_headers, verbose=False):
        Base.__init__(self, url, base_headers, self.method, verbose)

    def album_picture(self, user_id, album_id, picture_id, auth_token=None):
        """DELETE album picture endpoint

        :param user_id: `int`, user id
        :param album_id: `int`, album id
        :param picture_id: `int`, picture id
        :param auth_token: `str`, authentication token
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'albums', album_id,
                                     'pictures', picture_id]))
        data = {'authentication_token': auth_token}

        return self.handle.url_request(url, headers, data)

    def user_album(self, user_id, album_id, auth_token=None):
        """DELETE user album endpoint

        :param user_id: `int`, user id
        :param album_id: `int`, album id
        :param auth_token: `str`, authentication token
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'albums', album_id]))
        data = {'authentication_token': auth_token}

        return self.handle.url_request(url, headers, data)


class Post(Base):
    """Lytro HTTP POST method functions

    :param url: `str`, URL for controller endpoint
    :param base_headers: `dict`, HTTP headers
    :param verbose: `bool`, increase HTTP call verbosity
    """

    method = 'POST'
    print_help = object

    def __init__(self, url, base_headers, verbose=False):
        Base.__init__(self, url, base_headers, self.method, verbose)

    def session(self, username=None, password=None, email=None):
        """POST session endpoint

        :param username: `str`, username
        :param email: `str`, email address
        :param password: `str`, password
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['sessions']))

        data = {'password': password,
                'username': username,
                'email': email}

        return self.handle.url_request(url, headers, data)

    def upload_picture(self, user_id, upload_id, asset, album_id=None,
                       caption=None, auth_token=None):
        """POST upload picture endpoint

        :param user_id: `int`, user id
        :param upload_id: `int`, upload id
        :param album_id: `int`, album id
        :param asset: `str`, path to LFP asset
        :param caption: `str`, picture caption
        :param auth_token: `str`, authentication token
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'uploads', upload_id,
                                     'pictures']))

        md5_checksum = self.handle.md5sum(asset)
        form_data = {'authentication_token': auth_token,
                     'picture': {'album_id': album_id,
                                 'asset': asset,
                                 'caption': caption,
                                 'md5_checksum': md5_checksum,
                                 'upload_id': upload_id}}

        boundary = self.handle.boundary()
        crlf = '\r\n'
        data = '--' + boundary + crlf

        if auth_token:
            data += (
                'Content-Disposition: form-data; '
                'name="authentication_token"' +
                crlf + crlf + str(auth_token) +
                crlf + '--' + boundary + crlf)
        if upload_id:
            data += (
                'Content-Disposition: form-data; '
                'name="picture[upload_id]"' +
                crlf + crlf + str(upload_id) +
                crlf + '--' + boundary + crlf)
        if album_id:
            data += (
                'Content-Disposition: form-data; '
                'name="picture[album_id]"' +
                crlf + crlf + str(album_id) +
                crlf + '--' + boundary + crlf)
        if caption:
            data += (
                'Content-Disposition: form-data; '
                'name="picture[caption]"' +
                crlf + crlf + str(caption) +
                crlf + '--' + boundary + crlf)
        data += (
            'Content-Disposition: form-data; '
            'name="picture[md5_checksum]"' +
            crlf + crlf + str(md5_checksum) +
            crlf + '--' + boundary + crlf)
        data += (
            'Content-Disposition: form-data; '
            'name="picture[asset]"; ' +
            'filename="' + str(asset) + '"' + crlf +
            'Content-Type: application/octet-stream' + crlf + crlf)
        data += open(asset, 'rb').read()
        data += crlf + '--' + boundary + '--' + crlf

        headers['Content-Type'] = 'multipart/form-data; boundary=%s' % boundary
        headers['Content-Disposition'] = 'form-data'
        headers['Content-Length'] = len(data)

        return self.handle.url_request(url, headers, data, form_data)

    def user_album(self, user_id, auth_token=None, name=None, description=None,
                   is_public=False):
        """POST user album endpoint

        :param user_id: `int`, user id
        :param auth_token: `str`, authentication token
        :param name: `str`, album name
        :param description: `str`, album description
        :param is_public: `bool`, album privacy
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'albums']))

        data = {'authentication_token': auth_token,
                'album': {'description': description,
                          'name': name,
                          'is_public': is_public}}

        return self.handle.url_request(url, headers, data)

    def user_upload(self, user_id, picture_count=None, auth_token=None):
        """POST user upload endpoint

        :param user_id: `int`, user id
        :param picture_count: `int`, picture count for upload
        :param auth_token: `str`, authentication token
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'uploads']))
        data = {'authentication_token': auth_token,
                'upload': {'picture_count': picture_count}}
        return self.handle.url_request(url, headers, data)


class Put(Base):
    """Lytro HTTP PUT method functions

    :param url: `str`, URL for controller endpoint
    :param base_headers: `dict`, HTTP headers
    :param verbose: `bool`, increase HTTP call verbosity
    """

    method = 'PUT'
    print_help = object

    def __init__(self, url, base_headers, verbose=False):
        Base.__init__(self, url, base_headers, self.method, verbose)

    def user_album(self, user_id, album_id, auth_token=None, description=None,
                   is_public=None, name=None):
        """PUT user album endpoint

        :param user_id: `int`, user id
        :param album_id: `int`, album id to update
        :param auth_token: `str`, authentication token
        :param name: `str`, album name
        :param description: `str`, album description
        :param is_public: `bool`, album privacy
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'albums', album_id]))

        data = {'authentication_token': auth_token,
                'album': {'description': description,
                          'is_public': is_public,
                          'name': name}}

        return self.handle.url_request(url, headers, data)

    def album_picture(self, user_id, album_id, picture_id, auth_token=None,
                      caption=None):
        """PUT album endpoint

        :param user_id: `int`, user id
        :param album_id: `int`, album id containing the picture
        :param picture_id: `int`, picture id
        :param auth_token: `str`, authentication token
        :param caption: `str`, picture caption
        :return: urllib request/response
        """

        headers = self.base_headers.copy()
        url = (self.url +
               self.handle.url_path(['users', user_id,
                                     'albums', album_id,
                                     'pictures', picture_id]))

        data = {'authentication_token': auth_token,
                'picture': {'caption': caption}}
        return self.handle.url_request(url, headers, data)
