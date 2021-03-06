/*
 * Copyright (C) 2008-2010 Yung-Yu Chen <yyc@solvcon.net>.
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

#include "solvcon.h"
int calc_soln(MeshData *msd, ExecutionData *exd,
        FPTYPE *clvol, FPTYPE *sol, FPTYPE *soln) {
    FPTYPE *psol, *psoln, *pclvol;
    int icl, ieq;
    psol = sol + msd->ngstcell*exd->neq;
    psoln = soln + msd->ngstcell*exd->neq;
    pclvol = clvol + msd->ngstcell;
    for (icl=0; icl<msd->ncell; icl++) {
        for (ieq=0; ieq<exd->neq; ieq++) {
            psoln[ieq] = psol[ieq] + pclvol[0] * exd->time_increment / 2.0;
        };
        psol += exd->neq;
        psoln += exd->neq;
        pclvol += 1;
    };
    return 0;
};
// vim: set ts=4 et:
