/*
 * Copyright (C) 2008-2012 Yung-Yu Chen <yyc@solvcon.net>.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#include <Python.h>

#include "mesh.h"
#include "lincese_algorithm.h"

#define NDIM 3
#define NEQ exd->neq

void sc_lincese_calc_soln(sc_mesh_t *msd, sc_lincese_algorithm_t *exd) {
    int clnfc, fcnnd;
    // partial pointers.
    int *pclfcs, *pfcnds, *pfccls;
    double *pjcecnd, *pcecnd, *pcevol, (*psfmrc)[NDIM];
    double *pjsol, *pdsol, *pjsolt, *psoln;
    // scalars.
    double hdt, qdt;
    double voe, fusp, futm;
    // arrays.
    double usfc[NEQ];
    double fcn[NEQ][NDIM], dfcn[NEQ][NDIM];
    double jacos[NEQ][NEQ][NDIM];
    // interators.
    int icl, ifl, inf, ifc, jcl, ieq, jeq;
    qdt = exd->time_increment * 0.25;
    hdt = exd->time_increment * 0.5;
    #pragma omp parallel for private(clnfc, fcnnd, \
    pclfcs, pfcnds, pfccls, pjcecnd, pcecnd, pcevol, psfmrc, \
    pjsol, pdsol, pjsolt, psoln, \
    voe, fusp, futm, usfc, fcn, dfcn, jacos, \
    icl, ifl, inf, ifc, jcl, ieq, jeq) \
    firstprivate(hdt, qdt)
    for (icl=0; icl<msd->ncell; icl++) {
        psoln = exd->soln + icl*NEQ;
        pcevol = exd->cevol + icl*(CLMFC+1);
        // initialize fluxes.
        for (ieq=0; ieq<NEQ; ieq++) {
            psoln[ieq] = 0.0;
        };

        pclfcs = msd->clfcs + icl*(CLMFC+1);
        clnfc = pclfcs[0];
        for (ifl=1; ifl<=clnfc; ifl++) {
            ifc = pclfcs[ifl];

            // spatial flux (given time).
            pfccls = msd->fccls + ifc*FCREL;
            jcl = pfccls[0] + pfccls[1] - icl;
            pjcecnd = exd->cecnd + jcl*(CLMFC+1)*NDIM;
            pcecnd = exd->cecnd + (icl*(CLMFC+1)+ifl)*NDIM;
            pjsol = exd->sol + jcl*NEQ;
            pdsol = exd->dsol + jcl*NEQ*NDIM;
            for (ieq=0; ieq<NEQ; ieq++) {
                fusp = pjsol[ieq];
                fusp += (pcecnd[0]-pjcecnd[0]) * pdsol[0];
                fusp += (pcecnd[1]-pjcecnd[1]) * pdsol[1];
#if NDIM == 3
                fusp += (pcecnd[2]-pjcecnd[2]) * pdsol[2];
#endif
                psoln[ieq] += fusp * pcevol[ifl];
                pdsol += NDIM;
            };

            // temporal flux (give space).
            exd->jacofunc(exd, jcl, (double *)fcn, (double *)jacos);
            pjsolt = exd->solt + jcl*NEQ;
            fcnnd = msd->fcnds[ifc*(FCMND+1)];
            for (inf=0; inf<fcnnd; inf++) {
                psfmrc = (double (*)[NDIM])(exd->sfmrc
                    + (((icl*CLMFC + ifl-1)*FCMND+inf)*2*NDIM));
                // solution at sub-face center.
                pdsol = exd->dsol + jcl*NEQ*NDIM;
                for (ieq=0; ieq<NEQ; ieq++) {
                    usfc[ieq] = qdt * pjsolt[ieq];
                    usfc[ieq] += (psfmrc[0][0]-pjcecnd[0]) * pdsol[0];
                    usfc[ieq] += (psfmrc[0][1]-pjcecnd[1]) * pdsol[1];
#if NDIM == 3
                    usfc[ieq] += (psfmrc[0][2]-pjcecnd[2]) * pdsol[2];
#endif
                    pdsol += NDIM;
                };
                // spatial derivatives.
                for (ieq=0; ieq<NEQ; ieq++) {
                    dfcn[ieq][0] = fcn[ieq][0];
                    dfcn[ieq][1] = fcn[ieq][1];
#if NDIM == 3
                    dfcn[ieq][2] = fcn[ieq][2];
#endif
                    for (jeq=0; jeq<NEQ; jeq++) {
                        dfcn[ieq][0] += jacos[ieq][jeq][0] * usfc[jeq];
                        dfcn[ieq][1] += jacos[ieq][jeq][1] * usfc[jeq];
#if NDIM == 3
                        dfcn[ieq][2] += jacos[ieq][jeq][2] * usfc[jeq];
#endif
                    };
                };
                // temporal flux.
                for (ieq=0; ieq<NEQ; ieq++) {
                    futm = 0.0;
                    futm += dfcn[ieq][0] * psfmrc[1][0];
                    futm += dfcn[ieq][1] * psfmrc[1][1];
#if NDIM == 3
                    futm += dfcn[ieq][2] * psfmrc[1][2];
#endif
                    psoln[ieq] -= hdt*futm;
                };
            };
        };

        // update solutions.
        for (ieq=0; ieq<NEQ; ieq++) {
            psoln[ieq] /= pcevol[0];
        };
    };
};

// vim: set ts=4 et:
