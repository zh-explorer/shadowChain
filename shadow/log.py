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
import logging


def log_init():
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)

    file_log = logging.FileHandler("/tmp/shadow.log")
    file_log.setLevel(logging.INFO)

    fmt = logging.Formatter('[%(levelname)s] %(asctime)s  %(filename)s %(lineno)d : %(message)s')
    console.setFormatter(fmt)
    fmt = logging.Formatter('[%(levelname)s] %(asctime)s  %(filename)s %(lineno)d : %(message)s')
    file_log.setFormatter(fmt)

    logger = logging.getLogger("asyncio")
    logger.addHandler(console)
    logger.addHandler(file_log)
    logger.setLevel(logging.DEBUG)
    return logger


logger = log_init()


def get_logger():
    return logger

