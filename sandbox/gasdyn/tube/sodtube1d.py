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

import scipy.optimize as so
import matplotlib.pyplot as plt

class PlotManager():
    """
    Manage how to show the data generated by SodTube.
    Roughly speaking, it is a wrapper of matplotlib
    """
    def __init__(self):
        pass

    def plot_mesh(self, mesh):
        pass

    def plot_solution(self):
        pass

    def show_solution_comparison(self):
        plt.show()

    def get_plot_solutions_fig_rho(self,
                           solution_a,
                           solution_b,
                           solution_a_label="series 1",
                           solution_b_label="series 2"):
        return self.get_plot_solutions_fig(solution_a,
                                           solution_b,
                                           1,
                                           solution_a_label,
                                           solution_b_label)

    def get_plot_solutions_fig_v(self,
                           solution_a,
                           solution_b,
                           solution_a_label="series 1",
                           solution_b_label="series 2"):
        return self.get_plot_solutions_fig(solution_a,
                                           solution_b,
                                           2,
                                           solution_a_label,
                                           solution_b_label)

    def get_plot_solutions_fig_p(self,
                           solution_a,
                           solution_b,
                           solution_a_label="series 1",
                           solution_b_label="series 2"):
        return self.get_plot_solutions_fig(solution_a,
                                           solution_b,
                                           3,
                                           solution_a_label,
                                           solution_b_label)

    def get_plot_solutions_fig(self,
                       solution_a,
                       solution_b,
                       item,
                       solution_a_label="series 1",
                       solution_b_label="series 2"):
        ax = self.get_solution_value_list(solution_a, 0)
        ay = self.get_solution_value_list(solution_a, item)
        bx = self.get_solution_value_list(solution_b, 0)
        by = self.get_solution_value_list(solution_b, item)
        fig = plt.figure()
        ax1 = fig.add_subplot(111)
        ax1.set_title(solution_a_label + " v.s. " + solution_b_label)
        ax1.scatter(ax, ay, s=10, c='b', marker="s", label=solution_a_label)
        ax1.scatter(bx, by, s=10, c='r', marker="o", label=solution_b_label)
        plt.legend(loc='upper left')
        return fig

    def get_solution_value_list(self, solution, item):
        solution_item_list = []
        for i in solution:
            solution_item_list.append(i[item])
        return solution_item_list

class DataManager(PlotManager):
    """
    Manage how to get extended information by input data.
    """
    def __init__(self):
        pass

    def get_errorNorm(self, solution_A, solution_B):
        return solution_errornorm

    def get_l2Norm(self, solution_A, solution_B):
        return solution_errornorm

    def get_deviation(self, solution_a, solution_b):
        solution_deviation = []
        if len(solution_a) != len(solution_b):
            print("two solutions have different mesh point numbers!")

        for i in range(len(solution_a)):
            if abs(solution_a[i][0] - solution_b[i][0]) < 0.000000001:
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


    def dump_solution(self, solution):
        print'x rho v p'
        for i in solution:
            print'%f %f %f %f' % (i[0], i[1], i[2], i[3])

