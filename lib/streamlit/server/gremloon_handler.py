# Copyright 2018-2020 Streamlit Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Dict, Any
from typing import List

import tornado.web
import tornado.httputil

from streamlit.uploaded_file_manager import UploadedFile
from streamlit import config
from streamlit.logger import get_logger
from streamlit.report import Report
from streamlit.server import routes

LOGGER = get_logger(__name__)


class GremloonRequestHandler(tornado.web.RequestHandler):
    def initialize(self, gremloon_request_manager):
        """
        Parameters
        ----------
        file_mgr : UploadedFileManager
            The server's singleton UploadedFileManager. All file uploads
            go here.

        """
        self._gremloon_request_manager = gremloon_request_manager

    """
    Implements the Gremloon custom endpoints.
    """
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")

    def options(self):
        """/OPTIONS handler for preflight CORS checks.

        When a browser is making a CORS request, it may sometimes first
        send an OPTIONS request, to check whether the server understands the
        CORS protocol. This is optional, and doesn't happen for every request
        or in every browser. If an OPTIONS request does get sent, and is not
        then handled by the server, the browser will fail the underlying
        request.

        The proper way to handle this is to send a 204 response ("no content")
        with the CORS headers attached. (These headers are automatically added
        to every outgoing response, including OPTIONS responses,
        via set_default_headers().)

        See https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request
        """
        self.set_status(204)
        self.finish()

    @staticmethod
    def _require_arg(args, name):
        """Return the value of the argument with the given name.

        A human-readable exception will be raised if the argument doesn't
        exist. This will be used as the body for the error response returned
        from the request.
        """
        try:
            arg = args[name]
        except KeyError:
            raise Exception("Missing '%s'" % name)

        if len(arg) != 1:
            raise Exception("Expected 1 '%s' arg, but got %s" % (name, len(arg)))

        # Convert bytes to string
        return arg[0].decode("utf-8")

    def get(self):
        args = {}  # type: Dict[str, List[bytes]]
        files = {}  # type: Dict[str, List[Any]]

        tornado.httputil.parse_body_arguments(
            content_type=self.request.headers["Content-Type"],
            body=self.request.body,
            arguments=args,
            files=files,
        )

        try:
            session_id = self._require_arg(args, "sessionId")
        except Exception as e:
            self.send_error(400, reason=str(e))
            return

        session_cookie = self.get_cookie("sessionid")
        print(session_cookie)

        self._gremloon_request_manager.request_rerun(session_id)
        self.write({
            "session_id": session_id
        })
        self.flush()
        self.set_status(200)
