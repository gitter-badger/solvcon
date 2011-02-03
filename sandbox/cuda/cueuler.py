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
Euler equations solver using the CESE method with CUDA.
"""

from solvcon.kerpak.euler import EulerSolver
from solvcon.kerpak.cese import CeseCase
from solvcon.kerpak.cese import CeseBC
from solvcon.anchor import Anchor
from solvcon.hook import BlockHook

def getcdll(libname):
    """
    Load shared objects at the default location.

    @param libname: main basename of library without sc_ prefix.
    @type libname: str
    @return: ctypes library.
    @rtype: ctypes.CDLL
    """
    from solvcon.dependency import loadcdll
    return loadcdll('.', 'sc_'+libname)

###############################################################################
# Solver.
###############################################################################

class CueulerSolver(EulerSolver):
    """
    Inviscid aerodynamic solver for the Euler equations.
    """
    _pointers_ = ['exc']
    def __init__(self, blk, *args, **kw):
        from scuda import Scuda
        self.scu = scu = Scuda()
        kw['nsca'] = 1
        super(CueulerSolver, self).__init__(blk, *args, **kw)
        # data structure for CUDA/C.
        self.exc = None
        self.gexc = None
        # meta array.
        self.cugrpda = scu.alloc(self.grpda.nbytes)
        # dual mesh.
        self.cucecnd = scu.alloc(self.cecnd.nbytes)
        self.cucevol = scu.alloc(self.cevol.nbytes)
        # solutions.
        self.cusolt = scu.alloc(self.solt.nbytes)
        self.cusol = scu.alloc(self.sol.nbytes)
        self.cusoln = scu.alloc(self.soln.nbytes)
        self.cudsol = scu.alloc(self.dsol.nbytes)
        self.cudsoln = scu.alloc(self.dsoln.nbytes)
        self.cucfl = scu.alloc(self.cfl.nbytes)
        self.cuocfl = scu.alloc(self.ocfl.nbytes)
        self.cuamsca = scu.alloc(self.amsca.nbytes)
        self.cuamvec = scu.alloc(self.amvec.nbytes)
    #from solvcon.dependency import getcdll
    __clib_cueuler = {
        2: getcdll('cueuler2d'),
        3: getcdll('cueuler3d'),
    }
    #del getcdll
    @property
    def _clib_cueuler(self):
        return self.__clib_cueuler[self.ndim]
    _gdlen_ = 0
    @property
    def _jacofunc_(self):
        return self._clib_euler.calc_jaco

    def set_execuda(self, exd, exc):
        from ctypes import cast
        if exd is None:
            exd = self._exedatatype_(svr=self)
        ctmap = dict()
        for key, ctp in exd._fields_:
            ctmap[key] = ctp
            setattr(self.exc, key, getattr(exd, key))
        for key in ['grpda', 'cecnd', 'cevol',
            'solt', 'sol', 'soln', 'dsol', 'dsoln', 'cfl', 'ocfl',
            'amsca', 'amvec',
        ]:
            # FIXME: I don't know what I am doing.
            gptr = getattr(self, 'cu'+key).gptr
            newptr = cast(gptr, ctmap[key])
            setattr(self.exc, key, newptr)

    def bind(self):
        from ctypes import sizeof
        if self.scu:
            self.exc = self._exedatatype_(svr=self)
            self.set_execuda(None, self.exc)
            self.gexc = self.scu.alloc(sizeof(self.exc))
        super(CueulerSolver, self).bind()

    def update(self, worker=None):
        if self.debug: self.mesg('update')
        # exchange solution and gradient.
        self.sol, self.soln = self.soln, self.sol
        self.dsol, self.dsoln = self.dsoln, self.dsol
        # reset pointers in execution data.
        ngstcell = self.ngstcell
        self.exd.sol = self.sol[ngstcell:].ctypes.data_as(self.fpptr)
        self.exd.soln = self.soln[ngstcell:].ctypes.data_as(self.fpptr)
        self.exd.dsol = self.dsol[ngstcell:].ctypes.data_as(self.fpptr)
        self.exd.dsoln = self.dsoln[ngstcell:].ctypes.data_as(self.fpptr)
        # set to CUDA.
        if self.scu:
            self.set_execuda(self.exd, self.exc)
            self.scu.memcpy(self.cudsol, self.dsol)
        if self.debug: self.mesg(' done.\n')

    def ibcam(self, worker=None):
        if self.debug: self.mesg('ibcam')
        if worker:
            if self.nsca: self.exchangeibc('amsca', worker=worker)
            if self.nvec: self.exchangeibc('amvec', worker=worker)
            if self.scu:
                if self.nsca: self.scu.memcpy(self.cuamsca, self.amsca)
                if self.nvec: self.scu.memcpy(self.cuamvec, self.amvec)
        if self.debug: self.mesg(' done.\n')

    def calcsolt(self, worker=None):
        if self.debug: self.mesg('calcsolt')
        from ctypes import byref
        self.scu.memcpy(self.cusol, self.sol)
        self.scu.memcpy(self.cudsol, self.dsol)
        self.scu.memcpy(self.cuamsca, self.amsca)
        self._clib_cueuler.calc_solt(byref(self.exc), self.gexc.gptr)
        #self.scu.memcpy(self.solt, self.cusolt)
        raise RuntimeError(self.solt.sum())
        if self.debug: self.mesg(' done.\n')

    def vcalcsoln(self, worker=None):
        if self.debug: self.mesg('calcsoln')
        from ctypes import byref
        self._clib_cueuler.calc_soln(byref(self.exc))
        if self.debug: self.mesg(' done.\n')

    def vcalccfl(self, worker=None):
        from ctypes import byref
        self._clib_cueuler.calc_cfl(byref(self.exc))
        mincfl = self.ocfl.min()
        maxcfl = self.ocfl.max()
        nadj = (self.cfl==1).sum()
        if self.marchret is None:
            self.marchret = [0.0, 0.0, 0, 0]
        self.marchret[0] = mincfl
        self.marchret[1] = maxcfl
        self.marchret[2] = nadj
        self.marchret[3] += nadj
        return self.marchret

    def vcalcdsoln(self, worker=None):
        if self.debug: self.mesg('calcdsoln')
        from ctypes import byref
        self._clib_cueuler.calc_dsoln(byref(self.exc))
        if self.debug: self.mesg(' done.\n')

###############################################################################
# Case.
###############################################################################

class CueulerCase(CeseCase):
    """
    Inviscid aerodynamic case for the Euler equations.
    """
    from solvcon.domain import Domain
    defdict = {
        'solver.solvertype': CueulerSolver,
        'solver.domaintype': Domain,
        'solver.cflname': 'adj',
    }
    del Domain
    def make_solver_keywords(self):
        kw = super(CueulerCase, self).make_solver_keywords()
        kw['cflname'] = self.solver.cflname
        return kw
    def load_block(self):
        loaded = super(CueulerCase, self).load_block()
        if hasattr(loaded, 'ndim'):
            ndim = loaded.ndim
        else:
            ndim = loaded.blk.ndim
        self.execution.neq = ndim+2
        return loaded

###############################################################################
# Boundary conditions.
###############################################################################

class CueulerBC(CeseBC):
    """
    Basic BC class for the Euler equations.
    """
    #from solvcon.dependency import getcdll
    __clib_cueulerb = {
        2: getcdll('cueulerb2d'),
        3: getcdll('cueulerb3d'),
    }
    #del getcdll
    @property
    def _clib_eulerb(self):
        return self.__clib_cueulerb[self.svr.ndim]

class CueulerWall(CueulerBC):
    _ghostgeom_ = 'mirror'
    def sol(self):
        from solvcon.dependency import intptr
        from ctypes import byref, c_int
        svr = self.svr
        self._clib_cueulerb.bound_wall_soln(
            byref(svr.exd),
            c_int(self.facn.shape[0]),
            self.facn.ctypes.data_as(intptr),
        )
    def dsol(self):
        from solvcon.dependency import intptr
        from ctypes import byref, c_int
        svr = self.svr
        self._clib_cueulerb.bound_wall_dsoln(
            byref(svr.exd),
            c_int(self.facn.shape[0]),
            self.facn.ctypes.data_as(intptr),
        )

class CueulerInlet(CueulerBC):
    vnames = ['rho', 'v1', 'v2', 'v3', 'p', 'gamma']
    vdefaults = {
        'rho': 1.0, 'p': 1.0, 'gamma': 1.4, 'v1': 0.0, 'v2': 0.0, 'v3': 0.0,
    }
    _ghostgeom_ = 'mirror'
    def sol(self):
        from solvcon.dependency import intptr
        from ctypes import byref, c_int
        svr = self.svr
        self._clib_cueulerb.bound_inlet_soln(
            byref(svr.exd),
            c_int(self.facn.shape[0]),
            self.facn.ctypes.data_as(intptr),
            c_int(self.value.shape[1]),
            self.value.ctypes.data_as(intptr),
        )
    def dsol(self):
        from solvcon.dependency import intptr
        from ctypes import byref, c_int
        svr = self.svr
        self._clib_cueulerb.bound_inlet_dsoln(
            byref(svr.exd),
            c_int(self.facn.shape[0]),
            self.facn.ctypes.data_as(intptr),
        )

###############################################################################
# Anchors.
###############################################################################

class CueulerIAnchor(Anchor):
    """
    Basic initializing anchor class for all Euler problems.
    """
    def __init__(self, svr, **kw):
        assert isinstance(svr, CueulerSolver)
        self.gamma = float(kw.pop('gamma'))
        super(CueulerIAnchor, self).__init__(svr, **kw)
    def provide(self):
        from solvcon.solver import ALMOST_ZERO
        svr = self.svr
        svr.amsca.fill(self.gamma)
        svr.sol.fill(ALMOST_ZERO)
        svr.soln.fill(ALMOST_ZERO)
        svr.dsol.fill(ALMOST_ZERO)
        svr.dsoln.fill(ALMOST_ZERO)

class UniformIAnchor(CueulerIAnchor):
    def __init__(self, svr, **kw):
        self.rho = float(kw.pop('rho'))
        self.v1 = float(kw.pop('v1'))
        self.v2 = float(kw.pop('v2'))
        self.v3 = float(kw.pop('v3'))
        self.p = float(kw.pop('p'))
        super(UniformIAnchor, self).__init__(svr, **kw)
    def provide(self):
        super(UniformIAnchor, self).provide()
        gamma = self.gamma
        svr = self.svr
        svr.soln[:,0].fill(self.rho)
        svr.soln[:,1].fill(self.rho*self.v1)
        svr.soln[:,2].fill(self.rho*self.v2)
        vs = self.v1**2 + self.v2**2
        if svr.ndim == 3:
            vs += self.v3**2
            svr.soln[:,3].fill(self.rho*self.v3)
        svr.soln[:,svr.ndim+1].fill(self.rho*vs/2 + self.p/(gamma-1))
        svr.sol[:] = svr.soln[:]
