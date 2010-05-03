# -*- coding: UTF-8 -*-
# Copyright (C) 2008-2009 by Yung-Yu Chen.  See LICENSE.txt for terms of usage.

"""
Provide functionalities for unittests.
"""

import os
from unittest import TestCase
from .solver import BlockSolver

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
    import os
    from .conf import env
    path = [env.datadir] + filename.split('/')
    path = os.path.join(*path)
    return open(path).read()

def get_blk_from_sample_neu(fpdtype=None):
    """
    Read data from sample.neu file and convert it into Block.
    """
    from .io.gambit import GambitNeutral
    from .boundcond import bctregy
    return GambitNeutral(loadfile('sample.neu')).toblock(fpdtype=fpdtype)

def get_blk_from_oblique_neu(fpdtype=None):
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
    return GambitNeutral(loadfile('oblique.neu')
        ).toblock(bcname_mapper=bcname_mapper, fpdtype=fpdtype)

class TestingSolver(BlockSolver):
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
        from ctypes import byref
        fpptr = self.fpptr
        self._clib_solvcon.calc_soln_(
            byref(self.msh),
            byref(self.exd),
            self.clvol.ctypes.data_as(fpptr),
            self.sol.ctypes.data_as(fpptr),
            self.soln.ctypes.data_as(fpptr),
        )

    MMNAMES.append('ibcsol')
    def ibcsol(self, worker=None):
        if worker: self.exchangeibc('soln', worker=worker)
    MMNAMES.append('bcsol')
    def bcsol(self, worker=None):
        for bc in self.bclist: bc.sol()

    MMNAMES.append('calccfl')
    def calccfl(self, worker=None):
        self.marchret = -2.0

    MMNAMES.append('calcdsoln')
    def calcdsoln(self, worker=None):
        from ctypes import byref
        fpptr = self.fpptr
        self._clib_solvcon.calc_dsoln_(
            byref(self.msh),
            byref(self.exd),
            self.clcnd.ctypes.data_as(fpptr),
            self.dsol.ctypes.data_as(fpptr),
            self.dsoln.ctypes.data_as(fpptr),
        )

    MMNAMES.append('ibcdsol')
    def ibcdsol(self, worker=None):
        if worker: self.exchangeibc('dsoln', worker=worker)
    MMNAMES.append('bcdsol')
    def bcdsol(self, worker=None):
        for bc in self.bclist: bc.dsol()
