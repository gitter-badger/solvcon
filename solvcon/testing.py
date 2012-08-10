# -*- coding: UTF-8 -*-
#
# Copyright (C) 2008-2011 Yung-Yu Chen <yyc@solvcon.net>.
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

"""
Provide functionalities for unittests.
"""

import os
from unittest import TestCase
from .solver import BlockSolver

def openfile(filename, mode=None):
    """
    Open file with requested file name.  The file name contains relative path
    to 'data' directory in this directory, and uses forward slash as delimiter 
    of directory components.

    @param filename: path of file relative to 'data' directory in this
        directory.
    @type filename: str
    @keyword mode: file mode.
    @type mode: str
    @return: opened file.
    @rtype: file
    """
    import os
    from .conf import env
    path = [env.datadir] + filename.split('/')
    path = os.path.join(*path)
    if mode != None:
        return open(path, mode)
    else:
        return open(path)

def loadfile(filename):
    """
    Load file with requested file name.  The file name contains relative path
    to 'data' directory in this directory, and uses forward slash as delimiter 
    of directory components.

    @param filename: path of file relative to 'data' directory in this directory.
    @type filename: str
    @return: loaded data.
    @rtype: str
    """
    return openfile(filename).read()

def create_trivial_2d_blk():
    from solvcon.block import Block
    blk = Block(ndim=2, nnode=4, nface=6, ncell=3, nbound=3)
    blk.ndcrd[:,:] = (0,0), (-1,-1), (1,-1), (0,1)
    blk.cltpn[:] = 3
    blk.clnds[:,:4] = (3, 0,1,2), (3, 0,2,3), (3, 0,3,1)
    blk.build_interior()
    blk.build_boundary()
    blk.build_ghost()
    return blk

def get_blk_from_sample_neu(fpdtype=None, use_incenter=None):
    """
    Read data from sample.neu file and convert it into Block.
    """
    from .io.gambit import GambitNeutral
    from .boundcond import bctregy
    kw = {'fpdtype': fpdtype}
    if use_incenter is not None:
        kw['use_incenter'] = use_incenter
    return GambitNeutral(loadfile('sample.neu')).toblock(**kw)

def get_blk_from_oblique_neu(fpdtype=None, use_incenter=None):
    """
    Read data from oblique.neu file and convert it into Block.
    """
    from .io.gambit import GambitNeutral
    from .boundcond import bctregy
    bcname_mapper = {
        'inlet': (bctregy.unspecified, {}),
        'outlet': (bctregy.unspecified, {}),
        'wall': (bctregy.unspecified, {}),
        'farfield': (bctregy.unspecified, {}),
    }
    kw = {'fpdtype': fpdtype, 'bcname_mapper': bcname_mapper}
    if use_incenter is not None:
        kw['use_incenter'] = use_incenter
    return GambitNeutral(loadfile('oblique.neu')).toblock(**kw)

class TestingSolver(BlockSolver):
    _interface_init_ = ['cecnd', 'cevol']

    def __init__(self, blk, *args, **kw):
        """
        @keyword neq: number of equations (variables).
        @type neq: int
        """
        from numpy import empty
        super(TestingSolver, self).__init__(blk, *args, **kw)
        # data structure for C/FORTRAN.
        self.blk = blk
        # arrays.
        ndim = self.ndim
        ncell = self.ncell
        ngstcell = self.ngstcell
        ## solutions.
        neq = self.neq
        self.sol = empty((ngstcell+ncell, neq), dtype=self.fpdtype)
        self.soln = empty((ngstcell+ncell, neq), dtype=self.fpdtype)
        self.dsol = empty((ngstcell+ncell, neq, ndim), dtype=self.fpdtype)
        self.dsoln = empty((ngstcell+ncell, neq, ndim), dtype=self.fpdtype)
        ## metrics.
        self.cecnd = empty(
            (ngstcell+ncell, self.CLMFC+1, ndim), dtype=self.fpdtype)
        self.cevol = empty((ngstcell+ncell, self.CLMFC+1), dtype=self.fpdtype)

    def create_alg(self):
        from .fake_algorithm import FakeAlgorithm
        alg = FakeAlgorithm()
        alg.setup_mesh(self.blk)
        alg.setup_algorithm(self)
        return alg

    ##################################################
    # marching algorithm.
    ##################################################
    MMNAMES = list()
    MMNAMES.append('update')
    def update(self, worker=None):
        self.sol[:,:] = self.soln[:,:]
        self.dsol[:,:,:] = self.dsoln[:,:,:]

    MMNAMES.append('calcsoln')
    def calcsoln(self, worker=None):
        self.create_alg().calc_soln()

    MMNAMES.append('ibcsoln')
    def ibcsoln(self, worker=None):
        if worker: self.exchangeibc('soln', worker=worker)

    MMNAMES.append('calccfl')
    def calccfl(self, worker=None):
        self.marchret = -2.0

    MMNAMES.append('calcdsoln')
    def calcdsoln(self, worker=None):
        self.create_alg().calc_dsoln()

    MMNAMES.append('ibcdsoln')
    def ibcdsoln(self, worker=None):
        if worker: self.exchangeibc('dsoln', worker=worker)
