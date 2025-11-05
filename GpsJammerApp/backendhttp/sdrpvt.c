#include "nml.h"
#include "sdr.h"

 
 
 

 
 
 
extern int pvtProcessor(void)
{
  mlock(hobsvecmtx);
  int numSat = sdrstat.nsatValid;
  unmlock(hobsvecmtx);

  double *pr_v = (double *)malloc(numSat * sizeof(double));
  double *Xs_v = (double *)malloc(numSat * 3 * sizeof(double));
   

   
   
  double *rcvr_tow_v = (double *)malloc(numSat * sizeof(double));
  double *prRaw_v = (double *)malloc(numSat * sizeof(double));
  double *prSvClkCorr_v = (double *)malloc(numSat * sizeof(double));
  double *snr_v = (double *)malloc(numSat * sizeof(double));

  double tau;
  double lambda;
  double phi;
  double height;
  double rcvr_tow;
  double lat, lon;

   
  mlock(hobsvecmtx);
  for (int i=0; i<numSat; i++) {
    int prn = sdrstat.obsValidList[i];
    prRaw_v[i]         = sdrstat.obs_v[(prn-1)*11+5];
    rcvr_tow_v[i]      = sdrstat.obs_v[(prn-1)*11+6];
    snr_v[i]           = sdrstat.obs_v[(prn-1)*11+8];
  }
  unmlock(hobsvecmtx);

   
  rcvr_tow = rcvr_tow_v[0];

   
  double xyzdt_v[] = {0,0,0,0};
  double xs_v[3];
  double svClkCorr;
  double transmitTime;
  double gdop = 0.0;
  int ret = 0;

   
   
   
  for (int i=0; i<numSat; i++) {
     

    mlock(hobsvecmtx);
    pr_v[i] = prRaw_v[i] - sdrstat.xyzdt[3];
    unmlock(hobsvecmtx);

     
    tau = pr_v[i] / CTIME;

     
    transmitTime = rcvr_tow - tau;
    mlock(hobsvecmtx);
    ret = satPos(&sdrch[sdrstat.obsValidList[i]-1].nav.sdreph, transmitTime, xs_v,
             &svClkCorr);
    unmlock(hobsvecmtx);
    if (ret != 0) {
      printf("Function satPos has xs NaN for G%02d, exiting pvtProcessor\n",
             sdrstat.obsValidList[i]);
      goto errorDetected;
    }

     
    if (isnan(xs_v[0]) || isnan(xs_v[0]) || isnan(xs_v[0])) {
       
       
      goto errorDetected;
    }

     
    prSvClkCorr_v[i] = prRaw_v[i] + (CTIME * svClkCorr);

     
     
    Xs_v[(i*3)+0] = xs_v[0];
    Xs_v[(i*3)+1] = xs_v[1];
    Xs_v[(i*3)+2] = xs_v[2];

     
    mlock(hobsvecmtx);
    int prn = sdrstat.obsValidList[i];
    sdrstat.obs_v[(prn-1)*11+2] = xs_v[0];
    sdrstat.obs_v[(prn-1)*11+3] = xs_v[1];
    sdrstat.obs_v[(prn-1)*11+4] = xs_v[2];
    unmlock(hobsvecmtx);

  }  

   
  if (sdrstat.nsatValid<4) {
    goto errorDetected;
  }

   
   
  if (sdrini.ekfFilterOn==0) {
    ret = blsFilter(Xs_v, prSvClkCorr_v, numSat, xyzdt_v, &gdop);
  } else {
     
  }

   
  if (isnan(xyzdt_v[0]) || isnan(xyzdt_v[1]) || isnan(xyzdt_v[2])) {
    printf("Function estRcvrPosn gets NaN for xu, exiting pvtProcessor\n");
    goto errorDetected;
  }

   
  ecef2lla(xyzdt_v[0], xyzdt_v[1], xyzdt_v[2], &lambda, &phi, &height);

   
  lat = phi * 180.0/M_PI;
  lon = lambda * 180.0/M_PI;

   
  mlock(hobsvecmtx);
  sdrstat.lat = lat;
  sdrstat.lon = lon;
  sdrstat.hgt = height;
  sdrstat.gdop = gdop;
  sdrstat.xyzdt[0] = xyzdt_v[0];
  sdrstat.xyzdt[1] = xyzdt_v[1];
  sdrstat.xyzdt[2] = xyzdt_v[2];
  sdrstat.xyzdt[3] = xyzdt_v[3];
  unmlock(hobsvecmtx);

   
  free(Xs_v);
  free(pr_v);

  free(prRaw_v);
  free(prSvClkCorr_v);
  free(snr_v);
  free(rcvr_tow_v);

  return 0;

errorDetected:
   
  mlock(hobsvecmtx);
  sdrstat.lat = 0.0;
  sdrstat.lon = 0.0;
  sdrstat.hgt = 0.0;
  sdrstat.gdop = 0.0;
  unmlock(hobsvecmtx);

   
  free(Xs_v);
  free(pr_v);

  free(prRaw_v);
  free(prSvClkCorr_v);
  free(snr_v);
  free(rcvr_tow_v);

   
  return -1;
}  

 
 
 
extern int blsFilter(double *X_v, double *pr_v, int numSat,
                 double xyzdt_v[], double *gdop)
{
   
  numSat = sdrstat.nsatValid;

   
  nml_mat *x, *A, *W, *pos, *omc;
  nml_mat *At, *AtA, *AtW, *AtWA, *iAtA, *iAtWA, *iAtWAAt, *iAtWAAtW, *tempPos;

   
  x = nml_mat_new(4,1);
  pos = nml_mat_new(4,1);
   
  W = nml_mat_new(numSat,numSat);
  omc = nml_mat_new(numSat,1);
  At = nml_mat_new(4,numSat);
  AtA = nml_mat_new(4,4);
  AtW = nml_mat_new(4,numSat);
  AtWA = nml_mat_new(4,4);
  iAtA = nml_mat_new(4,4);
  iAtWA = nml_mat_new(4,4);
  iAtWAAt = nml_mat_new(4,numSat);
  iAtWAAtW = nml_mat_new(4,numSat);
  tempPos = nml_mat_new(4,1);

   
  double Rot_X_v[] = {0,0,0};
  double pos_v[] = {0,0,0,0};
  double rho2 = 0.0;
  double travelTime = 0.0;
  double omegatau = 0.0;
  double rhoSq = 0.0;
  double *A_v = (double *)calloc(numSat * 4, sizeof(double));
  double *W_v = (double *)calloc(numSat * numSat, sizeof(double));
  double det = 0.0;
  double detTol = 1e-12;
  double trop = 0.0;
  double *omc_v = (double *)calloc(numSat, sizeof(double));
  int ret = 0;
  double az, el;
  double D = 0.0;
  double X[] = {0,0,0};
  double dx[] = {0,0,0};
  double normX = 100.0;
  int iter = 0;

   
  pos_v[0] = (double)sdrini.xu0_v[0];
  pos_v[1] = (double)sdrini.xu0_v[1];
  pos_v[2] = (double)sdrini.xu0_v[2];
   
   
   
   

   
  mlock(hobsvecmtx);
  sdrekf.varR = 5.0 * 5.0;        
  for (int i=0; i<32; i++) {
    sdrekf.rk1_v[i] = 0.0;
  }
  for (int k=0; k<numSat; k++) {
     
    int prn = sdrstat.obsValidList[k];
    sdrekf.rk1_v[prn-1] = sdrekf.varR;

    double el2 = sdrstat.obs_v[(prn-1)*11+10];
    if ((sdrstat.azElCalculatedflag) && (el2 < 30)) {
      sdrekf.rk1_v[prn-1] = sdrekf.varR +
        (25 - (25/15)*(el2-15.0)) * (25 - (25/15)*(el2-15.0));
    }

     
    W_v[k + (k*numSat)] = 1.0 / sdrekf.rk1_v[prn-1];
  }
  unmlock(hobsvecmtx);

   
  int nmbOfIterations = 10;

   
   
  for (int j=0; j<nmbOfIterations; j++) {
   

     
    if (normX < 1.0e-10) {
       
      break;
    }

     
     
    for (int i=0; i<numSat; i++) {
       
      if (iter==0) {
        for (int k=0; k<3; k++) {
          Rot_X_v[k] = X_v[i*3+k];
        }
        trop = 2.0;
      } else {

       
      rho2 = ( ( (X_v[i*3+0] - pos_v[0]) * (X_v[i*3+0] - pos_v[0]) ) +
               ( (X_v[i*3+1] - pos_v[1]) * (X_v[i*3+1] - pos_v[1]) ) +
               ( (X_v[i*3+2] - pos_v[2]) * (X_v[i*3+2] - pos_v[2]) ) );

       
      travelTime = sqrt(rho2) / CTIME;

       
       
      omegatau =  OMEGAEDOT * travelTime;
      Rot_X_v[0] =  (cos(omegatau) * X_v[i*3+0])  + (sin(omegatau) * X_v[i*3+1]);
      Rot_X_v[1] = (-sin(omegatau) * X_v[i*3+0]) + (cos(omegatau) * X_v[i*3+1]);
      Rot_X_v[2] = X_v[i*3+2];

       
      for (int i=0; i<3; i++) {
        X[i] = pos_v[i];
        dx[i] = Rot_X_v[i] - pos_v[i];
      }
      ret = topocent(X, dx, &az, &el, &D);
      if (ret!=0) {
        printf("topocent function: error\n");
      }
      sdrstat.azElCalculatedflag = 1;   

       
      mlock(hobsvecmtx);
      int prn = sdrstat.obsValidList[i];
      sdrstat.obs_v[(prn-1)*11+2] = Rot_X_v[0];
      sdrstat.obs_v[(prn-1)*11+3] = Rot_X_v[1];
      sdrstat.obs_v[(prn-1)*11+4] = Rot_X_v[2];
      sdrstat.obs_v[(prn-1)*11+9] = az;
      sdrstat.obs_v[(prn-1)*11+10] = el;
      unmlock(hobsvecmtx);

       
      ret = tropo(sin(el*D2R), 0.0, 1013.0, 293.0, 50.0,
                               0.0, 0.0, 0.0, &trop);
      if (ret!=0) {
        printf("tropo function: error\n");
      }

      }  

       
       
      rhoSq = ( ( (Rot_X_v[0] - pos_v[0]) * (Rot_X_v[0] - pos_v[0]) ) +
                ( (Rot_X_v[1] - pos_v[1]) * (Rot_X_v[1] - pos_v[1]) ) +
                ( (Rot_X_v[2] - pos_v[2]) * (Rot_X_v[2] - pos_v[2]) ) );

       
      omc_v[i] = pr_v[i] - sqrt(rhoSq) - pos_v[3] - trop;

       
      A_v[i*4+0] = (-(Rot_X_v[0] - pos_v[0])) / sqrt(rhoSq);
      A_v[i*4+1] = (-(Rot_X_v[1] - pos_v[1])) / sqrt(rhoSq);
      A_v[i*4+2] = (-(Rot_X_v[2] - pos_v[2])) / sqrt(rhoSq);
      A_v[i*4+3] = 1.0;

    }  

     

     
     

     
    W = nml_mat_from(numSat,numSat,numSat*numSat,W_v);
    A = nml_mat_from(numSat,4,numSat*4,A_v);  
    At = nml_mat_transp(A);             

     
    AtA = nml_mat_dot(At,A);      
    AtW = nml_mat_dot(At,W);      
    AtWA = nml_mat_dot(AtW,A);    

     
    nml_mat_lup *lupAtA;
    lupAtA = nml_mat_lup_solve(AtA);          
    nml_mat_lup *lupAtWA;
    lupAtWA = nml_mat_lup_solve(AtWA);        

     
    det = nml_mat_det(lupAtA);
    if (fabs(det)<detTol) {
      printf("Exiting estRcvrPosn, determinant=%lf\n", det);
      goto errorDetected;
    }

     
    iAtA = nml_mat_inv(lupAtA);                
    nml_mat_lup_free(lupAtA);
    iAtWA = nml_mat_inv(lupAtWA);              
    nml_mat_lup_free(lupAtWA);

     
    iAtWAAt = nml_mat_dot(iAtWA,At);       
    iAtWAAtW = nml_mat_dot(iAtWAAt,W);     
    omc = nml_mat_from(numSat,1,numSat,omc_v);  
    x   = nml_mat_dot(iAtWAAtW,omc);       

     
    tempPos = nml_mat_from(4,1,4,pos_v);              
    pos = nml_mat_add(tempPos,x);                    

     
    pos_v[0] = pos->data[0][0];
    pos_v[1] = pos->data[1][0];
    pos_v[2] = pos->data[2][0];
    pos_v[3] = pos->data[3][0];

     
    normX = sqrt( (x->data[0][0]*x->data[0][0]) +
                  (x->data[1][1]*x->data[1][1]) +
                  (x->data[2][2]*x->data[2][2]) +
                  (x->data[3][3]*x->data[3][3]) );

     
    iter = iter + 1;

  }  

   
  xyzdt_v[0] = pos->data[0][0];
  xyzdt_v[1] = pos->data[1][0];
  xyzdt_v[2] = pos->data[2][0];
  xyzdt_v[3] = pos->data[3][0];

   
  *gdop =  sqrt( iAtA->data[0][0] + iAtA->data[1][1] +
                 iAtA->data[2][2] + iAtA->data[3][3] );

   
  mlock(hobsvecmtx);
  for (int i=0; i<32; i++) {
    sdrstat.vk1_v[i] = 0;
  }
  for (int j=0; j<numSat; j++) {
      int prn = sdrstat.obsValidList[j];
      sdrstat.vk1_v[prn-1] = omc_v[j];
  }
  unmlock(hobsvecmtx);

   
  nml_mat_free(x);
  nml_mat_free(A);
  nml_mat_free(W);
  nml_mat_free(pos);
  nml_mat_free(omc);
  nml_mat_free(At);
  nml_mat_free(AtA);
  nml_mat_free(AtW);
  nml_mat_free(AtWA);
  nml_mat_free(iAtA);
  nml_mat_free(iAtWA);
  nml_mat_free(iAtWAAt);
  nml_mat_free(iAtWAAtW);
  nml_mat_free(tempPos);

   
  free(A_v);
  free(W_v);
  free(omc_v);

   
  return 0;

errorDetected:
   
  xyzdt_v[0] = 0.0;
  xyzdt_v[1] = 0.0;
  xyzdt_v[2] = 0.0;
  xyzdt_v[3] = 0.0;
  *gdop = 0.0;

   
  nml_mat_free(x);
  nml_mat_free(A);
  nml_mat_free(W);
  nml_mat_free(pos);
  nml_mat_free(omc);
  nml_mat_free(At);
  nml_mat_free(AtA);
  nml_mat_free(AtW);
  nml_mat_free(AtWA);
  nml_mat_free(iAtA);
  nml_mat_free(iAtWA);
  nml_mat_free(iAtWAAt);
  nml_mat_free(iAtWAAtW);
  nml_mat_free(tempPos);

   
  free(A_v);
  free(W_v);
  free(omc_v);

   
  return -1;

}  

 
 
 
extern void check_t(double time, double *corrTime) {

  
 double halfweek = 302400.0;

  
 *corrTime = time;

  
 if (time > halfweek) {
  *corrTime = time - (2 * halfweek);
 }  else if (time < -halfweek) {
  *corrTime = time + (2 * halfweek);
 }
}  

 
 
 
extern void ecef2lla(double x, double y, double z,
                    double *lambda, double *phi, double *height)
{
  
 double A = 6378137.0;   
 double F = 1.0 / 298.257223563;   
 double E = sqrt( (2*F) - (F*F) );

  
 *lambda = atan2(y,x);
 double p = sqrt(x * x + y * y);

  
 *height = 0.0;
 *phi = atan2(z, p*(1.0 - E*E));
 double N = A / sqrt( (1.0 - sin(*phi)) * (1.0 - sin(*phi)) );
 double delta_h = 1000000;

  
 while (delta_h > 0.01) {
   double prev_h = *height;
   *phi = atan2(z, p*(1-(E*E) * (N / (N + *height) ) ) );
   N = A / sqrt( (1 - ( (E * sin(*phi)) * (E * sin(*phi)) ) ) );
   *height = (p / cos(*phi)) - N;
   delta_h = fabs(*height - prev_h);
 }
}  

 
 
 
extern int satPos(sdreph_t *sdreph, double transmitTime, double svPos[3],
            double *svClkCorr)
{
   
   
   
   
  double toe                      = sdreph->eph.toes;
  double toc						= toe;
   
  double sqrta                    = sqrt(sdreph->eph.A);
  double e                        = sdreph->eph.e;
  double M0                       = sdreph->eph.M0;
  double omega                    = sdreph->eph.omg;
  double i0                       = sdreph->eph.i0;
  double Omega0                   = sdreph->eph.OMG0;
  double deltan                   = sdreph->eph.deln;
  double idot                     = sdreph->eph.idot;
  double Omegadot                 = sdreph->eph.OMGd;
  double cuc                      = sdreph->eph.cuc;
  double cus                      = sdreph->eph.cus;
  double crc                      = sdreph->eph.crc;
  double crs                      = sdreph->eph.crs;
  double cic                      = sdreph->eph.cic;
  double cis                      = sdreph->eph.cis;
  double af0                      = sdreph->eph.f0;
  double af1                      = sdreph->eph.f1;
  double af2                      = sdreph->eph.f2;
  double tgd                      = sdreph->eph.tgd[0];

   

   
  double t = transmitTime;  
  double A;
  double n0, n;
  double tk, tc;
  double Mk, vk, ik, phik, u_k, rk, Omega_k;
  double delta_uk, delta_rk, delta_ik;
  double x_kp, y_kp;
  double xk, yk, zk;
  double E0, Ek, dtr, dt;
  int ii;

   
  svPos[0] = 0.0; svPos[1] = 0.0; svPos[2] = 0.0;

   
   
   
   

   
  A = sqrta * sqrta;            

   
  n0 = sqrt( MU / (A*A*A) );

   
  tk = t - toe;               
  if (tk > 302400) {
    tk = tk - (2 * 302400);
  }
  else if (tk < -302400) {
  	tk = tk + (604800);
  }

   
  n = n0 + deltan;

   
  Mk = M0 + n*tk;

   
  E0 = Mk;

  for (ii=0; ii<3; ii++){
    Ek = E0 + (Mk - E0 + e * sin(E0)) / (1 - e * cos(E0));
    E0 = Ek;
  }

   
  vk = 2 * atan( sqrt( (1.0 + e) / (1.0 - e) ) * tan(Ek / 2) );

   
  phik = omega + vk;

   
  delta_uk = cus * sin(2.0 * phik) + cuc * cos(2.0 * phik);
  delta_rk = crs * sin(2.0 * phik) + crc * cos(2.0 * phik);
  delta_ik = cis * sin(2.0 * phik) + cic * cos(2.0 * phik);

   
  u_k = phik + delta_uk;

   
  rk = A * (1.0 - (e * cos(Ek))) + delta_rk;

   
  ik = i0 + (idot * tk) + delta_ik;

   
  x_kp = rk * cos(u_k);
  y_kp = rk * sin(u_k);

   
  Omega_k = Omega0 + (Omegadot - OMEGAEDOT) * tk - (OMEGAEDOT * toe);

   
  xk = (x_kp * cos(Omega_k)) - (y_kp * sin(Omega_k) * cos(ik));
  yk = (x_kp * sin(Omega_k)) + (y_kp * cos(Omega_k) * cos(ik));
  zk =                          y_kp * sin(ik);

  if ( isnan(xk) || isnan(yk) || isnan(zk) ) {
    goto errorDetected;
  }

   
  svPos[0] = xk; svPos[1] = yk; svPos[2] = zk;

   
   
   

   
  tc = t - toc;               
  if (tc > 302400) {
    tc = tc - (2 * 302400);
  }
  else if (tc < -302400) {
    tc = tc + (604800);
  }

   
  dtr = -2 * sqrt(MU) / (CTIME * CTIME) * e * sqrta * sin(Ek);

   
   
   
  dt = af0 + (af1 * tc) + (af2 * (tc * tc)) - tgd + dtr;
  *svClkCorr = dt;

   
  return 0;

 
errorDetected:
  return -1;

}  

 
 
 
extern void rot(double R[9], double angle, int axis) {
 R[0] = 1.0; R[4] = 1.0; R[8] = 1.0;
 R[1] = 0.0; R[3] = 0.0; R[6] = 0.0;
 R[2] = 0.0; R[5] = 0.0; R[7] = 0.0;

 double cang, sang;
 cang = cos(angle * M_PI/180.0);
 sang = sin(angle * M_PI/180.0);

 if (axis == 1) {
  R[4] = cang;
  R[8] = cang;
  R[5] = sang;
  R[7] = -sang;
 }
 if (axis == 2) {
  R[0] = cang;
  R[8] = cang;
  R[2] = -sang;
  R[6] = sang;
 }
 if (axis == 3) {
  R[0] = cang;
  R[4] = cang;
  R[3] = -sang;
  R[1] = sang;
 }
}  

 
 
 
 
 
extern void precheckObs()
{

   
  int ret = 0;
  int updateRequired = 0;
  int prn = 0;
  int i = 0;
  double tol = 1e-15;  
  char buffer[MSG_LENGTH];

   
  mlock(hobsvecmtx);
  for (i=0; i<sdrstat.nsatValid; i++) {
    prn = sdrstat.obsValidList[i];

     
    if (sdrstat.obs_v[(prn-1) * 11 + 8] < SNR_PVT_THRES) {
      sdrstat.obs_v[(prn-1) * 11 + 1] = 0;
      snprintf(buffer, sizeof(buffer),
        "%.3f  preCheckObs: G%02d has SNR:%.1f\n",
        sdrstat.elapsedTime, prn,
        sdrstat.obs_v[(prn-1) * 11 + 8]);
      add_message(buffer);
      updateRequired = 1;
    }  

     
    if (sdrstat.obs_v[(prn-1) * 11 + 7] < GPS_WEEK) {
      sdrstat.obs_v[(prn-1) * 11 + 1] = 0;
      snprintf(buffer, sizeof(buffer),
        "%.3f  preCheckObs: G%02d has Week:%d\n",
        sdrstat.elapsedTime, prn,
         (int)sdrstat.obs_v[(prn-1) * 11 + 7]);
      add_message(buffer);
      updateRequired = 1;
    }  

     
    if (sdrstat.obs_v[(prn-1) * 11 + 6] < 1.0) {
      sdrstat.obs_v[(prn-1) * 11 + 1] = 0;
      snprintf(buffer, sizeof(buffer),
        "%.3f  preCheckObs: G%02d has ToW:%.1f\n",
        sdrstat.elapsedTime, prn,
         sdrstat.obs_v[(prn-1) * 11 + 6]);
      add_message(buffer);
      updateRequired = 1;
    }  

     
    if (sdrstat.obs_v[(prn-1) * 11 + 5] < LOW_PR) {
      sdrstat.obs_v[(prn-1) * 11 + 1] = 0;
      snprintf(buffer, sizeof(buffer),
        "%.3f  preCheckObs: G%02d has Low PR:%.1f\n",
        sdrstat.elapsedTime, prn,
         sdrstat.obs_v[(prn-1) * 11 + 5]);
      add_message(buffer);
      updateRequired = 1;
    }  

     
    if (sdrstat.obs_v[(prn-1) * 11 + 5] > HIGH_PR) {
      sdrstat.obs_v[(prn-1) * 11 + 1] = 0;
      snprintf(buffer, sizeof(buffer),
        "%.3f  preCheckObs: G%02d has High PR:%.1f\n",
        sdrstat.elapsedTime, prn,
         sdrstat.obs_v[(prn-1) * 11 + 5]);
      add_message(buffer);
      updateRequired = 1;
    }  

     
    if ( (sdrch[prn-1].nav.sdreph.eph.toes<1.0) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.A)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.e)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.M0)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.omg)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.i0)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.OMG0)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.deln)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.idot)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.OMGd)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.cuc)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.cus)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.crc)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.crs)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.cic)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.cis)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.f0)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.f1)<tol) ||
         (fabs(sdrch[prn-1].nav.sdreph.eph.tgd[0])<tol) ){

       
      sdrstat.obs_v[(prn-1) * 11 + 1] = 0;
      snprintf(buffer, sizeof(buffer),
        "%.3f  precheckEPH: G%02d tagged for removal for eph error\n",
        sdrstat.elapsedTime, prn);
      add_message(buffer);
      updateRequired = 1;
    }  

     
     
    if (sdrstat.azElCalculatedflag) {
      if (sdrstat.obs_v[(prn-1) * 11 + 10] < SV_EL_PVT_MASK) {
        sdrstat.obs_v[(prn-1) * 11 + 1] = 0;
        snprintf(buffer, sizeof(buffer),
            "%.3f  precheckObs: G%02d tagged for removal with el of %.1f\n",
             sdrstat.elapsedTime, prn, sdrstat.obs_v[(prn-1) * 11 + 10]);
        add_message(buffer);
        updateRequired = 1;
      }  
    }  

   
  }  

   
  unmlock(hobsvecmtx);

   
  if (updateRequired) {
    ret = updateObsList();
    if (ret==-1) { printf("updateObsList: error\n"); }
  }

   
}

 
 
 
extern int tropo(double sinel, double hsta, double p, double tkel,
                 double hum, double hp, double htkel, double hhum,
                 double *ddr) {

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 

 
 
 
 
 
 

double a_e    = 6378.137;      
double b0     = 7.839257e-5;
double tlapse = -6.5;
double tkhum  = tkel + tlapse * (hhum - htkel);
double atkel  = 7.5*(tkhum-273.15) / (237.3+tkhum-273.15);
double e0     = 0.0611 * hum * pow(10,atkel);
double tksea  = tkel - tlapse * htkel;
double em     = -978.77 / (2.8704e6*tlapse*1.0e-5);
double tkelh  = tksea + tlapse*hhum;
double e0sea  = e0 * pow((tksea/tkelh),(4*em));
double tkelp  = tksea + tlapse*hp;
double psea   = p * pow((tksea/tkelp),em);
double alpha[] = {0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0};
double rn[] = {0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0};

if (sinel < 0) {
    sinel = 0;
}

double tropo   = 0;
int done    = 0;
double refsea  = 77.624e-6 / tksea;
double htop    = 1.1385e-5 / refsea;
refsea  = refsea * psea;
double ref     = refsea * pow(((htop-hsta)/htop),4);

while (1) {
    double rtop = pow((a_e+htop),2) - pow((a_e+hsta),2)*(1-pow(sinel,2));

     
    if (rtop < 0) {
        rtop = 0;
    }

    rtop = sqrt(rtop) - (a_e+hsta)*sinel;
    double a    = -sinel/(htop-hsta);
    double b    = -b0*(1-pow(sinel,2)) / (htop-hsta);
     

    for (int i=0; i<7; i++) {
        rn[i] = pow(rtop,(i+2));
    }

    alpha[0] = 2 * a;
    alpha[1] = 2 * pow(a,2) + 4 * b/3;
    alpha[2] = a * (pow(a,2) + 3 * b);
    alpha[3] = pow(a,4)/5 + 2.4 * pow(a,2) * b + 1.2 * pow(b,2);
    alpha[4] = 2 * a * b * (pow(a,2) + 3 * b) / 3;
    alpha[5] = pow(b,2) * (6 * pow(a,2) + 4 * b) * 1.428571e-1;
    alpha[6] =     0.0;
    alpha[7] =     0.0;

    if (pow(b,2) > 1.0e-35) {
        alpha[6] = a*pow(b,3)/2;
        alpha[7] = pow(b,4)/9;
    }

    double dr = rtop;
     
    for (int i=0; i<7; i++) {
      dr = dr + alpha[i] * rn[i];
    }

    tropo = tropo + dr * ref * 1000;

    if (done == 1) {
        *ddr = tropo;
        break;
    }

    done    = 1;
    refsea  = (371900.0e-6 / tksea - 12.92e-6) / tksea;
    htop    = 1.1385e-5 * (1255 / tksea + 0.05) / refsea;
    ref     = refsea * e0sea * pow(((htop-hsta)/htop),4);

}  

 
return 0;

}  

 
 
 
extern int togeod(double a, double finv, double X, double Y, double Z,
                  double *dphi, double *dlambda, double *h) {
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 

 
 
 
 
 
 
 
 

  *h       = 0;
  double tolsq   = 1.e-10;
  double maxit   = 50;
  double esq = 0.0;
  double sinphi = 0.0;

   
   

   
  if (finv < 1.e-20) {
    esq = 0;
  } else {
    esq = (2 - 1/finv) / finv;
  }

  double oneesq  = 1 - esq;

   
   
  double P = sqrt(X*X+Y*Y);
   

  if (P > 1.e-20) {
    *dlambda = atan2(Y,X) * R2D;
  } else {
    *dlambda = 0;
  }

  if (*dlambda < 0) {
    *dlambda = *dlambda + 360;
  }

   
  double r = sqrt(P*P + Z*Z);

  if (r > 1.e-20) {
    sinphi = Z/r;
  } else {
    sinphi = 0;
  }

  *dphi = asin(sinphi);

   
   
  if (r < 1.e-20) {
    *h = 0;
    goto errorDetected;
  }

  *h = r - a * (1 - sinphi * sinphi / finv);

   
  for (int i=0; i<maxit; i++) {
    double sinphi  = sin(*dphi);
    double cosphi  = cos(*dphi);

     
    double N_phi   = a / sqrt(1 - esq * sinphi * sinphi);

     
    double dP      = P - (N_phi + *h) * cosphi;
    double dZ      = Z - (N_phi * oneesq + *h) * sinphi;

     
    *h       = *h + (sinphi*dZ + cosphi*dP);
    *dphi    = *dphi + (cosphi*dZ - sinphi*dP)/(N_phi + *h);

     
    if (dP*dP + dZ*dZ < tolsq) {
        break;
    }

     
    if (i == maxit) {
        printf("Problem in TOGEOD, did not converge in %2d iterations\n", i);
    }
  }  

  *dphi = *dphi * R2D;

   
  return 0;

errorDetected:
    printf("togeod--- errorDetected\n");
    return -1;

}  

 
 
 
extern int topocent(double X[], double dx[], double *Az, double *El, double *D) {
 
 
 
 
 
 
 
 
 
 
 
 
 
 

 
 
 
 
 
 

int ret;
 
double local_v[3] = {0};
double phi;
double lambda;
double h;

ret = togeod(6378137, 298.257223563, X[0], X[1], X[2], &phi, &lambda, &h);
if (ret!=0) {
 printf("togeod function: error\n");
}

double cl  = cos(lambda * D2R);
double sl  = sin(lambda * D2R);
double cb  = cos(phi * D2R);
double sb  = sin(phi * D2R);

 
 
 
 

 
local_v[0] = -sl * dx[0] + cl * dx[1] + 0.0 * dx[2];
local_v[1] = -sb*cl * dx[0] - sb*sl * dx[1] + cb * dx[2];
local_v[2] = cb*cl * dx[0] + cb*sl * dx[1] + sb * dx[2];

double E   = local_v[0];
double N   = local_v[1];
double U   = local_v[2];

double hor_dis = sqrt(E*E + N*N);

if (hor_dis < 1.e-20) {
  *Az = 0.0;
  *El = 90;
} else {
  *Az = atan2(E, N)/D2R;
  *El = atan2(U, hor_dis)/D2R;
}

if (*Az < 0) {
  *Az = *Az + 360;
}

*D   = sqrt(dx[0]*dx[0] + dx[1]*dx[1] + dx[2]*dx[2]);

return 0;
}   

 
 
 
extern int updateObsList(void) {

  mlock(hobsvecmtx);
   
  sdrstat.nsatValid = 0;

   
  for (int j=0; j<32; j++) {
    sdrstat.obsValidList[j] = 0;
  }

   
  for (int i=0; i<32; i++) {
     if (sdrstat.obs_v[i*11+1]==1) {
      sdrstat.obsValidList[sdrstat.nsatValid] = sdrstat.obs_v[i*11+0];
      sdrstat.nsatValid = sdrstat.nsatValid + 1;
    }   
  }  
  unmlock(hobsvecmtx);

  return 0;
}
