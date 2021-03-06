# -*- coding: UTF-8 -*-
#
# Copyright (c) 2008, Yung-Yu Chen <yyc@solvcon.net>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the SOLVCON nor the names of its contributors may be
#   used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import unittest

import numpy as np

from solvcon import testing

from . import solver as fake_solver


class TestFakeSolver(unittest.TestCase):
    def setUp(self):
        blk = testing.create_trivial_2d_blk()
        self.svr = fake_solver.FakeSolver(blk, neq=1)
        self.svr.sol.fill(0)
        self.svr.soln.fill(0)
        self.svr.dsol.fill(0)
        self.svr.dsoln.fill(0)

    def test_calcsoln(self):
        svr = self.svr
        # run the solver.
        _ = svr.march(0.0, 0.01, 100)
        # calculate and compare the results in soln (discard ghost cells).
        soln = svr.soln[svr.blk.ngstcell:,:]
        clvol = np.empty_like(soln)
        clvol.fill(0)
        for iistep in range(200):
            clvol[:,0] += svr.blk.clvol*svr.time_increment/2
        # compare.
        self.assertTrue((soln==clvol).all())

    def test_calcdsoln(self):
        svr = self.svr
        # run the solver.
        _ = svr.march(0.0, 0.01, 100)
        # calculate and compare the results in dsoln (discard ghost cells).
        dsoln = svr.dsoln[svr.blk.ngstcell:,0,:]
        clcnd = np.empty_like(dsoln)
        clcnd.fill(0)
        for iistep in range(200):
            clcnd += svr.blk.clcnd*svr.time_increment/2
        # compare.
        self.assertTrue((dsoln==clcnd).all())

    def placeholder(self):
        pass

# vim: set ff=unix fenc=utf8 ft=python ai et sw=4 ts=4 tw=79:
