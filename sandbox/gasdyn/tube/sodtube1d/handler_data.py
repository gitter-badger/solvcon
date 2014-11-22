#!/usr/bin/python
#
# sodtube1d.py
#
# Description:
#     1D Sod Tube Test
#
#     This program is implemented by OO style to be
#     a part of ipython notebook demo materials.
#
#     The derivation of the equations for the analytic solution
#     is based on the book,
#     Principles of Computational Fluid Dynamics,
#     written by Pieter Wesseling.
#     Or, someone could refer to the solvcon website
#     http://www.solvcon.net/en/latest/cese.html#sod-s-shock-tube-problem
#
#
# DEBUG: search string 'DEBUG'
# why: somewhere don't understand very much ...

import sys
import scipy.optimize as so
import matplotlib.pyplot as plt

# a number to claim two floating number value are equal.
delta_precision = 0.0000000000001

class DataManager():
    """
    Manage how to get extended information by input data.
    """
    def __init__(self):
        pass

    def get_errorNorm(self, solution_a, solution_b):
        return solution_errornorm

    def get_l2_norm(self, solution_a, solution_b, vi=1, filter=[]):
        """
        vi(vector_i)
            1:rho
            2:v
            3:p
        filter = [(x1,x2),(x3,x4),...], x1 < x2, x3 < x4
            when caculating l2 norm,
            data between x1 and x2, and x3 and x4,
            will be ignored.
            data on x1, x2, x3 and x4 will be adopted.
        """
        solution_deviation_square = self.get_deviation_square(solution_a, solution_b)
        l2_norm = 0
        sds = [] # deviation square of the solution

        # remove the deviation square value in the specific intervals
        for solution_dev_sqr_vector in solution_deviation_square:
            if len(filter) > 0:
                sdsv = solution_dev_sqr_vector[vi]
                for interval in filter:
                    if interval[0] < solution_dev_sqr_vector[0] < interval[1]:
                        sdsv = 0.
                sds.append(sdsv)
            else:
                sds.append(solution_dev_sqr_vector[vi])
        return sum(sds)

    def get_deviation(self, solution_a, solution_b):
        """
        Note:
            only the mesh grid points of solution_a
            will be adopted.
        """
        solution_deviation = []
        if len(solution_a) != len(solution_b):
            print("two solutions have different mesh point numbers!")
            solution_c = []
            for i in solution_a:
                for j in solution_b:
                    if abs(i[0] - j[0]) < delta_precision:
                        solution_c.append(j)
            solution_b = solution_c

        for i in range(len(solution_a)):
            if abs(solution_a[i][0] - solution_b[i][0]) < delta_precision:
                # 0.000000001 is a bad way
                # the mesh points are not the same
                # because they are not generated by the same
                # mesh generator,
                # and the float number will differ in the very small
                # order.
                x = solution_a[i][0]
                drho_abs = abs(solution_a[i][1] - solution_b[i][1])
                dv_abs = abs(solution_a[i][2] - solution_b[i][2])
                dp_abs = abs(solution_a[i][3] - solution_b[i][3])
                solution_deviation.append((x, drho_abs, dv_abs, dp_abs))
            else:
                print("two solutions have different mesh point!!")

        if len(solution_deviation) == len(solution_a):
            return solution_deviation
        else:
            print("sth. wrong when getting deviation!!")

    def get_deviation_percent(self, solution_a, solution_b):
        solution_deviation = self.get_deviation(solution_a, solution_b)
        solution_deviation_precent = []
        for i in range(len(solution_deviation)):
            solution_deviation_precent.append((solution_a[i][0],
                solution_deviation[i][1]/(solution_a[i][1]+1e-20),
                solution_deviation[i][2]/(solution_a[i][2]+1e-20),
                solution_deviation[i][3]/(solution_a[i][3]+1e-20)))
        return solution_deviation_precent

    def get_deviation_square(self, solution_a, solution_b):
        solution_deviation_square = []
        solution_deviation = self.get_deviation(solution_a, solution_b)
        for i in range(len(solution_deviation)):
            solution_deviation_square.append((
                solution_deviation[i][0],
                solution_deviation[i][1]*solution_deviation[i][1],
                solution_deviation[i][2]*solution_deviation[i][2],
                solution_deviation[i][3]*solution_deviation[i][3]))
        return solution_deviation_square

    def dump_solution(self, solution):
        print'x rho v p'
        for i in solution:
            print'%f %f %f %f' % (i[0], i[1], i[2], i[3])