class SodTube():
    """
    The core to generate the 1D Sod tube test
    """
    def __init__(self):
        # initial condition
        # [(rhol, ul, pl), (rhor, ur, pr)]
        #
        # Sod's initial condition
        self.RHOL = 1.0
        self.UL = 0.0
        self.PL = 1.0
        self.RHOR = 0.125
        self.UR = 0.0
        self.PR = 0.1
        self.initcondition_sod = [(self.RHOL, self.UL, self.PL),
                                  (self.RHOR, self.UR, self.PR)]
        # initial condition for a shock tube problem
        # default is Sod's initial condition
        # users could change this initial conditions
        self.initcondition = self.initcondition_sod
        # constants and conventions
        self.GAMMA = 1.4 # ideal gas constant
        self.GAMMA2 = (self.GAMMA - 1.0) / (self.GAMMA + 1.0)
        self.ALPHA = (self.GAMMA + 1.0) / (self.GAMMA - 1.0)
        self.BETA = (self.GAMMA - 1.0) / (2.0*self.GAMMA)
        # a mesh, which has this format:
        # [point0, point1, point2, point3, ......, pointn]
        self.mesh = []
        # solution has this format:
        # [(x0, rho0, u0, p0),
        #  (x1, rho1, u1, p1),
        #  ......,
        #  (xn, rhon, un, pn)]
        self.solution = []
        self.ceseparameters = []

    def get_initcondition(self):
        return self.initcondition

    def set_initcondition(self, initcondition):
        self.initcondition = initcondition

    def gen_mesh(self):
        # this is horrible
        # implement its own generator please.
        import sodtubecmdp
        solution_client = sodtubecmdp.SolutionClient()
        solution_client.invoke("grid")
        self.mesh = solution_client._solver._grid

    def get_mesh(self):
        return self.mesh

    def get_analytic_solution(self):
        return self.cal_analytic_solution()

    def cal_analytic_solution(self, mesh, t=0.2, initcondition=None):
        # where implementing the code to get the analytic solution
        # by users' input condition
        # default is the Sod's condition
        initcondition = initcondition or self.initcondition

        rho4 = self.get_analytic_density_region4()
        u4 = self.get_analytic_velocity_region4()
        p4 = self.get_analytic_pressure_region4()
        
        rho3 = self.get_analytic_density_region3()
        u3 = self.get_analytic_velocity_region3()
        p3 = self.get_analytic_pressure_region3()
        
        x_shock = self.get_velocity_shock()*t
        x_disconti = u3*t
        x_fan_right = self.get_velocity_fan_right()*t
        x_fan_left = self.get_velocity_fan_left()*t
        
        solution = []
        for x in mesh:
            if x < x_fan_left or x == x_fan_left:
                solution.append((x,
                                 self.get_density_region1(),
                                 self.get_velocity_region1(),
                                 self.get_pressure_region1()))
            elif x > x_fan_left and (x < x_fan_right or x == x_fan_right):
                d = self.get_analytic_density_region2(float(x),t)
                v = self.get_analytic_velocity_region2(float(x),t)
                p = self.get_analytic_pressure_region2(float(x),t)
                solution.append((x,
                                 d,
                                 v,
                                 p))
            elif x > x_fan_right and (x < x_disconti or x == x_disconti):
                solution.append((x,
                                 rho3,
                                 u3,
                                 p3))
            elif x > x_disconti and (x < x_shock or x == x_shock):
                solution.append((x,
                                 rho4,
                                 u4,
                                 p4))
            elif x > x_shock:
                solution.append((x,
                                self.get_density_region5(),
                                self.get_velocity_region5(),
                                self.get_pressure_region5()))
            else:
                print("Something wrong!!!")

        return solution

    ##########################
    ### Analytical formula ###
    ##########################
    def analytic_pressure_region4(self, x):
        """
        x: the root value we want to know.

        This method return the formula to get the solution
        of the pressure in the region 4.
        It is a equation that could get the solution
        by numerical approaches, e.g. Newton method.

        For details how to derive the equation, someone
        could refer to, for example, the equation (10.51)
        of Pieter Wesseling,
        Principles of Computational Fluid Dynamics

        The method and the return equation will be
        used by scipy numerial method, e.g.
        scipy.newton
        So, the method and the return value format
        follow the request of scipy.
        """
        p1 = self.PL
        p5 = self.get_pressure_region5()
        c1 = self.get_velocity_c1()
        c5 = self.get_velocity_c5()
        beta = self.BETA
        gamma = self.GAMMA
        return ((x/p1) - \
                ((1.0 - \
                    ((gamma-1.0)*c5*((x/p5) - 1.0))/ \
                    (c1*((2.0*gamma*(gamma-1.0+(gamma+1.0)*(x/p5)))**0.5)) \
                 )**(1.0/beta)))

    ################
    ### Velocity ###
    ################
    def get_velocity_fan_left(self):
        c1 = self.get_velocity_c1()
        return -c1

    def get_velocity_fan_right(self):
        u3 = self.get_analytic_velocity_region3()
        c3 = self.get_velocity_c3()
        return u3 - c3

    def get_velocity_shock(self):
        # P409, Wesseling P.
        c5 = self.get_velocity_c5() # 1.0583
        gamma = self.GAMMA
        p4 = self.get_analytic_pressure_region4() # 0.3031
        p5 = self.get_pressure_region5() # 0.1
        return c5*((1.0+(((gamma+1.0)*((p4/p5)-1.0))/(2.0*gamma)))**0.5)

    def get_velocity_c1(self):
        return ((self.GAMMA*self.PL/self.RHOL)**0.5)

    def get_velocity_c3(self):
        p3 = self.get_analytic_pressure_region3()
        rho3 = self.get_analytic_density_region3()
        return (self.GAMMA*p3/rho3)**0.5

    def get_velocity_c5(self):
        return ((self.GAMMA*self.PR/self.RHOR)**0.5)

    def get_velocity_region1(self):
        return self.UL

    def get_analytic_velocity_region2(self, x, t):
        c1 = self.get_velocity_c1()
        gamma = self.GAMMA
        return 2.0/(gamma+1.0)*(c1+x/t)

    def get_analytic_velocity_region3(self):
        return self.get_analytic_velocity_region4()

    def get_analytic_velocity_region4(self):
        """
        The equation could be found in the
        equation next to (10.48), Wesseling P.,
        Principles of Computational Fluid Dynamics
        """
        gamma = self.GAMMA
        p4 = self.get_analytic_pressure_region4()
        p5 = self.get_pressure_region5()
        p = p4/p5
        c5 = self.get_velocity_c5()
        return c5*(p-1.0)*(2.0/(gamma*(gamma-1.0+(gamma+1.0)*p)))**0.5

    def get_velocity_region5(self):
        return self.UR

    ################
    ### Pressure ###
    ################
    def get_pressure_region1(self):
        return self.PL

    def get_analytic_pressure_region2(self, x, t):
        # (10.44) Wesssling P.
        c1 = self.get_velocity_c1()
        u2 = self.get_analytic_velocity_region2(x, t)
        p1 = self.PL
        gamma = self.GAMMA
        beta = self.BETA
        return p1*(1.0-(gamma-1.0)*u2/2/c1)**(1.0/beta)

    def get_analytic_pressure_region3(self):
        return self.get_analytic_pressure_region4() 

    def get_analytic_pressure_region4(self):
        return self.get_analytic_pressure_region4_by_newton()

    def get_analytic_pressure_region4_by_newton(self, x0=1):
        """
        x0 : the guess initial value to be applied in Newton method
        """
        return so.newton(self.analytic_pressure_region4,x0)

    def get_pressure_region5(self):
        return self.PR

    ################
    ### Density  ###
    ################
    def get_density_region1(self):
        return self.RHOL

    def get_analytic_density_region2(self, x,t):
        # (10.45), Wesseling P.
        # Principles of Computational Fluid Dynamics
        gamma = self.GAMMA
        rho1 = self.RHOL
        p1 = self.get_pressure_region1()
        p2 = self.get_analytic_pressure_region2(x, t)
        return rho1*(p2/p1)**(1.0/gamma)

    def get_analytic_density_region3(self):
        # P410, Wesseling P.
        # Principles of Computational Fluid Dynamics
        rho1 = self.get_density_region1()
        p1 = self.get_pressure_region1()
        p3 = self.get_analytic_pressure_region3()
        return rho1*(p3/p1)**(1.0/self.GAMMA)

    def get_analytic_density_region4(self):
        # P410, Wesseling P.
        # Principles of Computational Fluid Dynamics
        alpha = self.ALPHA
        p4 = self.get_analytic_pressure_region4()
        p5 = self.get_pressure_region5()
        p = p4/p5
        rho5 = self.get_density_region5()
        return rho5*(1.0+alpha*p)/(alpha+p)

    def get_density_region5(self):
        return self.RHOR 

    def get_cese_solution(self):
        import numpy as np
        
        it = 100 # iteration, which is integer
        dt = 0.004
        dx = 0.01
        ga = 1.4
        
        rhol = 1.0
        ul = 0.0
        pl = 1.0
        rhor = 0.125
        ur = 0.0
        pr = 0.1
        
        ia = 1
        
        mtxq = np.asmatrix(np.zeros(shape=(3,1000)))
        mtxqn = np.asmatrix(np.zeros(shape=(3,1000)))
        mtxqx = np.asmatrix(np.zeros(shape=(3,1000)))
        mtxqt = np.asmatrix(np.zeros(shape=(3,1000)))
        mtxs = np.asmatrix(np.zeros(shape=(3,1000)))
        vxl = np.zeros(shape=(3,1))
        vxr = np.zeros(shape=(3,1))
        xx = np.zeros(shape=(1000))
        
        mtxf = np.asmatrix(np.zeros(shape=(3,3)))
        
        hdt = dt/2.0
        qdt = dt/4.0 #q:quad
        hdx = dx/2.0
        qdx = dx/4.0
        
        tt = hdt*it
        dtx = dt/dx
        
        a1 = ga - 1.0
        a2 = 3.0 - ga
        a3 = a2/2.0
        a4 = 1.5*a1
        mtxq[0][0] = rhol
        mtxq[1][0] = rhol*ul
        mtxq[2][0] = pl/a1 + 0.5*rhol*ul**2.0
        itp = it + 1
        for i in xrange(itp):
            mtxq[0,i+1] = rhor
            mtxq[1,i+1] = rhor*ur
            mtxq[2,i+1] = pr/a1 + 0.5*rhor*ur**2.0
            # this was done by qx = np.zeros(shape=(3,1000))
            # for j in xrange(3):
            #     qx[j][i] = 0.0
        
        m = 2
        mtxf = np.asmatrix(np.zeros(shape=(3,3)))
        for i in xrange(it):
            for j in xrange(m):
                w2 = mtxq[1,j]/mtxq[0,j]
                w3 = mtxq[2,j]/mtxq[0,j]
                # f[0][0] = 0.0
                mtxf[0,1] = 1.0
                # f[0][2] = 0.0
                mtxf[1,0] = -a3*w2**2
                mtxf[1,1] = a2*w2
                mtxf[1,2] = ga - 1.0
                mtxf[2,0] = a1*w2**3 - ga*w2*w3
                mtxf[2,1] = ga*w3 - a1*w2**2
                mtxf[2,2] = ga*w2
        
                mtxqt[:,j] = -1.0*mtxf*mtxqx[:,j]
                mtxs[:,j] = qdx*mtxqx[:,j] + dtx*mtxf*mtxq[:,j] \
                            - dtx*qdt*mtxf*mtxf*mtxqx[:,j]
        
            mm = m - 1
            for j in xrange(mm):
                mtxqn[:,j+1] = 0.5*(mtxq[:,j] \
                                    + mtxq[:,j+1] \
                                    + mtxs[:,j] - mtxs[:,j+1]) # why?
                vxl = np.asarray((mtxqn[:,j+1] - mtxq[:,j] - hdt*mtxqt[:,j]) \
                                  /hdx)
                vxr = np.asarray((mtxq[:,j+1] \
                                  + hdt*mtxqt[:,j+1] \
                                  - mtxqn[:,j+1]) \
                                  /hdx) # why?
                mtxqx[:,j+1] = np.asmatrix((vxl*((abs(vxr))**ia) \
                                            + vxr*((abs(vxl))**ia)) \
                                            /(((abs(vxl))**ia) \
                                                + ((abs(vxr))**ia) + 1.0E-60))
        
            for j in xrange(1,m):
                mtxq[:,j] = mtxqn[:,j]
        
            m = m + 1
        
        t2 = dx*float(itp)
        xx[0] = -0.5*t2
        for i in xrange(itp):
            xx[i+1] = xx[i] + dx
       
        solution = []
        for i in xrange(m):
            x = mtxq[1,i]/mtxq[0,i]
            z = a1*(mtxq[2,i] - 0.5*(x**2)*mtxq[0,i])
            solution.append((xx[i],mtxq[0,i],x,z))

        #return self.solution
        return solution

    def cal_cese_solution(self, initcondition, mesh, ceseparameters):
        return self.solution

