# -*- coding: utf-8 -*-
"""Lytro Power Tools - web package - URL/HTTP handler"""

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
import hashlib
import inspect
import json
import random
import string
import httplib
import urllib2

from lpt.utils.msgutils import MsgUtils

od = collections.OrderedDict
msgutils = MsgUtils()


class Handle(object):
    """miscellaneous shared URL/HTTP functions

    :param method: `str`, HTTP method
    :param verbose: `bool`, increase HTTP call verbosity
    """

    def __init__(self, method=None, verbose=False):
        self.method = method
        self.verbose = verbose

    def url_request(self, url, headers, data=None, form_data=None):
        """urllib2 wrapper for interacting with Lytro Web API

        :param url: `str`, url endpoint
        :param headers: `dict`, url headers
        :param data: `dict`/`str`, data uploaded for POST/PUT HTTP calls
        :param form_data: `dict`, metadata when 'data' is raw file data
        """

        domain = url.split('/')[2].split('.')[-2].title()
        caller = inspect.stack()[1][3].replace('_', ' ').title()
        meta = "{domain} {method} {caller}: ".format(domain=domain,
                                                     method=self.method,
                                                     caller=caller)
        msgutils.msg(meta, crlf='', type_='HTTP')

        call = od(request=od(url=url, method=self.method, headers=headers),
                  response=od())

        content_type = headers['Content-Type']

        if form_data:
            call['request']['form_data'] = self.obj_filter(form_data)
            call['request']['data'] = "%d bytes" % len(data)
        elif data:
            data = self.obj_filter(data)
            call['request']['data'] = data
            data = json.dumps(data)

        request = urllib2.Request(url, data=data, headers=headers)

        if self.method in ('DELETE', 'PUT'):
            opener = urllib2.build_opener(urllib2.HTTPHandler)
            urlopen = opener.open
            request.add_header('Content-Type', content_type)
            request.get_method = lambda: self.method
        else:
            urlopen = urllib2.urlopen

        try:
            response = urlopen(request)
            error_type = None
        except urllib2.HTTPError as error:
            response = error
            error_type = 'HTTPError'
        except urllib2.URLError as error:
            response = error
            error_type = 'URLError'
        except httplib.BadStatusLine as error:
            response = error
            error_type = 'BadStatusLine'
        except Exception as error:
            response = error
            error_type = 'Unexpected'

        if error_type:
            resp_code = response.code if 'code' in dir(response) else 0
            if error_type in ('HTTPError', 'URLError'):
                resp_msg = response.reason
            elif error_type == 'BadStatusLine':
                resp_msg = response.message
            elif len(response) > 0 and response[1]:
                resp_msg = response[1][0]
            else:
                resp_msg = response[0]
        else:
            resp_msg = response.msg
            resp_code = response.code

        call['response']['msg'] = resp_msg
        call['response']['code'] = resp_code

        try:
            read = response.read()
        except AttributeError:
            resp_data = {}
        else:
            try:
                resp_read = json.loads(read)
            except ValueError:
                resp_data = read
            else:
                resp_data = self.obj_stringify(resp_read)

        if resp_data:
            call['response']['data'] = resp_data

        if self.verbose:
            request_obj = call['request']

            if 'data' in request_obj and 'password' in request_obj['data']:
                password = request_obj['data']['password']
                request_obj['data']['password'] = '*' * len(password)

            msgutils.dumps(call)

        else:
            msg = "HTTP {code} - {msg}".format(code=resp_code, msg=resp_msg)
            msgutils.msg(msg, raw=True)

        return call['response']

    def obj_stringify(self, obj):
        """converts all values in a dict object to str

        :param obj: `dict`/`str`, object to convert
        :return: converted dict
        """

        if not isinstance(obj, dict):
            return obj
        return dict((str(k), self.obj_stringify(v)) for k, v in obj.items())

    def obj_filter(self, obj):
        """filters out NoneType keys/values from a dict

        if the dict value is the word "NULL", explicitly send None as a value

        :param obj: `dict`, input object to filter
        :return: converted dict
        """

        build = {}
        for key, value in obj.items():
            if value is not None:
                if isinstance(value, dict):
                    build[key] = self.obj_filter(value)
                else:
                    build[key] = value
        return build

    @staticmethod
    def url_path(roots, end='json'):
        """formats URL path section of a URL

        :param roots: `list`, object to convert
        :param end: `str`, if the path ends with an extension, append end
        :return: formatted URL path
        """

        path = ''.join(['/' + str(s) for s in roots])
        path += '.{}'.format(end) if end else ''
        return path

    @staticmethod
    def url_query(**kwargs):
        """formats a string for the query section of a URL from **kwargs

        :param kwargs: `type`, convert kwargs key/values to str
        :return: formatted string
        """

        query = ''
        start = True
        kwargs = od(sorted(kwargs.items()))
        for param, value in kwargs.items():
            param = str(param)
            value_str = ''
            if value or str(value) == '0':
                query += '?' if start else '&'
                start = False
                if isinstance(value, (str, unicode)):
                    value = value.replace(' ', '%20')

                if isinstance(value, list):
                    for i, val in enumerate(value, start=1):
                        value_str += str(val)
                        if i != len(value):
                            value_str += ","
                else:
                    value_str = str(value)
                query += "{}={}".format(param, value_str)
        return query

    @staticmethod
    def boundary(length=20):
        """randomized boundary used for raw data uploads

        :param length: `int`, length of boundary
        :return: random boundary from ASCII upper case + digits
        """

        chars = (string.ascii_uppercase + string.digits)
        bound = 'tnt__' + ''.join(random.sample(chars, length))
        return bound

    @staticmethod
    def md5sum(file_path, bs=65536):
        """read md5sum of local file

        :param file_path: `str`, file to check
        :param bs: `int`, file read blocksize
        :return: md5 hex digest of file_path
        """

        md5 = hashlib.md5()
        with open(file_path, "r+b") as f:
            [md5.update(block) for block in iter(lambda: f.read(bs), '')]

        return md5.hexdigest()
