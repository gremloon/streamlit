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

import threading
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Tuple

from blinker import Signal


class GremloonRequestManager(object):
    """Holds files uploaded by users of the running Streamlit app,
    and emits an event signal when a file is added.
    """

    def __init__(self):
        self.on_rerun_requested = Signal(
            doc="""Emitted when a rerun has been requested.
            """
        )

    def request_rerun(self, session_id):
        self.on_rerun_requested.send(session_id)
