# -*- coding: UTF-8 -*-
# Copyright (C) 2008-2010 by Yung-Yu Chen.  See LICENSE.txt for terms of usage.

from unittest import TestCase

class TestArrangement(TestCase):
    def test_arrangement_registry(self):
        from ..case import BaseCase, BlockCase
        self.assertNotEqual(
            id(BaseCase.arrangements),
            id(BlockCase.arrangements)
        )

class TestCaseInfo(TestCase):
    def test_CaseInfo(self):
        from ..case import CaseInfo
        tdic = CaseInfo(_defdict={
            'lay1_1': '1_1',
            'lay1_2.lay2_1': '1_2/2_1',
            'lay1_2.lay2_2': '1_2/2_2',
            'lay1_3.': '1_3/',
        })
        self.assertEqual(tdic.lay1_1, '1_1')
        self.assertEqual(tdic.lay1_2.lay2_1, '1_2/2_1')
        self.assertEqual(tdic.lay1_2.lay2_2, '1_2/2_2')
        self.assertEqual(len(tdic.lay1_3), 0)

class TestBaseCase(TestCase):
    def test_empty_fields(self):
        from ..case import BaseCase
        case = BaseCase()
        # execution related.
        self.assertTrue(isinstance(case.runhooks, list))
        self.assertEqual(case.execution.time, 0.0)
        self.assertEqual(case.execution.time_increment, 0.0)
        self.assertEqual(case.execution.step_init, 0)
        self.assertEqual(case.execution.step_current, None)
        self.assertEqual(case.execution.steps_run, None)
        self.assertEqual(case.execution.neq, 0)
        self.assertEqual(case.execution.var, dict())
        self.assertEqual(case.execution.varstep, None)
        # io related.
        self.assertEqual(case.io.abspath, False)
        self.assertEqual(case.io.basedir, None)
        self.assertEqual(case.io.basefn, None)
        # condition related.
        self.assertEqual(case.condition.mtrllist, list())
        # solver related.
        self.assertEqual(case.solver.solvertype, None)
        self.assertEqual(case.solver.solverobj, None)
        # logging.
        self.assertEqual(case.log.time, dict())

    def test_abspath(self):
        import os
        from ..case import BaseCase
        case = BaseCase(basedir='.', abspath=True)
        path = os.path.abspath('.')
        self.assertEqual(case.io.basedir, path)

    def test_init(self):
        from ..case import BaseCase
        case = BaseCase()
        case.init()

from ..hook import BlockHook
class CaseCollect(BlockHook):
    def postmarch(self):
        self._collect_interior('soln', tovar=True)
        self._collect_interior('dsoln', tovar=True)
    def preloop(self):
        self.postmarch()
del BlockHook

class TestBlockCaseRun(TestCase):
    time = 0.0
    time_increment = 1.0
    nsteps = 10

    def _get_case(self, **kw):
        import os
        from ..testing import TestingSolver
        from ..conf import env
        from ..case import BlockCase
        from ..anchor import FillAnchor
        from ..helper import Information
        meshfn = kw.get('meshfn', 'sample.neu')
        kw['meshfn'] = os.path.join(env.datadir, meshfn)
        case = BlockCase(basedir='.', basefn='blockcase', bcmap=None,
            solvertype=TestingSolver, neq=1,
            steps_run=self.nsteps, time_increment=self.time_increment,
            **kw
        )
        case.info = Information()
        case.runhooks.append(FillAnchor,
            keys=('soln', 'dsoln'), value=0.0,
        )
        case.runhooks.append(CaseCollect)
        case.init()
        return case

class TestSequential(TestBlockCaseRun):
    def test_soln(self):
        from numpy import zeros
        from ..domain import Domain
        case = self._get_case(domaintype=Domain)
        svr = case.solver.solverobj
        case.run()
        ngstcell = svr.ngstcell
        # get result.
        soln = svr.soln[ngstcell:,0]
        # calculate reference
        clvol = zeros(soln.shape, dtype=soln.dtype)
        for iistep in range(self.nsteps*2):
            clvol += svr.clvol[ngstcell:]*self.time_increment/2
        # compare.
        self.assertTrue((soln==clvol).all())

    def test_dsoln(self):
        from numpy import zeros
        from ..domain import Domain
        case = self._get_case(domaintype=Domain)
        svr = case.solver.solverobj
        case.run()
        ngstcell = svr.ngstcell
        # get result.
        dsoln = svr.dsoln[ngstcell:,0,:]
        # calculate reference
        clcnd = zeros(dsoln.shape, dtype=dsoln.dtype)
        for iistep in range(self.nsteps*2):
            clcnd += svr.clcnd[ngstcell:]*self.time_increment/2
        # compare.
        self.assertTrue((dsoln==clcnd).all())

