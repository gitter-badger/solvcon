# -*- coding: UTF-8 -*-
#
# Copyright (C) 2008-2010 Yung-Yu Chen <yyc@solvcon.net>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""Unstructured mesh manipulator."""

import os

CLASSIFIERS = """\
Development Status :: 3 - alpha
Intended Audience :: Developers
Intended Audience :: Education
Intended Audience :: Science/Research
License :: OSI Approved :: GNU General Public License (GPL)
Operating System :: Microsoft :: Windows
Operating System :: POSIX :: Linux
Programming Language :: C
Programming Language :: Python
Topic :: Scientific/Engineering
Topic :: Software Development :: Libraries :: Application Frameworks
"""

# BEFORE importing distutils, remove MANIFEST. distutils doesn't properly
# update it when the contents of directories change.
if os.path.exists('MANIFEST'): os.remove('MANIFEST')

def main():
    import os, sys
    from glob import glob
    from distutils.core import setup
    import solvcon

    doclines = solvcon.__doc__.split('\n')

    setup(
        name='solvcon',
        maintainer='Yung-Yu Chen',
        author='Yung-Yu Chen',
        maintainer_email='yyc@solvcon.net',
        author_email='yyc@solvcon.net',
        description=doclines[0],
        long_description='\n'.join(doclines[2:]),
        license='GPL',
        url='http://solvcon.net/',
        download_url='https://bitbucket.org/yungyuc/solvcon/downloads',
        classifiers=[tok.strip() for tok in CLASSIFIERS.split('\n')],
        platforms=[
            'Linux',
            'Windows',
        ],
        version=solvcon.__version__,
        scripts=[
            'scg',
        ],
        packages=[
            'solvcon',
            'solvcon.io',
            'solvcon.io.tests',
            'solvcon.kerpak',
            'solvcon.tests',
        ],
        data_files=[
            ('solvcon/lib', glob(os.path.join('lib', '*'))),
            ('solvcon/test/data',
                glob(os.path.join('test', 'data', '*.neu'))),
            ('solvcon/test/data',
                glob(os.path.join('test', 'data', '*.blk'))),
            ('solvcon/test/data',
                glob(os.path.join('test', 'data', '*.vtk'))),
            ('solvcon/test/data/sample.dom',
                glob(os.path.join('test', 'data', 'sample.dom', '*'))),
        ],
    )
    return

if __name__ == '__main__':
    main()
