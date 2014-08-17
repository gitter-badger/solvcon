#!/usr/bin/python
#
# sodtube1d.py
#
#
# 1D Sod Tube Test
#
# This program is implemented by OO style to be
# a part of ipython notebook demo materials.
#
# DEBUG: search string 'DEBUG'

import scipy.optimize as so

class PlotManager():
    """
    Manage how to show the data generated by SodTube.
    Roughly speaking, it is a wrapper of matplotlib
    """
    def __init__(self):
        pass

    def plotMesh(self, mesh):
        pass

    def plotSolution(self, solution):
        pass

class DataManager(PlotManager):
    """
    Manage how to get extended information by input data.
    """
    def __init__(self):
        pass

    def get_ErrorNorm(self, solution_A, solution_B):
        return solution_errornorm

    def get_L2Norm(self, solution_A, solution_B):
        return solution_errornorm

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

    def get_Initcondition(self):
        return self.initcondition

    def setInitcondition(self, initcondition):
        self.initcondition = initcondition

    def get_Mesh(self):
        return self.mesh

    def get_AnalyticSolution(self):
        return self.calAnalyticSolution()

    def calAnalyticSolution(self, initcondition=None):
        # where implementing the code to get the analytic solution
        # by users' input condition
        # default is the Sod's condition
        initcondition = initcondition or self.initcondition
        solution = []
        return solution

    ##########################
    ### Analytical formula ###
    ##########################
    def analyticPressureRegion4(self, x):
        # DEBUG: REMOVE ME AFTER DEVELOPMENT
        #return ((x-pr)*(((1.0-gamma2)/(rhor*(x+gamma2*pr)))**0.5)) - (((pl**beta)-(x**beta))*(((1.0-gamma2**2)*(pl**(1.0/gamma))/((gamma2**2)*rhol))**0.5)) # wiki

        # (10.51) Wesseling P.
        p1 = self.PL
        p5 = self.get_PressureRegion5()
        c1 = self.get_VelocityC1()
        c5 = self.get_VelocityC5()
        beta = self.BETA
        gamma = self.GAMMA
        return ((x/p1) - ((1.0 - ((gamma-1.0)*c5*((x/p5) - 1.0))/(c1*((2.0*gamma*(gamma-1.0+(gamma+1.0)*(x/p5)))**0.5)))**(1.0/beta)))

    ################
    ### Velocity ###
    ################
    def get_VelocityFanLeft(self):
        c1 = self.get_VelocityC1()
        return -c1

    def get_VelocityFanRight(self):
        u3 = self.get_AnalyticVelocityRegion3()
        c3 = self.get_VelocityC3()
        return u3 - c3

    def get_VelocityShock(self):
        # P409, Wesseling P.
        c5 = self.get_VelocityC5()
        gamma = self.GAMMA
        p4 = self.get_AnalyticPressureRegion4()
        p5 = self.get_PressureRegion5()
        return c5*(1.0+(gamma+1.0)/2.0/gamma*((p4/p5)-1.0))*0.5

    def get_VelocityC1(self):
        return ((self.GAMMA*self.PL/self.RHOL)**0.5)

    def get_VelocityC3(self):
        p3 = self.get_AnalyticPressureRegion3()
        rho3 = self.get_AnalyticDensityRegion3()
        return (self.GAMMA*p3/rho3)**0.5

    def get_VelocityC5(self):
        return ((self.GAMMA*self.PR/self.RHOR)**0.5)

    def get_VelocityRegion1(self):
        return self.UL

    def get_AnalyticVelocityRegion2(self, x, t):
        c1 = self.get_VelocityC1()
        gamma = self.GAMMA
        return 2.0/(gamma+1.0)*(c1+x/t)

    def get_AnalyticVelocityRegion3(self):
        return self.get_AnalyticVelocityRegion4()

    def get_AnalyticVelocityRegion4(self): # ~0.916 for Sod tube problem
        #gamma = self.GAMMA
        #c5 = self.get_VelocityC5()
        #p5 = self.PR
        #return x - (ushock/gamma)*(x/pr-1.0)*(((2*gamma/(gamma+1.0))/((x/pr)+(gamma-1.0)/(gamma+1.0)))**0.5)

        # next to (10.51), P410, Wesseling P.
        # Need to verified...
        #c1 = self.get_VelocityC1()
        #beta = self.BETA
        #gamma = self.GAMMA
        #p1 = self.get_PressureRegion1()
        #p4 = self.get_AnalyticPressureRegion4()
        #return p1 - x + 2.0/(gamma-1.0)*c1*(1.0 - (p4/p1)**(beta))

        # next to (10.48), Wesseling P. # ~0.306 for Sod tube problem
        gamma = self.GAMMA
        p4 = self.get_AnalyticPressureRegion4()
        p5 = self.get_PressureRegion5()
        p = p4/p5
        c5 = self.get_VelocityC5()
        return c5*(p-1.0)*(2.0/(gamma*(gamma-1.0+(gamma+1.0)*p)))**0.5

    def get_VelocityRegion5(self):
        return self.UR

    ################
    ### Pressure ###
    ################
    def get_PressureRegion1(self):
        return self.PL

    def get_AnalyticPressureRegion2(self, x, t):
        # (10.44) Wesssling P.
        c1 = self.get_VelocityC1()
        u2 = self.get_AnalyticVelocityRegion2(x, t)
        p1 = self.PL
        gamma = self.GAMMA
        beta = self.BETA
        return p1*(1.0-(gamma-1.0)*u2/2/c1)**(1.0/beta)

    def get_AnalyticPressureRegion3(self):
        return self.get_AnalyticPressureRegion4() 

    def get_AnalyticPressureRegion4(self):
        return self.get_AnalyticPressureRegion4ByNewton()

    def get_AnalyticPressureRegion4ByNewton(self, x0=1):
        """
        x0 : the guess initial value to be applied in Newton method
        """
        return so.newton(self.analyticPressureRegion4,x0)

    def get_PressureRegion5(self):
        return self.PR

    ################
    ### Density  ###
    ################
    def get_DensityRegion1(self):
        return self.RHOL

    def get_AnalyticDensityRegion2(self, x,t):
        # (10.45), Wesseling P.
        gamma = self.GAMMA
        rho1 = self.RHOL
        p1 = self.get_PressureRegion1()
        p2 = self.get_AnalyticPressureRegion2(x, t)
        return rho1*(p2/p1)**(1.0/gamma)

    def get_AnalyticDensityRegion3(self):
        # P410, Wesseling P.
        rho1 = self.get_DensityRegion1()
        p1 = self.get_PressureRegion1()
        p3 = self.get_AnalyticPressureRegion3()
        return rho1*(p3/p1)**(1.0/self.GAMMA)

    def get_AnalyticDensityRegion4(self):
        # P410, Wesseling P.
        alpha = self.ALPHA
        p4 = self.get_AnalyticPressureRegion4()
        p5 = self.get_PressureRegion5()
        p = p4/p5
        rho5 = self.get_DensityRegion5()
        return rho5*(1.0+alpha*p)/(alpha+p)

    def get_DensityRegion5(self):
        return self.RHOR 

    def get_CESESolution(self):
        return self.solution

    def calCESESolution(self, initcondition, mesh, ceseparameters):
        return self.solution

