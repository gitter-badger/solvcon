#!/usr/bin/env python

import numpy as np

from velstress import material

class VeMaterial(material.Material):
    def __init__(self, **kw):
        self.rho = kw["rho"]
        self.Gep = kw['Gep']
        self.Gem = kw['Gem']
        self.Glp = kw['Glp']
        self.Glm = kw['Glm']
        self.tau = kw['tau']
    def get_jacos(self, ndim):
        sumGlp = 0.0
        sumGlm = 0.0
        rho = self.rho
        Gep = self.Gep
        Gem = self.Gem
        Glp = self.Glp
        Glm = self.Glm
        tau = self.tau
        for i in range(6):
            sumGlp += Glp[i]
            sumGlm += Glm[i]
        if ndim == 3:
            jacos = np.zeros((3,45,45), dtype='float64')
            jacos[0][0][3] = -1.0/rho 
            jacos[0][1][8] = -1.0/rho 
            jacos[0][2][7] = -1.0/rho
            jacos[0][3][0] = (-Gep-sumGlp)
            jacos[0][4][0] = (2*(Gem+sumGlm)-Gep-sumGlp) 
            jacos[0][5][0] = (2*(Gem+sumGlm)-Gep-sumGlp)
            jacos[0][7][2] = (-Gem-sumGlm)
            jacos[0][8][1] = (-Gem-sumGlm)
                
            jacos[1][0][8] = -1.0/rho
            jacos[1][1][4] = -1.0/rho
            jacos[1][2][6] = -1.0/rho
            jacos[1][3][1] = (2*(Gem+sumGlm)-Gep-sumGlp)
            jacos[1][4][1] = (-Gep-sumGlp)
            jacos[1][5][1] = (2*(Gem+sumGlm)-Gep-sumGlp)
            jacos[1][6][2] = (-Gem-sumGlm)
            jacos[1][8][0] = (-Gem-sumGlm)
                
            jacos[2][0][7] = -1.0/rho
            jacos[2][1][6] = -1.0/rho
            jacos[2][2][5] = -1.0/rho
            jacos[2][3][2] = (2*(Gem+sumGlm)-Gep-sumGlp)
            jacos[2][4][2] = (2*(Gem+sumGlm)-Gep-sumGlp)
            jacos[2][5][2] = (-Gep-sumGlp)
            jacos[2][6][1] = (-Gem-sumGlm)
            jacos[2][7][0] = (-Gem-sumGlm)
            for i in range(6):
                jacos[0][9+i][0]= (Glp[i]/tau[i]+Glm[i]/tau[i])
                jacos[0][15+i][0] = (Glp[i]/tau[i]-Glm[i]/tau[i])
                jacos[0][21+i][0] = (Glp[i]/tau[i]-Glm[i]/tau[i])
                jacos[0][33+i][2] = Glm[i]/tau[i]
                jacos[0][39+i][1] = Glm[i]/tau[i]

                jacos[1][9+i][1]= (Glp[i]/tau[i]-Glm[i]/tau[i])
                jacos[1][15+i][1] = (Glp[i]/tau[i]+Glm[i]/tau[i])
                jacos[1][21+i][1] = (Glp[i]/tau[i]-Glm[i]/tau[i])
                jacos[1][27+i][2] = Glm[i]/tau[i]
                jacos[1][39+i][0] = Glm[i]/tau[i]

                jacos[2][9+i][2]= (Glp[i]/tau[i]-Glm[i]/tau[i])
                jacos[2][15+i][2] = (Glp[i]/tau[i]-Glm[i]/tau[i])
                jacos[2][21+i][2] = (Glp[i]/tau[i]+Glm[i]/tau[i])
                jacos[2][27+i][1] = Glm[i]/tau[i]
                jacos[2][33+i][0] = Glm[i]/tau[i]
        if ndim == 2:
            jacos = np.zeros((2,23,23), dtype='float64')
            jacos[0][0][2] = -1.0/rho 
            jacos[0][1][4] = -1.0/rho 
            jacos[0][2][0] = (-Gep-sumGlp)
            jacos[0][3][0] = (2*(Gem+sumGlm)-Gep-sumGlp) 
            jacos[0][4][1] = (-Gem-sumGlm)
                
            jacos[1][0][4] = -1.0/rho
            jacos[1][1][3] = -1.0/rho
            jacos[1][2][1] = (2*(Gem+sumGlm)-Gep-sumGlp)
            jacos[1][3][1] = (-Gep-sumGlp)
            jacos[1][4][0] = (-Gem-sumGlm)

            for i in range(6):
                jacos[0][5+i][0]= (Glp[i]/tau[i]+Glm[i]/tau[i])
                jacos[0][11+i][0] = (Glp[i]/tau[i]-Glm[i]/tau[i])
                jacos[0][17+i][2] = Glm[i]/tau[i]

                jacos[1][5+i][1]= (Glp[i]/tau[i]-Glm[i]/tau[i])
                jacos[1][11+i][1] = (Glp[i]/tau[i]+Glm[i]/tau[i])
                jacos[1][17+i][0] = Glm[i]/tau[i]
        return jacos

class SoftTissue(VeMaterial):
    def __init__(self, **kw):
        kw.setdefault('rho', 1100.0)
        kw.setdefault('Gep', 0.98666)
        kw.setdefault('Gem', 0.98666)
        kw.setdefault('Glp', [0.0025, 0.000368, 0.000744, 0.000132, 0.000511, 
                              0.000753])
        kw.setdefault('Glm', [0.0025, 0.000368, 0.000744, 0.000132, 0.000511, 
                              0.000753])
        kw.setdefault('tau', [3.1567e-9, 1.0508e-8, 3.3761e-8, 3.1344e-7, 
                              3.2936e-6, 3.1123e-5])
        super(SoftTissue, self). __init__(**kw)

if __name__ == "__main__":
    test = VeMaterial()
    test.get_jacos(3)
