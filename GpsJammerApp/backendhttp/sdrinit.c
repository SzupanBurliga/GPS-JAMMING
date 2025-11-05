#include "sdr.h"

 
extern int loadinit(sdrini_t *ini, const char *filename)
{
    int i;
    ini->fend = FEND_FRTLSDR;
    ini->f_cf[0] = 1575.42e6;
    ini->f_sf[0] = 2.048e6;
    ini->f_if[0] = 0.0;
    ini->dtype[0] = 2;
    ini->f_cf[1] = 0.0;
    ini->f_sf[1] = 0.0;
    ini->f_if[1] = 0.0;
    ini->dtype[1] = 0;
    strcpy(ini->file, filename);
    ini->useif = ON;
    ini->rtlsdrppmerr = 0;
    ini->trkcorrn = 4;
    ini->trkcorrd = 1;
    ini->trkcorrp = 1;
    ini->trkdllb[0] = 5.0;
    ini->trkpllb[0] = 30.0;
    ini->trkfllb[0] = 200.0;
    ini->trkdllb[1] = 2.0;
    ini->trkpllb[1] = 20.0;
    ini->trkfllb[1] = 50.0;
    ini->nch = 32;
    int prn[32] = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32};
    int sys[32] = {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1};
    int ctype[32] = {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1};
    int ftype[32] = {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1};
    for(i=0;i<32;i++) {
        ini->prn[i] = prn[i];
        ini->sys[i] = sys[i];
        ini->ctype[i] = ctype[i];
        ini->ftype[i] = ftype[i];
    }
    ini->pltacq = 0;
    ini->plttrk = 0;
    ini->outms = 200;
    ini->sbas = 0;
    ini->pltspec = 0;
    ini->xu0_v[0] = 693570;
    ini->xu0_v[1] = -5193930;
    ini->xu0_v[2] = 3624632;
    ini->ekfFilterOn = 0;
    ini->nchL1 = 0;
    for (i=0;i<ini->nch;i++) {
        if (ini->ctype[i]==1) {  
            ini->nchL1++;
        }
    }
    return 0;
}

 
 
 
 
 
extern int chk_initvalue(sdrini_t *ini)
{
     
    if ((ini->f_sf[0]<=0||ini->f_sf[0]>100e6) ||
        (ini->f_if[0]<0 ||ini->f_if[0]>100e6)) {
            SDRPRINTF("error: wrong freq. input sf1: %.0f if1: %.0f\n",
                ini->f_sf[0],ini->f_if[0]);
            return -1;
    }

     

     
    if (ini->fend==FEND_FILE   || ini->fend==FEND_FRTLSDR) {
        if (ini->useif) {
            FILE *fp = fopen(ini->file, "r");
            if (!fp) {
                SDRPRINTF("error: file doesn't exist: %s\n",ini->file);
                return -1;
            }
            fclose(fp);
        }
        if (!ini->useif) {
            SDRPRINTF("error: file is not selected\n");
            return -1;
        }
    }

    return 0;
}

 
 
 
 
 
extern void openhandles(void)
{
     
    initmlock(hbuffmtx);
    initmlock(hreadmtx);
    initmlock(hfftmtx);
    initmlock(hobsmtx);
    initmlock(hresetmtx);
    initmlock(hobsvecmtx);
    initmlock(hmsgmtx);
}

 
 
 
 
 
extern void closehandles(void)
{
     
    delmlock(hbuffmtx);
    delmlock(hreadmtx);
    delmlock(hfftmtx);
    delmlock(hobsmtx);
    delmlock(hresetmtx);
    delmlock(hobsvecmtx);
    delmlock(hmsgmtx);
}

 
 
 
 
 
 
 
 
extern void initacqstruct(int sys, int ctype, int prn, sdracq_t *acq)
{
    if (ctype==CTYPE_L1CA) acq->intg=ACQINTG_L1CA;

    acq->hband=ACQHBAND;
    acq->step=ACQSTEP;
    acq->nfreq=2*(ACQHBAND/ACQSTEP)+1;
}

 
 
 
 
 
extern void inittrkprmstruct(sdrtrk_t *trk)
{
     
    trk->prm1.dllb=sdrini.trkdllb[0];
    trk->prm1.pllb=sdrini.trkpllb[0];
    trk->prm1.fllb=sdrini.trkfllb[0];
    trk->prm2.dllb=sdrini.trkdllb[1];
    trk->prm2.pllb=sdrini.trkpllb[1];
    trk->prm2.fllb=sdrini.trkfllb[1];

     
    trk->prm1.dllw2=(trk->prm1.dllb/0.53)*(trk->prm1.dllb/0.53);
    trk->prm1.dllaw=1.414*(trk->prm1.dllb/0.53);
    trk->prm1.pllw2=(trk->prm1.pllb/0.53)*(trk->prm1.pllb/0.53);
    trk->prm1.pllaw=1.414*(trk->prm1.pllb/0.53);
    trk->prm1.fllw =trk->prm1.fllb/0.25;

     
    trk->prm2.dllw2=(trk->prm2.dllb/0.53)*(trk->prm2.dllb/0.53);
    trk->prm2.dllaw=1.414*(trk->prm2.dllb/0.53);
    trk->prm2.pllw2=(trk->prm2.pllb/0.53)*(trk->prm2.pllb/0.53);
    trk->prm2.pllaw=1.414*(trk->prm2.pllb/0.53);
    trk->prm2.fllw =trk->prm2.fllb/0.25;
}

 
 
 
 
 
 
 
 
