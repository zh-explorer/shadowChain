# Copyright [2018] [zh_explorer]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# store some config and context


class Context(object):
    logger = None
    main_loop = None
    sock_pool = None
    pool_max_size = 50
    pool_size = 0

    password = None

    out_protocol_stack = []
    first_client = 0
    target_host = None
    target_port = None

    in_protocol_stack = []
    server_host = None
    server_port = None

    is_reverse_server = False
    is_reverse_client = False

context = Context()