class TestLocalParallel(TestBlockCaseRun):
    npart = 3

    def test_soln(self):
        import sys
        from nose.plugins.skip import SkipTest
        if sys.platform.startswith('win'): raise SkipTest
        from numpy import zeros
        from ..domain import Collective
        case = self._get_case(npart=self.npart, domaintype=Collective)
        case.run()
        # get result.
        soln = case.execution.var['soln'][:,0]
        # calculate reference
        blk = case.solver.domainobj.blk
        clvol = zeros(soln.shape, dtype=soln.dtype)
        for iistep in range(self.nsteps*2):
            clvol += blk.clvol*self.time_increment/2
        # compare.
        self.assertTrue((soln==clvol).all())

    def test_dsoln(self):
        import sys
        from nose.plugins.skip import SkipTest
        if sys.platform.startswith('win'): raise SkipTest
        from numpy import zeros
        from ..domain import Collective
        case = self._get_case(npart=self.npart, domaintype=Collective)
        case.run()
        # get result.
        dsoln = case.execution.var['dsoln'][:,0,:]
        # calculate reference
        blk = case.solver.domainobj.blk
        clcnd = zeros(dsoln.shape, dtype=dsoln.dtype)
        for iistep in range(self.nsteps*2):
            clcnd += blk.clcnd*self.time_increment/2
        # compare.
        self.assertTrue((dsoln==clcnd).all())

    def test_ibcthread(self):
        import sys
        from nose.plugins.skip import SkipTest
        if sys.platform.startswith('win'): raise SkipTest
        from numpy import zeros
        from ..domain import Collective
        case = self._get_case(npart=self.npart, domaintype=Collective,
            ibcthread=True)
        case.run()
        # get result.
        soln = case.execution.var['soln'][:,0]
        # calculate reference
        blk = case.solver.domainobj.blk
        clvol = zeros(soln.shape, dtype=soln.dtype)
        for iistep in range(self.nsteps*2):
            clvol += blk.clvol*self.time_increment/2
        # compare.
        self.assertTrue((soln==clvol).all())

class TestRemoteParallel(TestBlockCaseRun):
    npart = 2

    def test_dsoln(self):
        import sys
        from nose.plugins.skip import SkipTest
        if sys.platform.startswith('win'): raise SkipTest
        from numpy import zeros
        from ..batch import Localhost
        from ..domain import Distributed
        case = self._get_case(npart=self.npart, domaintype=Distributed,
            batch=Localhost, rkillfn='')
        case.run()
        # get result.
        dsoln = case.execution.var['dsoln'][:,0,:]
        # calculate reference
        blk = case.solver.domainobj.blk
        clcnd = zeros(dsoln.shape, dtype=dsoln.dtype)
        for iistep in range(self.nsteps*2):
            clcnd += blk.clcnd*self.time_increment/2
        # compare.
        self.assertTrue((dsoln==clcnd).all())

class TestPresplitLocalParallel(TestBlockCaseRun):
    npart = 3
    def test_soln(self):
        import sys
        from nose.plugins.skip import SkipTest
        if sys.platform.startswith('win'): raise SkipTest
        from numpy import zeros
        from ..domain import Collective
        case = self._get_case(npart=self.npart, domaintype=Collective,
            meshfn='sample.dom')
        case.run()
        # get result.
        soln = case.execution.var['soln'][:,0]
        # calculate reference
        blk = case.solver.domainobj.blk
        clvol = zeros(soln.shape, dtype=soln.dtype)
        for iistep in range(self.nsteps*2):
            clvol += blk.clvol*self.time_increment/2
        # compare.
        self.assertTrue((soln==clvol).all())
class TestPresplitRemoteParallel(TestBlockCaseRun):
    npart = 3
    def test_dsoln(self):
        import sys
        from nose.plugins.skip import SkipTest
        if sys.platform.startswith('win'): raise SkipTest
        from numpy import zeros
        from ..batch import Localhost
        from ..domain import Distributed
        case = self._get_case(npart=self.npart, domaintype=Distributed,
            batch=Localhost, rkillfn='', meshfn='sample.dom')
        case.run()
        # get result.
        dsoln = case.execution.var['dsoln'][:,0,:]
        # calculate reference
        blk = case.solver.domainobj.blk
        clcnd = zeros(dsoln.shape, dtype=dsoln.dtype)
        for iistep in range(self.nsteps*2):
            clcnd += blk.clcnd*self.time_increment/2
        # compare.
        self.assertTrue((dsoln==clcnd).all())

class TestTorqueParallel(TestBlockCaseRun):
    npart = 2

    def test_runparallel(self):
        import sys, os
        from nose.plugins.skip import SkipTest
        if sys.platform.startswith('win'): raise SkipTest
        from ..batch_torque import TaskManager
        if TaskManager._clib_torque == None or \
           'PBS_NODEFILE' not in os.environ: raise SkipTest
        from numpy import zeros
        from ..batch import Torque
        from ..domain import Distributed
        case = self._get_case(npart=self.npart, domaintype=Distributed,
            batch=Torque, rkillfn='')
        case.run()