extern int inittrkstruct(int sat, int ctype, double ctime, sdrtrk_t *trk)
{
    int i;
    int ctimems=(int)(ctime*1000);

     
    inittrkprmstruct(trk);

     
    trk->corrn=sdrini.trkcorrn;
    trk->corrp=(int *)malloc(sizeof(int)*trk->corrn);
    for (i=0;i<trk->corrn;i++) {
        trk->corrp[i]=sdrini.trkcorrd*(i+1);
        if (trk->corrp[i]==sdrini.trkcorrp){
            trk->ne=2*(i+1)-1;  
            trk->nl=2*(i+1);    
        }
    }
     
    (trk->corrx=(double *)calloc(2*trk->corrn+1,sizeof(double)));
    for (i=1;i<=trk->corrn;i++) {
        trk->corrx[2*i-1]=-sdrini.trkcorrd*i;
        trk->corrx[2*i  ]= sdrini.trkcorrd*i;
    }

    trk->II     =(double*)calloc(1+2*trk->corrn,sizeof(double));
    trk->QQ     =(double*)calloc(1+2*trk->corrn,sizeof(double));
    trk->oldI   =(double*)calloc(1+2*trk->corrn,sizeof(double));
    trk->oldQ   =(double*)calloc(1+2*trk->corrn,sizeof(double));
    trk->sumI   =(double*)calloc(1+2*trk->corrn,sizeof(double));
    trk->sumQ   =(double*)calloc(1+2*trk->corrn,sizeof(double));
    trk->oldsumI=(double*)calloc(1+2*trk->corrn,sizeof(double));
    trk->oldsumQ=(double*)calloc(1+2*trk->corrn,sizeof(double));

    if (ctype==CTYPE_L1CA)   trk->loop=LOOP_L1CA;
    if (ctype==CTYPE_L1SBAS) trk->loop=LOOP_SBAS;

     
    trk->loopms=trk->loop*ctimems;

    if (!trk->II||!trk->QQ||!trk->oldI||!trk->oldQ||!trk->sumI||!trk->sumQ||
        !trk->oldsumI||!trk->oldsumQ) {
        SDRPRINTF("error: inittrkstruct memory allocation\n");
        return -1;
    }
    return 0;
}

 
 
 
 
 
 
 
 
