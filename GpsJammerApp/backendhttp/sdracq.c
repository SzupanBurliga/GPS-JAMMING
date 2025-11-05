#include "sdr.h"

 
extern uint64_t sdraqcuisition(sdrch_t *sdr, double *power)
{
    int i;
    char *data;
    uint64_t buffloc;

     
    data=(char*)sdrmalloc(sizeof(char)*2*sdr->nsamp*sdr->dtype);

     
    mlock(hreadmtx);
    buffloc=(sdrstat.fendbuffsize*sdrstat.buffcnt)-(sdr->acq.intg+1)*sdr->nsamp;
    unmlock(hreadmtx);

     
    for (i=0;i<sdr->acq.intg;i++) {
         
        rcvgetbuff(&sdrini,buffloc,2*sdr->nsamp,sdr->ftype,sdr->dtype,data);
        buffloc+=sdr->nsamp;

         

         
        pcorrelator(data,sdr->dtype,sdr->ti,sdr->nsamp,sdr->acq.freq,
            sdr->acq.nfreq,sdr->crate,sdr->acq.nfft,sdr->xcode,power);

         
        if (checkacquisition(power,sdr)) {
            sdr->flagacq=ON;
            break;
        }
    }

     
     

     
    if (sdr->flagacq) {
         
        buffloc+=-(i+1)*sdr->nsamp+sdr->acq.acqcodei;
        sdr->trk.carrfreq=sdr->acq.acqfreq;
        sdr->trk.codefreq=sdr->crate;
    }
    else {
        sleepms(ACQSLEEP);
    }
    sdrfree(data);
    return buffloc;
}
 
extern int checkacquisition(double *P, sdrch_t *sdr)
{
    int maxi,codei,freqi,exinds,exinde;
    double maxP,maxP2,meanP;

    maxP=maxvd(P,sdr->nsamp*sdr->acq.nfreq,-1,-1,&maxi);
    ind2sub(maxi,sdr->nsamp,sdr->acq.nfreq,&codei,&freqi);

     
     
    exinds=codei-2*sdr->nsampchip; if(exinds<0) exinds+=sdr->nsamp;
    exinde=codei+2*sdr->nsampchip; if(exinde>=sdr->nsamp) exinde-=sdr->nsamp;
    meanP=meanvd(&P[freqi*sdr->nsamp],sdr->nsamp,exinds,exinde);  
    sdr->acq.cn0=10*log10(maxP/meanP/sdr->ctime);

     
    maxP2=maxvd(&P[freqi*sdr->nsamp],sdr->nsamp,exinds,exinde,&maxi);

    sdr->acq.peakr=maxP/maxP2;
    sdr->acq.acqcodei=codei;
    sdr->acq.freqi=freqi;
    sdr->acq.acqfreq=sdr->acq.freq[freqi];

    return sdr->acq.peakr>ACQTH;
}
