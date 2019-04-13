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


# from distutils.core import setup
import subprocess

import sys
import traceback

from setuptools import setup

long_description = ''
try:
    long_description = subprocess.check_output(['pandoc', 'README.md', '--to=rst'])
except Exception as e:
    sys.stderr.write("Failed to convert README.md through pandoc, proceeding anyway")
    traceback.print_exc()
setup(
    name='shadowChain',
    version='0.0.3',
    packages=['shadow', 'shadow.unit', 'shadow.protocols'],
    url='https://github.com/zh-explorer/shadowChain',
    license='Apache License 2.0',
    author='explorer',
    author_email='hsadkhk@gmail.com',
    description='A proxy tool',
    long_description=long_description.decode(),
    entry_points={'console_scripts': [
        'SCStart=shadow.run_server:main_start',
    ]},
    install_requires=[
        "jsonschema >= 2.3.0",
        "pycryptodome >= 3.6",
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Customer Service',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='proxy',
    project_urls={
        'Documentation': 'https://github.com/zh-explorer/shadowChain/blob/master/README.md',
        'Source': 'https://github.com/zh-explorer/shadowChain',
        'Tracker': 'https://github.com/zh-explorer/shadowChain/issues',
    },
    python_requires='>=3.5.2, <4',
)
