# -*- coding: UTF-8 -*-
#
# Copyright (C) 2010-2011 Yung-Yu Chen <yyc@solvcon.net>.
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
Anisotropic velocity-stress equations solver using the CESE method.
"""

from solvcon.gendata import SingleAssignDict, AttributeDict
from solvcon.anchor import Anchor
from solvcon.hook import BlockHook
from .cese import CeseSolver
from .cese import CeseCase
from .cese import CeseBC

###############################################################################
# Metadata for materials.
###############################################################################

class MtrlTypeRegistry(SingleAssignDict, AttributeDict):
    """
    BC type registry class, and its instance holds BC type classes, which can
    be indexed by BC type name and BC type number. 
    
    In current design, there should exist only one registry singleton in 
    package.

    BC classes in registry should not be altered, in any circumstances.
    """
    def register(self, bctype):
        name = bctype.__name__
        self[name] = bctype
        return bctype
mltregy = MtrlTypeRegistry()  # registry singleton.

class MaterialMeta(type):
    """
    Meta class for material class.
    """
    def __new__(cls, name, bases, namespace):
        newcls = super(MaterialMeta, cls).__new__(cls, name, bases, namespace)
        # register.
        mltregy.register(newcls)
        return newcls

###############################################################################
# Solver.
###############################################################################

class ElasticSolver(CeseSolver):
    """
    Basic elastic solver.

    @ivar cfldt: the time_increment for CFL calculation at boundcond.
    @itype cfldt: float
    @ivar cflmax: the maximum CFL number.
    @itype cflmax: float
    @ivar mtrldict: map from names to material objects.
    @itype mtrldict: dict
    @ivar mtrllist: list of all material objects.
    @itype mtrllist: list
    """
    from solvcon.dependency import getcdll
    __clib_elastic = {
        2: getcdll('elastic2d'),
        3: getcdll('elastic3d'),
    }
    del getcdll
    @property
    def _clib_elastic(self):
        return self.__clib_elastic[self.ndim]
    _gdlen_ = 9 * 9 * 2
    @property
    def _jacofunc_(self):
        return self._clib_elastic.calc_jaco
    def __init__(self, *args, **kw):
        self.cfldt = kw.pop('cfldt', None)
        self.cflmax = 0.0
        self.mtrldict = kw.pop('mtrldict', {})
        self.mtrllist = None
        super(ElasticSolver, self).__init__(*args, **kw)
    @staticmethod
    def _build_mtrllist(grpnames, mtrldict):
        """
        Build the material list out of the mapping dict.

        @param grpnames: sequence of group names.
        @type grpnames: list
        @param mtrldict: the map from names to material objects.
        @type mtrldict: dict
        @return: the list of material object.
        @rtype: Material
        """
        mtrllist = list()
        default_mtuple = mtrldict.get(None, None)
        for grpname in grpnames:
            try:
                mtrl = mtrldict.get(grpname, default_mtuple)
            except KeyError, e:
                args = e.args[:]
                args.append('no material named %s in mtrldict'%grpname)
                e.args = args
                raise
            mtrllist.append(mtrl)
        return mtrllist
    def provide(self):
        from ctypes import byref, c_int
        # build material list.
        self.mtrllist = self._build_mtrllist(self.grpnames, self.mtrldict)
        for igrp in range(len(self.grpnames)):
            mtrl = self.mtrllist[igrp]
            jaco = self.grpda[igrp].reshape(self.neq, self.neq, self.ndim)
            jaco[:,:,0] = mtrl.jacox
            jaco[:,:,1] = mtrl.jacoy
            if self.ndim == 3:
                jaco[:,:,2] = mtrl.jacoz
        # pre-calculate CFL.
        self._set_time(self.time, self.cfldt)
        self._clib_elastic.calc_cfl(
            byref(self.exd), c_int(0), c_int(self.ncell))
        self.cflmax = self.cfl.max()
        # super method.
        super(ElasticSolver, self).provide()
    def calccfl(self, worker=None):
        if self.marchret is None:
            self.marchret = [0.0, 0.0, 0, 0]
        self.marchret[0] = self.cflmax
        self.marchret[1] = self.cflmax
        self.marchret[2] = 0
        self.marchret[3] = 0
        return self.marchret

###############################################################################
# Case.
###############################################################################

class ElasticCase(CeseCase):
    """
    Case for anisotropic elastic solids.
    """
    from solvcon.domain import Domain
    defdict = {
        'execution.neq': 9,
        'solver.solvertype': ElasticSolver,
        'solver.domaintype': Domain,
        'solver.alpha': 0,
        'solver.cfldt': None,
        'solver.mtrldict': dict,
    }
    del Domain
    def make_solver_keywords(self):
        kw = super(ElasticCase, self).make_solver_keywords()
        # setup delta t for CFL calculation.
        cfldt = self.solver.cfldt
        cfldt = self.execution.time_increment if cfldt is None else cfldt
        kw['cfldt'] = cfldt
        # setup material mapper.
        kw['mtrldict'] = self.solver.mtrldict
        return kw

###############################################################################
# Boundary conditions.
###############################################################################

class ElasticBC(CeseBC):
    """
    Basic BC class for elastic problems.
    """
    from solvcon.dependency import getcdll
    __clib_elasticb = {
        2: getcdll('elasticb2d'),
        3: getcdll('elasticb3d'),
    }
    del getcdll
    @property
    def _clib_elasticb(self):
        return self.__clib_elasticb[self.svr.ndim]

class ElasticTraction(ElasticBC):
    vnames = [
        'bfcsys', 'tau1', 'tau2', 'tau3', 'freq', 'phase',
    ]
    vdefaults = {
        'bfcsys': 0.0,
        'tau1': 0.0, 'tau2': 0.0, 'tau3': 0.0, 'freq': 0.0, 'phase': 0.0,
    }
    _ghostgeom_ = 'compress'
    def sol(self):
        from solvcon.dependency import intptr
        from ctypes import byref, c_int
        self._clib_boundcond.bound_traction_soln(
            byref(self.svr.exd),
            c_int(self.facn.shape[0]),
            self.facn.ctypes.data_as(intptr),
            c_int(self.value.shape[1]),
            self.value.ctypes.data_as(self.fpptr),
        )
    def dsol(self):
        from solvcon.dependency import intptr
        from ctypes import byref, c_int
        self._clib_boundcond.bound_traction_dsoln(
            byref(self.svr.exd),
            c_int(self.facn.shape[0]),
            self.facn.ctypes.data_as(intptr),
        )

class ElasticTractionFree(ElasticBC):
    _ghostgeom_ = 'mirror'
    def sol(self):
        from solvcon.dependency import intptr
        from ctypes import byref, c_int
        self._clib_boundcond.bound_traction_free_soln(
            byref(self.svr.exd),
            c_int(self.facn.shape[0]),
            self.facn.ctypes.data_as(intptr),
        )
    def dsol(self):
        from solvcon.dependency import intptr
        from ctypes import byref, c_int
        self._clib_boundcond.bound_traction_free_dsoln(
            byref(self.svr.exd),
            c_int(self.facn.shape[0]),
            self.facn.ctypes.data_as(intptr),
        )

class ElasticTractionFree2(ElasticBC):
    _ghostgeom_ = 'mirror'
    def sol(self):
        from solvcon.dependency import intptr
        from ctypes import byref, c_int
        self._clib_boundcond.bound_traction_free2_soln(
            byref(self.svr.exd),
            c_int(self.facn.shape[0]),
            self.facn.ctypes.data_as(intptr),
        )
    def dsol(self):
        from solvcon.dependency import intptr
        from ctypes import byref, c_int
        self._clib_boundcond.bound_traction_free2_dsoln(
            byref(self.svr.exd),
            c_int(self.facn.shape[0]),
            self.facn.ctypes.data_as(intptr),
        )

################################################################################
# Anchor.
################################################################################

class ElasticOAnchor(Anchor):
    """
    Calculate total energy, i.e., the summation of kinetic energy and strain
    energy.
    """
    def _calculate_physics(self):
        from ctypes import byref
        from numpy import empty
        from numpy.linalg import inv
        svr = self.svr
        # input arrays.
        rhos = empty(svr.ngroup, dtype=svr.fpdtype)
        comps = empty((svr.ngroup, 6, 6), dtype=svr.fpdtype)
        for igp in range(svr.ngroup):
            mtrl = svr.mtrllist[igp]
            rhos[igp] = mtrl.rho
            comps[igp,:,:] = inv(mtrl.stiff).T
        # output arrays.
        svr._clib_elastic.calc_energy(
            byref(svr.exd),
            rhos.ctypes.data_as(svr.fpptr),
            comps.ctypes.data_as(svr.fpptr),
            svr.der['energy'].ctypes.data_as(svr.fpptr),
        )
    def provide(self):
        from numpy import empty
        svr = self.svr
        svr.der['energy'] = empty(svr.ngstcell+svr.ncell, dtype=svr.fpdtype)
        self._calculate_physics()
    def postfull(self):
        self._calculate_physics()

################################################################################
# Material definition.
################################################################################

class Material(object):
    """
    Material properties.  The constitutive relation needs not be symmetric.
    
    @cvar _zeropoints_: list of tuples for indices where the content should be
        zero.
    @ctype _zeropoints_: list
    @ivar rho: density
    @ivar al: alpha angle.
    @ivar be: beta angle.
    @ivar ga: gamma angle.
    @ivar origstiff: stiffness matrix in the crystal coordinate.
    @ivar stiff: stiffness matrix in the transformed global coordinate.
    """

    __metaclass__ = MaterialMeta

    _zeropoints_ = []

    from numpy import array
    K = array([
        [
            [1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 1, 0],
        ],
        [
            [0, 0, 0, 0, 0, 1],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0],
        ],
        [
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0, 0],
        ],
    ], dtype='float64')
    del array

    def __init__(self, *args, **kw):
        from numpy import empty, dot
        self.rho = kw.pop('rho')
        self.al = kw.pop('al')
        self.be = kw.pop('be')
        self.ga = kw.pop('ga')
        # set stiffness matrix.
        origstiff = empty((6,6), dtype='float64')
        origstiff.fill(0.0)
        for key in kw.keys():   # becaues I pop out the key.
            if len(key) == 4 and key[:2] == 'co':
                try:
                    i = int(key[2])-1
                    j = int(key[3])-1
                except:
                    continue
                assert i < origstiff.shape[0]
                assert j < origstiff.shape[1]
                val = kw.pop(key)
                origstiff[i,j] = val
        self.origstiff = origstiff
        # check for zeros.
        self._check_origstiffzero(self.origstiff)
        # compute the stiffness matrix in the transformed global coordinate
        # system.
        bondmat = self.bondmat
        self.stiff = dot(bondmat, dot(self.origstiff, bondmat.T))
        super(Material, self).__init__(*args, **kw)

    def __getattr__(self, key):
        if len(key) == 4 and key[:2] == 'co':
            i = int(key[2])
            j = int(key[3])
            if 1 <= i <= 6 and 1 <= j <= 6:
                return self.origstiff[i-1,j-1]
        elif len(key) == 3 and key[0] == 'c':
            i = int(key[1])
            j = int(key[2])
            if 1 <= i <= 6 and 1 <= j <= 6:
                return self.stiff[i-1,j-1]
        else:
            raise AttributeError

    def __str__(self):
        from math import pi
        return '[%s: al=%.2f be=%.2f ga=%.2f (deg)]' % (self.__class__.__name__,
            self.al/(pi/180), self.be/(pi/180), self.ga/(pi/180))

    @classmethod
    def _check_origstiffzero(cls, origstiff):
        """
        Check for zero in original stiffness matrix.

        @note: no assumed symmetry.
        """
        for i, j in cls._zeropoints_:
            assert origstiff[i,j] == 0.0

    @property
    def rotmat(self):
        """
        Coordinate transformation matrix for three successive rotations through
        the Euler angles.

        @return: the transformation matrix.
        @rtype: numpy.ndarray
        """
        from numpy import array, cos, sin, dot
        al = self.al; be = self.be; ga = self.ga
        almat = array([
            [cos(al), sin(al), 0],
            [-sin(al), cos(al), 0],
            [0, 0, 1],
        ], dtype='float64')
        bemat = array([
            [1, 0, 0],
            [0, cos(be), sin(be)],
            [0, -sin(be), cos(be)],
        ], dtype='float64')
        gamat = array([
            [cos(ga), sin(ga), 0],
            [-sin(ga), cos(ga), 0],
            [0, 0, 1],
        ], dtype='float64')
        return dot(gamat, dot(bemat, almat))

    @property
    def bondmat(self):
        """
        The Bond's matrix M as a shorthand of coordinate transformation for the 
        6-component stress vector.

        @return: the Bond's matrix.
        @rtype: numpy.ndarray
        """
        from numpy import empty
        rotmat = self.rotmat
        bond = empty((6,6), dtype='float64')
        # upper left.
        bond[:3,:3] = rotmat[:,:]**2
        # upper right.
        bond[0,3] = 2*rotmat[0,1]*rotmat[0,2]
        bond[0,4] = 2*rotmat[0,2]*rotmat[0,0]
        bond[0,5] = 2*rotmat[0,0]*rotmat[0,1]
        bond[1,3] = 2*rotmat[1,1]*rotmat[1,2]
        bond[1,4] = 2*rotmat[1,2]*rotmat[1,0]
        bond[1,5] = 2*rotmat[1,0]*rotmat[1,1]
        bond[2,3] = 2*rotmat[2,1]*rotmat[2,2]
        bond[2,4] = 2*rotmat[2,2]*rotmat[2,0]
        bond[2,5] = 2*rotmat[2,0]*rotmat[2,1]
        # lower left.
        bond[3,0] = rotmat[1,0]*rotmat[2,0]
        bond[3,1] = rotmat[1,1]*rotmat[2,1]
        bond[3,2] = rotmat[1,2]*rotmat[2,2]
        bond[4,0] = rotmat[2,0]*rotmat[0,0]
        bond[4,1] = rotmat[2,1]*rotmat[0,1]
        bond[4,2] = rotmat[2,2]*rotmat[0,2]
        bond[5,0] = rotmat[0,0]*rotmat[1,0]
        bond[5,1] = rotmat[0,1]*rotmat[1,1]
        bond[5,2] = rotmat[0,2]*rotmat[1,2]
        # lower right.
        bond[3,3] = rotmat[1,1]*rotmat[2,2] + rotmat[1,2]*rotmat[2,1]
        bond[3,4] = rotmat[1,0]*rotmat[2,2] + rotmat[1,2]*rotmat[2,0]
        bond[3,5] = rotmat[1,1]*rotmat[2,0] + rotmat[1,0]*rotmat[2,1]
        bond[4,3] = rotmat[0,1]*rotmat[2,2] + rotmat[0,2]*rotmat[2,1]
        bond[4,4] = rotmat[0,0]*rotmat[2,2] + rotmat[0,2]*rotmat[2,0]
        bond[4,5] = rotmat[0,1]*rotmat[2,0] + rotmat[0,0]*rotmat[2,1]
        bond[5,3] = rotmat[0,1]*rotmat[1,2] + rotmat[0,2]*rotmat[1,1]
        bond[5,4] = rotmat[0,0]*rotmat[1,2] + rotmat[0,2]*rotmat[1,0]
        bond[5,5] = rotmat[0,1]*rotmat[1,0] + rotmat[0,0]*rotmat[1,1]
        return bond

    def _jaco(self, K):
        """
        @param K: the K matrix.
        @type K: numpy.ndarray
        @return: the Jacobian matrix in x-dir.
        @rtype: numpy.ndarray
        """
        from numpy import zeros, dot
        rho = self.rho
        sf = self.stiff
        jaco = zeros((9,9), dtype='float64')
        jaco[:3,3:] = K/(-rho)  # the upper right submatrix.
        jaco[3:,:3] = -dot(sf, K.T) # the lower left submatrix.
        return jaco
    @property
    def jacox(self):
        """
        @return: the Jacobian matrix in x-dir.
        @rtype: numpy.ndarray
        """
        return self._jaco(self.K[0])
    @property
    def jacoy(self):
        """
        @return: the Jacobian matrix in y-dir.
        @rtype: numpy.ndarray
        """
        return self._jaco(self.K[1])
    @property
    def jacoz(self):
        """
        @return: the Jacobian matrix in z-dir.
        @rtype: numpy.ndarray
        """
        return self._jaco(self.K[2])

    def _eig(self, jaco):
        from numpy.linalg import eig
        evl, evc = eig(jaco)
        srt = evl.argsort()
        evl = evl[srt]
        evc = evc[:,srt]
        return evl, evc

    @property
    def eigx(self):
        return self._eig(self.jacox)
    @property
    def eigy(self):
        return self._eig(self.jacoy)
    @property
    def eigz(self):
        return self._eig(self.jacoz)

    @property
    def vpx(self):
        return self.eigx[0][-3:]
    @property
    def vpy(self):
        return self.eigy[0][-3:]
    @property
    def vpz(self):
        return self.eigz[0][-3:]

class Triclinic(Material):
    """
    The stiffness matrix has to be symmetric.
    """
    _zeropoints_ = []

    def __init__(self, *args, **kw):
        for key in kw.keys():   # becaues I modify the key.
            if len(key) == 4 and key[:2] == 'co':
                try:
                    i = int(key[2])
                    j = int(key[3])
                except:
                    continue
                symkey = 'co%d%d' % (j, i)
                if i != j:
                    assert symkey not in kw
                kw[symkey] = kw[key]
        super(Triclinic, self).__init__(*args, **kw)

    @classmethod
    def _check_origstiffzero(cls, origstiff):
        """
        Check for zero in original stiffness matrix.

        @note: assumed symmetric.
        """
        for i, j in cls._zeropoints_:
            assert origstiff[i,j] == origstiff[j,i] == 0.0

class Monoclinic(Triclinic):
    _zeropoints_ = [
        (0,3), (0,5),
        (1,3), (1,5),
        (2,3), (2,5),
        (3,4), (4,5),
    ]

class Orthorhombic(Triclinic):
    _zeropoints_ = [
        (0,3), (0,4), (0,5),
        (1,3), (1,4), (1,5),
        (2,3), (2,4), (2,5),
        (3,4), (3,5), (4,5),
    ]

class Tetragonal(Triclinic):
    _zeropoints_ = [
        (0,3), (0,4),
        (1,3), (1,4),
        (2,3), (2,4), (2,5),
        (3,4), (3,5), (4,5),
    ]

    def __init__(self, *args, **kw):
        kw['co22'] = kw['co11']
        kw['co23'] = kw['co13']
        kw['co26'] = -kw.get('co16', 0.0)
        kw['co55'] = kw['co44']
        super(Tetragonal, self).__init__(*args, **kw)

class Trigonal(Triclinic):
    _zeropoints_ = [
        (0,5), (1,5),
        (2,3), (2,4), (2,5),
        (3,4),
    ]

    def __init__(self, *args, **kw):
        kw['co15'] = -kw.get('co25', 0.0)
        kw['co22'] = kw['co11']
        kw['co23'] = kw['co13']
        kw['co24'] = -kw.get('co14', 0.0)
        kw['co46'] = kw.get('co25', 0.0)
        kw['co55'] = kw['co44']
        kw['co56'] = kw.get('co14', 0.0)
        kw['co66'] = (kw['co11'] - kw['co12'])/2
        super(Trigonal, self).__init__(*args, **kw)

class Hexagonal(Trigonal):
    _zeropoints_ = [
        (0,3), (0,4), (0,5),
        (1,3), (1,4), (1,5),
        (2,3), (2,4), (2,5),
        (3,4), (3,5), (4,5),
    ]

class Cubic(Triclinic):
    _zeropoints_ = [
        (0,3), (0,4), (0,5),
        (1,3), (1,4), (1,5),
        (2,3), (2,4), (2,5),
        (3,4), (3,5), (4,5),
    ]

    def __init__(self, *args, **kw):
        kw['co13'] = kw['co12']
        kw['co22'] = kw['co11']
        kw['co23'] = kw['co12']
        kw['co33'] = kw['co11']
        kw['co55'] = kw['co44']
        kw['co66'] = kw['co44']
        super(Cubic, self).__init__(*args, **kw)

class Isotropic(Triclinic):
    _zeropoints_ = [
        (0,3), (0,4), (0,5),
        (1,3), (1,4), (1,5),
        (2,3), (2,4), (2,5),
        (3,4), (3,5), (4,5),
    ]

    def __init__(self, *args, **kw):
        kw['co12'] = kw['co11']-2*kw['co44']
        kw['co13'] = kw['co11']-2*kw['co44']
        kw['co22'] = kw['co11']
        kw['co23'] = kw['co11']-2*kw['co44']
        kw['co33'] = kw['co11']
        kw['co55'] = kw['co44']
        kw['co66'] = kw['co44']
        super(Isotropic, self).__init__(*args, **kw)

class GaAs(Cubic):
    def __init__(self, *args, **kw):
        kw.setdefault('rho', 5307.0)
        kw.setdefault('co11', 11.88e10)
        kw.setdefault('co12', 5.38e10)
        kw.setdefault('co44', 5.94e10)
        super(GaAs, self).__init__(*args, **kw)

class ZnO(Hexagonal):
    def __init__(self, *args, **kw):
        kw.setdefault('rho', 5680.0)
        kw.setdefault('co11', 20.97e10)
        kw.setdefault('co12', 12.11e10)
        kw.setdefault('co13', 10.51e10)
        kw.setdefault('co33', 21.09e10)
        kw.setdefault('co44', 4.247e10)
        super(ZnO, self).__init__(*args, **kw)

class CdS(Hexagonal):
    def __init__(self, *args, **kw):
        kw.setdefault('rho', 4820.0)
        kw.setdefault('co11', 9.07e10)
        kw.setdefault('co12', 5.81e10)
        kw.setdefault('co13', 5.1e10)
        kw.setdefault('co33', 9.38e10)
        kw.setdefault('co44', 1.504e10)
        super(CdS, self).__init__(*args, **kw)

class Zinc(Hexagonal):
    def __init__(self, *args, **kw):
        kw.setdefault('rho', 7.1*1.e-3/(1.e-2**3))
        kw.setdefault('co11', 14.3e11*1.e-5/(1.e-2**2))
        kw.setdefault('co12', 1.7e11*1.e-5/(1.e-2**2))
        kw.setdefault('co13', 3.3e11*1.e-5/(1.e-2**2))
        kw.setdefault('co33', 5.0e11*1.e-5/(1.e-2**2))
        kw.setdefault('co44', 4.0e11*1.e-5/(1.e-2**2))
        super(Zinc, self).__init__(*args, **kw)

class Beryl(Hexagonal):
    def __init__(self, *args, **kw):
        kw.setdefault('rho', 2.7*1.e-3/(1.e-2**3))
        kw.setdefault('co11', 26.94e11*1.e-5/(1.e-2**2))
        kw.setdefault('co12', 9.61e11*1.e-5/(1.e-2**2))
        kw.setdefault('co13', 6.61e11*1.e-5/(1.e-2**2))
        kw.setdefault('co33', 23.63e11*1.e-5/(1.e-2**2))
        kw.setdefault('co44', 6.53e11*1.e-5/(1.e-2**2))
        super(Beryl, self).__init__(*args, **kw)

class Albite(Triclinic):
    def __init__(self, *args, **kw):
        #kw.setdefault('rho', )
        kw.setdefault('co11', 69.9e9)
        kw.setdefault('co22', 183.5e9)
        kw.setdefault('co33', 179.5e9)
        kw.setdefault('co44', 24.9e9)
        kw.setdefault('co55', 26.8e9)
        kw.setdefault('co66', 33.5e9)
        kw.setdefault('co12', 34.0e9)
        kw.setdefault('co13', 30.8e9)
        kw.setdefault('co14', 5.1e9)
        kw.setdefault('co15', -2.4e9)
        kw.setdefault('co16', -0.9e9)
        kw.setdefault('co23', 5.5e9)
        kw.setdefault('co24', -3.9e9)
        kw.setdefault('co25', -7.7e9)
        kw.setdefault('co26', -5.8e9)
        kw.setdefault('co34', -8.7e9)
        kw.setdefault('co35', 7.1e9)
        kw.setdefault('co36', -9.8e9)
        kw.setdefault('co45', -2.4e9)
        kw.setdefault('co46', -7.2e9)
        kw.setdefault('co56', 0.5e9)
        super(Albite, self).__init__(*args, **kw)

class Acmite(Monoclinic):
    def __init__(self, *args, **kw):
        kw.setdefault('rho', 3.5e3)
        kw.setdefault('co11', 185.8e9)
        kw.setdefault('co22', 181.3e9)
        kw.setdefault('co33', 234.4e9)
        kw.setdefault('co44', 62.9e9)
        kw.setdefault('co55', 51.0e9)
        kw.setdefault('co66', 47.4e9)
        kw.setdefault('co12', 68.5e9)
        kw.setdefault('co13', 70.7e9)
        kw.setdefault('co15', 9.8e9)
        kw.setdefault('co23', 62.9e9)
        kw.setdefault('co25', 9.4e9)
        kw.setdefault('co35', 21.4e9)
        kw.setdefault('co46', 7.7e9)
        super(Acmite, self).__init__(*args, **kw)

class AlphaUranium(Orthorhombic):
    def __init__(self, *args, **kw):
        #kw.setdefault('rho', )
        kw.setdefault('rho', 8.2e3) # a false value.
        kw.setdefault('co11', 215.e9)
        kw.setdefault('co22', 199.e9)
        kw.setdefault('co33', 267.e9)
        kw.setdefault('co44', 124.e9)
        kw.setdefault('co55', 73.e9)
        kw.setdefault('co66', 74.e9)
        kw.setdefault('co12', 46.e9)
        kw.setdefault('co13', 22.e9)
        kw.setdefault('co23', 107.e9)
        super(AlphaUranium, self).__init__(*args, **kw)

class BariumTitanate(Tetragonal):
    def __init__(self, *args, **kw):
        kw.setdefault('rho', 6.2e3)
        kw.setdefault('co11', 275.0e9)
        kw.setdefault('co33', 165.0e9)
        kw.setdefault('co44', 54.3e9)
        kw.setdefault('co66', 113.0e9)
        kw.setdefault('co12', 179.0e9)
        kw.setdefault('co13', 151.0e9)
        super(BariumTitanate, self).__init__(*args, **kw)

class AlphaQuartz(Trigonal):
    def __init__(self, *args, **kw):
        kw.setdefault('rho', 2.651e3)
        kw.setdefault('co11', 87.6e9)
        kw.setdefault('co33', 106.8e9)
        kw.setdefault('co44', 57.2e9)
        kw.setdefault('co12', 6.1e9)
        kw.setdefault('co13', 13.3e9)
        kw.setdefault('co14', 17.3e9)
        super(AlphaQuartz, self).__init__(*args, **kw)

class RickerSample(Isotropic):
    def __init__(self, *args, **kw):
        kw.setdefault('rho', 2200.e0)
        kw.setdefault('co11', 3200.e0**2*2200.e0)
        kw.setdefault('co44', 1847.5e0**2*2200.e0)
        super(RickerSample, self).__init__(*args, **kw)
class RickerSampleLight(Isotropic):
    def __init__(self, *args, **kw):
        scale = 1.e-3
        kw.setdefault('rho', 2200.e0*scale)
        kw.setdefault('co11', 3200.e0**2*2200.e0*scale)
        kw.setdefault('co44', 1847.5e0**2*2200.e0*scale)
        super(RickerSampleLight, self).__init__(*args, **kw)