extern int initnavstruct(int sys, int ctype, int prn, sdrnav_t *nav)
{
    int i;
    int pre_l1ca[8]= { 1,-1,-1,-1, 1,-1, 1, 1};  
    int pre_sbs[24]= { 1,-1, 1,-1, 1, 1,-1,-1,-1, 1,
                       1,-1,-1, 1,-1, 1,-1,-1, 1, 1,
                       1 -1,-1, 1};  

    int poly[2]={V27POLYB,V27POLYA};

    nav->ctype=ctype;
    nav->sdreph.ctype=ctype;
    nav->sdreph.prn=prn;
    nav->sdreph.eph.iodc=-1;

     
    if (ctype==CTYPE_L1CA) {
        nav->rate=NAVRATE_L1CA;
        nav->flen=NAVFLEN_L1CA;
        nav->addflen=NAVADDFLEN_L1CA;
        nav->prelen=NAVPRELEN_L1CA;
        nav->sdreph.cntth=NAVEPHCNT_L1CA;
        nav->update=(int)(nav->flen*nav->rate);
        memcpy(nav->prebits,pre_l1ca,sizeof(int)*nav->prelen);

         
        nav->ocode=(short *)calloc(nav->rate,sizeof(short));
        for (i=0;i<nav->rate;i++) nav->ocode[i]=1;
    }
     
     
    if (ctype==CTYPE_L1SBAS) {
        nav->rate=NAVRATE_SBAS;
        nav->flen=NAVFLEN_SBAS;
        nav->addflen=NAVADDFLEN_SBAS;
        nav->prelen=NAVPRELEN_SBAS;
        nav->sdreph.cntth=NAVEPHCNT_SBAS;
        nav->update=(int)(nav->flen/3*nav->rate);
        memcpy(nav->prebits,pre_sbs,sizeof(int)*nav->prelen);

         
        if((nav->fec=create_viterbi27_port(NAVFLEN_SBAS/2))==NULL) {
            SDRPRINTF("error: create_viterbi27 failed\n");
            return -1;
        }
         
        set_viterbi27_polynomial_port(poly);

         
        nav->ocode=(short *)calloc(nav->rate,sizeof(short));
        for (i=0;i<nav->rate;i++) nav->ocode[i]=1;
    }

    if (!(nav->bitsync= (int *)calloc(nav->rate,sizeof(int))) ||
        !(nav->fbits=   (int *)calloc(nav->flen+nav->addflen,sizeof(int))) ||
        !(nav->fbitsdec=(int *)calloc(nav->flen+nav->addflen,sizeof(int)))) {
            SDRPRINTF("error: initnavstruct memory alocation\n");
            return -1;
    }
    return 0;
}

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
extern int initsdrch(int chno, int sys, int prn, int ctype, int dtype,
                     int ftype, int f_gain, int f_bias, int f_clock, double f_cf, double f_sf, double f_if,
                     sdrch_t *sdr)
{
    int i;
    short *rcode;

    sdr->no=chno;
    sdr->sys=sys;
    sdr->prn=prn;
    sdr->sat=satno(sys,prn);
    sdr->ctype=ctype;
    sdr->dtype=dtype;
    sdr->ftype=ftype;
    sdr->f_sf=f_sf;
    sdr->f_gain=f_gain;
    sdr->f_bias=f_bias;
    sdr->f_clock=f_clock;
    sdr->f_if=f_if;
    sdr->ti=1/f_sf;

     
    if (!(sdr->code=gencode(prn,ctype,&sdr->clen,&sdr->crate))) {
        SDRPRINTF("error: gencode\n"); return -1;
    }
    sdr->ci=sdr->ti*sdr->crate;
    sdr->ctime=sdr->clen/sdr->crate;
    sdr->nsamp=(int)(f_sf*sdr->ctime);
    sdr->nsampchip=(int)(sdr->nsamp/sdr->clen);
    satno2id(sdr->sat,sdr->satstr);

     
    if (sdrini.fend==FEND_FRTLSDR) {
        sdr->foffset=f_cf*sdrini.rtlsdrppmerr*1e-6;
        sdr->f_cf=f_cf;  
    } else {
        sdr->f_cf=f_cf;  
        sdr->foffset=0.0;  
    }

     
    initacqstruct(sys,ctype,prn,&sdr->acq);
    sdr->acq.nfft=2*sdr->nsamp; 

     
    if (!(sdr->acq.freq=(double*)malloc(sizeof(double)*sdr->acq.nfreq))) {
        SDRPRINTF("error: initsdrch memory alocation\n"); return -1;
    }

     
    for (i=0;i<sdr->acq.nfreq;i++)
        sdr->acq.freq[i]=sdr->f_if+((i-(sdr->acq.nfreq-1)/2)*sdr->acq.step)
                            +sdr->foffset;

     
    if (inittrkstruct(sdr->sat,ctype,sdr->ctime,&sdr->trk)<0) return -1;

     
    if (initnavstruct(sys,ctype,prn,&sdr->nav)<0) {
        return -1;
    }
     
    if (!(rcode=(short *)sdrmalloc(sizeof(short)*sdr->acq.nfft)) ||
        !(sdr->xcode=cpxmalloc(sdr->acq.nfft))) {
            SDRPRINTF("error: initsdrch memory alocation\n"); return -1;
    }
     
    for (i=0;i<sdr->acq.nfft;i++) rcode[i]=0;  
    rescode(sdr->code,sdr->clen,0,0,sdr->ci,sdr->nsamp,rcode);  
    cpxcpx(rcode,NULL,1.0,sdr->acq.nfft,sdr->xcode);  
    cpxfft(NULL,sdr->xcode,sdr->acq.nfft);

    sdrfree(rcode);
    return 0;
}

 
 
 
 
 
extern void freesdrch(sdrch_t *sdr)
{
    free(sdr->code);
    cpxfree(sdr->xcode);
    free(sdr->nav.fbits);
    free(sdr->nav.fbitsdec);
    free(sdr->nav.bitsync);
    free(sdr->trk.II);
    free(sdr->trk.QQ);
    free(sdr->trk.oldI);
    free(sdr->trk.oldQ);
    free(sdr->trk.sumI);
    free(sdr->trk.sumQ);
    free(sdr->trk.oldsumI);
    free(sdr->trk.oldsumQ);
    free(sdr->trk.corrp);
    free(sdr->acq.freq);

    if (sdr->nav.fec!=NULL)
        delete_viterbi27_port(sdr->nav.fec);

    if (sdr->nav.ocode!=NULL)
        free(sdr->nav.ocode);
}
