# -*- coding: utf-8 -*-
"""Lytro Power Tools - utilities package - shared JSON utilities"""

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

import json
import os
import jsonschema

from lpt.utils.msgutils import MsgUtils
from lpt.utils.msgutils import ToolError
from lpt.utils.utils import Utils

utils = Utils()
msgutils = MsgUtils()


class JsonUtils(object):
    """Lytro Power Tools json file manipulation functions"""

    ValidationError = jsonschema.ValidationError
    print_help = object

    def set_print_help(self, print_help):
        """sets `argparse` help menu for current command

        :param print_help: `object`, passed to ToolError for command help menu
        """

        self.print_help = print_help
        utils.set_print_help(print_help)

    @staticmethod
    def _load_schema(schema_file):
        """load Lytro schema as a json object"""

        with open(schema_file) as f:
            raw_data = f.read()

            try:
                schema = json.loads(raw_data)
            except ValueError:
                schema = json.loads(raw_data.replace('\\.', '.'))

        return schema

    def data(self, file_path_in, schema_file=None, valid=False):
        """loads data from json file

        :param file_path_in: `str`, input path to check
        :param schema_file: `str`, path to json schema file (for validation)
        :param valid: `bool`, raise exception if exception found
        :return: json data
        :raise: `ToolError` for all `file_path_in` failures
        """

        try:
            with open(file_path_in) as f:
                data = json.load(f)
        except Exception as e:
            if valid:
                raise ToolError(e, self.print_help)
            else:
                return False

        if schema_file:
            self.validate(data, schema_file=schema_file)

        return data

    def search(self, paths, schema_file=None, msg=None):
        """searches for valid json files from a list of files or directories

        :param paths: `str`/`iter`, files/directories to search in; if `str`,,
                      the object is auto converted to a list
        :param schema_file: `str`, path to json schema file (for validation)
        :param msg: `str`, override default status message
        :yields: available json files
        :raise: `ToolError` if an object in `paths` is invalid
        """

        paths = utils.make_iter(paths)

        for i, path_in in enumerate(paths, start=1):
            path = utils.full_path(path_in)

            is_file_or_dir = os.path.isdir(path) or os.path.isfile(path)
            e = "not a valid file or directory : " + path_in
            assert is_file_or_dir, ToolError(e, self.print_help)

            msg = msg or "checking for json content"
            msgutils.status(msg, src=path, count=i)

            if os.path.isfile(path):
                if self.data(path, schema_file):
                    yield path

            elif os.path.isdir(path):
                file_paths = utils.walk_path(path)

                for path_ in file_paths:
                    if self.data(path_, schema_file):
                        yield path_

    def validate(self, json_data, schema_file, raise_=False):
        """validates json data using a json schema file

        :param raise_: `bool`, raise `ToolError` on failure
        :param json_data: `dict`, json data to validate
        :param schema_file: `str`, path to json schema validation file
        :return: True if data is valid, else False (if `raise_` == False)
        :raise: `ToolError` if `raise_` is True and validation fails
        """

        schema = self._load_schema(schema_file)
        try:
            jsonschema.validate(json_data, schema)
        except jsonschema.ValidationError as e:
            if raise_:
                raise ToolError(e, self.print_help)
            else:
                return False
        else:
            return True
