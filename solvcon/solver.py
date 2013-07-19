# -*- coding: UTF-8 -*-
#
# Copyright (C) 2008-2013 Yung-Yu Chen <yyc@solvcon.net>.
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
Definition of the structure of solvers.
"""


import os
import time

import numpy as np

from . import anchor
from . import gendata
from . import helper
from . import boundcond

from .solver_core import ALMOST_ZERO

# import legacy.
from .solver_legacy import (
    BaseSolverExedata, BaseSolver, FakeBlockVtk, BlockSolver)


class _MethodList(list):
    """
    A custom :py:class:`list` that provides a decorator for keeping names of
    functions.

    >>> mmnames = _MethodList()
    >>> @mmnames.register
    ... def func_of_a_name():
    ...     pass
    >>> mmnames
    ['func_of_a_name']

    This class is a private helper and should only be used in
    :py:mod:`solvcon.solver`.
    """

    def register(self, func):
        self.append(func.__name__)
        return func

class MeshSolver(object):
    """
    Base class for all solving code that take :py:class:`Mesh
    <solvcon.mesh.Mesh>`, which is usually needed to write efficient C/C++ code
    for implementing numerical methods.

    Here're some examples about using :py:class:`MeshSolver`.  The first
    example shows that we can't directly use it.  A vanilla
    :py:class:`MeshSolver` can't march:

    >>> from .testing import create_trivial_2d_blk
    >>> svr = MeshSolver(create_trivial_2d_blk())
    >>> svr.march(0.0, 0.1, 1)
    Traceback (most recent call last):
        ...
    TypeError: 'NoneType' object has no attribute '__getitem__'

    At minimal we need to override the :py:attr:`_MMNAMES` class attribute:

    >>> class DerivedSolver(MeshSolver):
    ...     _MMNAMES = MeshSolver.new_method_list()
    >>> svr = DerivedSolver(create_trivial_2d_blk())
    >>> svr.march(0.0, 0.1, 1)
    {}

    Of course the above derived solver did nothing.  Let's see another example
    solver that does non-trivial things:

    >>> class ExampleSolver(MeshSolver):
    ...     _MMNAMES = MeshSolver.new_method_list()
    ...     @_MMNAMES.register
    ...     def calcsomething(self, worker=None):
    ...         self.marchret['key'] = 'value'
    >>> svr = ExampleSolver(create_trivial_2d_blk())
    >>> svr.march(0.0, 0.1, 1)
    {'key': 'value'}
    """

    _interface_init_ = []
    _solution_array_ = []

    def __init__(self, blk, time=0.0, time_increment=0.0, enable_mesg=False,
            **kw):
        """
        A :py:class:`solvcon.block.Block` object must be provided to set the
        :py:attr:`blk` attribute.  The attribute holds the mesh data.
        """
        super(MeshSolver, self).__init__()
        # set mesh and BCs.
        #: The :py:class:`Block <solvcon.block.Block>` that holds the mesh data
        #: for this :py:class:`MeshSolver`.
        self.blk = blk
        for bc in self.blk.bclist:
            bc.svr = self
        # set time.
        #: The current time of the solver.  By default, :py:attr:`time` is
        #: initialized to ``0.0``, which is usually desired value.  The default
        #: value can be overridden from the constructor.
        self.time = time
        #: The temporal interval between the current and the next time steps.
        #: It is usually referred to as :math:`\Delta t` in the numerical
        #: literature.  By default, :py:attr:`time_increment` is initialized to
        #: ``0.0``, but the default should be overridden from the constructor.
        self.time_increment = time_increment
        # set step.
        #: It is an :py:class:`int` that records the current step of the
        #: solver.  It is initialized to ``0``.
        self.step_current = 0
        #: It is similar to :py:attr:`step_current`, but persists over restart.
        #: Without restarts, :py:attr:`step_global` should be identical to
        #: :py:attr:`step_current`.
        self.step_global = 0
        #: The number of sub-steps that a single time step should be split
        #: into.  It is initialized to ``1`` and should be overidden in
        #: subclasses if needed.
        self.substep_run = 1
        #: The current sub-step of the solver.  It is initialized to ``0``.
        self.substep_current = 0
        # set meta data.
        #: 0-based serial number of this solver in a parallel execution.
        self.svrn = self.blk.blkn
        #: Total number of parallel solvers.
        self.nsvr = None
        # marching facilities.
        #: Cached marching-method names.
        self._mmnames = None
        #: This instance attribute is of type :py:class:`AnchorList
        #: <solvcon.anchor.AnchorList>`, and the foundation of the anchor
        #: mechanism of SOLVCON.  An :py:class:`AnchorList
        #: <solvcon.anchor.AnchorList>` object like this collects a set of
        #: :py:class:`Anchor <solver.anchor.Anchor>` #: objects, and is
        #: callable.  When being called, :py:attr:`runanchors` iterates the
        #: contained :py:class:`Anchor <solvcon.anchor.Anchor>` objects and
        #: invokes the corresponding methods of the individual
        #: :py:class:`Anchor <solvcon.anchor.Anchor>`.
        self.runanchors = anchor.AnchorList(self)
        #: Values to be returned by this solver.  It will be set to a
        #: :py:class:`dict` in :py:meth:`march`.
        self.marchret = None
        #: Derived data container as a :py:class:`dict`.
        self.der = dict()
        # reporting facility.
        self.timer = gendata.Timer(vtype=float)
        self.enable_mesg = enable_mesg
        self._mesg = None

    ############################################################################
    # Meta data.
    @property
    def bclist(self):
        """
        Delegate to :py:attr:`Block.bclist <solvcon.block.Block.bclist>` of the
        :py:attr:`blk` attribute.
        """
        return self.blk.bclist

    @property
    def grpnames(self):
        return self.blk.grpnames

    @property
    def ngroup(self):
        return len(self.grpnames)

    @property
    def ndim(self):
        return self.blk.ndim

    @property
    def nnode(self):
        return self.blk.nnode

    @property
    def nface(self):
        return self.blk.nface

    @property
    def ncell(self):
        return self.blk.ncell

    @property
    def ngstnode(self):
        return self.blk.ngstnode

    @property
    def ngstface(self):
        return self.blk.ngstface

    @property
    def ngstcell(self):
        return self.blk.ngstcell
    # Meta data.
    ############################################################################

    @staticmethod
    def detect_ncore():
        """
        This utility method returns the number of cores on this machine.  It
        only works under Linux.
        """
        f = open('/proc/stat')
        data = f.read()
        f.close()
        cpulist = [line for line in data.split('\n') if
            line.startswith('cpu')]
        cpulist = [line for line in cpulist if line.split()[0] != 'cpu']
        return len(cpulist)

    @property
    def mesg(self):
        """
        Create the message outputing object, which is intended for debugging
        and outputing messages related to the solver.  The outputing device is
        most useful when running distributed solvers.  The created device will
        be attach to self.
        """
        if None is self._mesg:
            if self.enable_mesg:
                if self.svrn != None:
                    dfn = 'solvcon.solver%d.log' % self.svrn
                    dprefix = 'SOLVER%d: ' % self.svrn
                else:
                    dfn = 'solvcon.solver.log'
                    dprefix = ''
            else:
                dfn = os.devnull
                dprefix = ''
            self._mesg = helper.Printer(dfn, prefix=dprefix, override=True)
        return self._mesg

    #: This class attribute holds the names of the methods to be called in
    #: :py:meth:`march`.  It is of type :py:class:`_MethodList`.  The default
    #: value is ``None`` and must be reset in subclasses by calling
    #: :py:meth:`new_method_list`.
    _MMNAMES = None

    @staticmethod
    def new_method_list():
        """
        :return: An object to be set to :py:attr:`_MMNAMES`.
        :rtype: :py:class:`_MethodList`

        In subclasses of :py:class:`MeshSolver`, implementors can use this
        utility method to creates an instance of :py:class:`_MethodList`, which
        should be set to :py:attr:`_MMNAMES`.
        """
        return _MethodList()

    @property
    def mmnames(self):
        if not self._mmnames:
            self._mmnames = self._MMNAMES[:]
        return self._mmnames

    ############################################################################
    # Anchors.
    def provide(self):
        self.runanchors('provide')

    def preloop(self):
        self.runanchors('preloop')

    def postloop(self):
        self.runanchors('postloop')

    def exhaust(self):
        self.runanchors('exhaust')
    # Anchors.
    ############################################################################

    def march(self, time_current, time_increment, steps_run, worker=None):
        """
        :param time_current: Starting time of this set of marching steps.
        :type time_current: float
        :param time_increment: Temporal interval :math:`\Delta t` of the time
            step.
        :type time_increment: float
        :param steps_run: The count of time steps to run.
        :type steps_run: int
        :return: :py:attr:`marchret`

        This method performs time-marching.  The parameters *time_current* and
        *time_increment* are used to reset the instance attributes
        :py:attr:`time` and :py:attr:`time_increment`, respectively.

        There is a nested two-level loop in this method for time-marching.  The
        outer loop iterates for time steps, and the inner loop iterates for sub
        time steps.  The outer loop runs ``steps_run`` times, while the inner
        loop runs :py:attr:`substep_run` times.  In total, the inner loop runs
        *steps_run* \* :py:attr:`substep_run` times.  In each sub time step
        (in the inner loop), the increment of the attribute :py:attr:`time` is
        :py:attr:`time_increment`/:py:attr:`substep_run`.  The temporal
        increment per time step is effectively :py:attr:`time_increment`, with
        a slight error because of round-off.

        Before entering and after leaving the outer loop, :py:meth:`premarch
        <solvcon.anchor.Anchor.premarch>` and :py:meth:`postmarch
        <solvcon.anchor.Anchor.postmarch>` anchors will be run (through the
        attribute :py:attr:`runanchors`).  Similarly, before entering and after
        leaving the inner loop, :py:meth:`prefull
        <solvcon.anchor.Anchor.prefull>` and :py:meth:`postfull
        <solvcon.anchor.Anchor.postfull>` anchors will be run.  Inside the
        inner loop of sub steps, before and after executing all the marching
        methods, :py:meth:`presub <solvcon.anchor.Anchor.presub>` and
        :py:meth:`postsub <solvcon.anchor.Anchor.postsub>` anchors will be run.
        Lastly, before and after invoking every marching method, a pair of
        anchors will be run.  The anchors for a marching method are related to
        the name of the marching method itself.  For example, if a marching
        method is named "calcsome", anchor ``precalcsome`` will be run before
        the invocation, and anchor ``postcalcsome`` will be run afterward.

        Derived classes can set :py:attr:`marchret` dictionary, and
        :py:meth:`march` will return the dictionary at the end of execution.
        The dictionary is reset to empty at the begninning of the execution.
        """
        self.marchret = dict()
        self.step_current = 0
        self.runanchors('premarch')
        while self.step_current < steps_run:
            self.substep_current = 0
            self.runanchors('prefull')
            t0 = time.time()
            while self.substep_current < self.substep_run:
                # set up time.
                self.time = time_current
                self.time_increment = time_increment
                self.runanchors('presub')
                # run marching methods.
                for mmname in self.mmnames:
                    method = getattr(self, mmname)
                    t1 = time.time()
                    self.runanchors('pre'+mmname)
                    t2 = time.time()
                    method(worker=worker)
                    self.timer.increase(mmname, time.time() - t2)
                    self.runanchors('post'+mmname)
                    self.timer.increase(mmname+'_a', time.time() - t1)
                # increment time.
                time_current += self.time_increment/self.substep_run
                self.time = time_current
                self.time_increment = time_increment
                self.substep_current += 1
                self.runanchors('postsub')
            self.timer.increase('march', time.time() - t0)
            self.step_global += 1
            self.step_current += 1
            self.runanchors('postfull')
        self.runanchors('postmarch')
        if worker:
            worker.conn.send(self.marchret)
        return self.marchret

    def init(self, **kw):
        """
        :return: Nothing.

        Check and initialize BCs.
        """
        for arrname in self._solution_array_:
            arr = getattr(self, arrname)
            arr.fill(ALMOST_ZERO)   # prevent initializer forgets to set!
        for bc in self.bclist:
            bc.init(**kw)

    def final(self, **kw):
        pass

    def apply_bc(self):
        """
        :return: Nothing.

        Update the boundary conditions.
        """
        pass

    def call_non_interface_bc(self, name, *args, **kw):
        """
        :param name: Name of the method of BC to call.
        :type name: str
        :return: Nothing.

        Call method of each of non-interface BC objects in my list.
        """
        bclist = [bc for bc in self.bclist
            if not isinstance(bc, boundcond.interface)]
        for bc in bclist:
            try:
                getattr(bc, name)(*args, **kw)
            except Exception as e:
                e.args = tuple([str(bc), name] + list(e.args))
                raise

    ##################################################
    # parallelization.
    ##################################################
    def remote_setattr(self, name, var):
        """
        Remotely set attribute of worker.
        """
        return setattr(self, name, var)

    def pull(self, arrname, inder=False, worker=None):
        """
        :param arrname: The namd of the array to pull to master.
        :type arrname: str
        :param inder: The data array is derived data array.  Default is False.
        :type inder: bool
        :keyword worker: The worker object for communication.  Default is None.
        :type worker: solvcon.rpc.Worker
        :return: Nothing.

        Pull data array to dealer (rpc) through worker object.
        """
        conn = worker.conn
        if inder:
            arr = self.der[arrname]
        else:
            arr = getattr(self, arrname)
        conn.send(arr)

    def push(self, marr, arrname, start=0, inder=False):
        """
        :param marr: The array passed in.
        :type marr: numpy.ndarray
        :param arrname: The array to pull to master.
        :type arrname: str
        :param start: The starting index of pushing.  Default is 0.
        :type start: int
        :param inder: The data array is derived data array.  Default is False.
        :type inder: bool
        :return: Nothing.

        Push data array received from dealer (rpc) into self.
        """
        if inder:
            arr = self.der[arrname]
        else:
            arr = getattr(self, arrname)
        arr[start:] = marr[start:]

    def pullank(self, ankname, objname, worker=None):
        """
        :param ankname: The name of related anchor.
        :type ankname: str
        :param objname: The object to pull to master.
        :type objname: str
        :keyword worker: The worker object for communication.  Default is None.
        :type worker: solvcon.rpc.Worker
        :return: Nothing.

        Pull data array to dealer (rpc) through worker object.
        """
        conn = worker.conn
        obj = getattr(self.runanchors[ankname], objname)
        conn.send(obj)

    def init_exchange(self, ifacelist):
        # grab peer index.
        ibclist = list()
        for pair in ifacelist:
            if pair < 0:
                ibclist.append(pair)
            else:
                assert len(pair) == 2
                assert self.svrn in pair
                ibclist.append(sum(pair)-self.svrn)
        # replace with BC object, sendn and recvn.
        for bc in self.bclist:
            if not isinstance(bc, boundcond.interface):
                continue
            it = ibclist.index(bc.rblkn)
            sendn, recvn = ifacelist[it]
            ibclist[it] = bc, sendn, recvn
        self.ibclist = ibclist

    def exchangeibc(self, arrname, worker=None):
        threads = list()
        for ibc in self.ibclist:
            # check if sleep or not.
            if ibc < 0:
                continue 
            bc, sendn, recvn = ibc
            # determine callable and arguments.
            if self.svrn == sendn:
                target = self.pushibc
                args = arrname, bc, recvn
            elif self.svrn == recvn:
                target = self.pullibc
                args = arrname, bc, sendn
            else:
                raise ValueError, 'bc.rblkn = %d != %d or %d' % (
                    bc.rblkn, sendn, recvn) 
            kwargs = {'worker': worker}
            # call to data transfer.
            target(*args, **kwargs)

    def pushibc(self, arrname, bc, recvn, worker=None):
        """
        :param arrname: The name of the array in the object to exchange.
        :type arrname: str
        :param bc: The interface BC to push.
        :type bc: solvcon.boundcond.interface
        :param recvn: Serial number of the peer to exchange data with.
        :type recvn: int
        :keyword worker: The wrapping worker object for parallel processing.
            Default is None.
        :type worker: solvcon.rpc.Worker

        Push data toward selected interface which connect to blocks with larger
        serial number than myself.
        """
        conn = worker.pconns[bc.rblkn]
        ngstcell = self.ngstcell
        arr = getattr(self, arrname)
        # ask the receiver for data.
        shape = list(arr.shape)
        shape[0] = bc.rclp.shape[0]
        rarr = np.empty(shape, dtype=arr.dtype)
        conn.recvarr(rarr)  # comm.
        slct = bc.rclp[:,0] + ngstcell
        arr[slct] = rarr[:]
        # provide the receiver with data.
        slct = bc.rclp[:,2] + ngstcell
        conn.sendarr(arr[slct]) # comm.

    def pullibc(self, arrname, bc, sendn, worker=None):
        """
        :param arrname: The name of the array in the object to exchange.
        :type arrname: str
        :param bc: The interface BC to pull.
        :type bc: solvcon.boundcond.interface
        :param sendn: Serial number of the peer to exchange data with.
        :type sendn: int
        :keyword worker: The wrapping worker object for parallel processing.
            Default is None.
        :type worker: solvcon.rpc.Worker

        Pull data from the interface determined by the serial of peer.
        """
        conn = worker.pconns[bc.rblkn]
        ngstcell = self.ngstcell
        arr = getattr(self, arrname)
        # provide sender the data.
        slct = bc.rclp[:,2] + ngstcell
        conn.sendarr(arr[slct]) # comm.
        # ask data from sender.
        shape = list(arr.shape)
        shape[0] = bc.rclp.shape[0]
        rarr = np.empty(shape, dtype=arr.dtype)
        conn.recvarr(rarr)  # comm.
        slct = bc.rclp[:,0] + ngstcell
        arr[slct] = rarr[:]
