#include "sdr.h"

 
extern int rcvinit(sdrini_t *ini)
{
         
        fftwf_init_threads();

        sdrstat.buff=sdrstat.tmpbuff=NULL;

        switch (ini->fend) {

         

        #ifdef RTLSDR
         
        case FEND_RTLSDR:
                if (rtlsdr_init()<0) return -1;  

                 
                sdrstat.fendbuffsize=RTLSDR_DATABUFF_SIZE;  
                sdrstat.buffsize=2*RTLSDR_DATABUFF_SIZE*MEMBUFFLEN;  

                 
                sdrstat.buff=(uint8_t*)malloc(sdrstat.buffsize);
                if (NULL==sdrstat.buff) {
                        SDRPRINTF("error: failed to allocate memory for the buffer\n");
                        return -1;
                }
                break;

         
        case FEND_FRTLSDR:
                 
                if ((ini->fp = fopen(ini->file,"rb"))==NULL) {
                        SDRPRINTF("error: failed to open file : %s\n",ini->file);
                        return -1;
                }

                 
                sdrstat.fendbuffsize=RTLSDR_DATABUFF_SIZE;  
                sdrstat.buffsize=2*RTLSDR_DATABUFF_SIZE*MEMBUFFLEN;  

                 
                sdrstat.buff=(uint8_t*)malloc(sdrstat.buffsize);
                if (NULL==sdrstat.buff) {
                        SDRPRINTF("error: failed to allocate memory for the buffer\n");
                        return -1;
                }
                break;
        #endif

         
        case FEND_FILE:
                 
                if ((ini->fp = fopen(ini->file,"rb"))==NULL) {
                        SDRPRINTF("error: failed to open file: %s\n",ini->file);
                        return -1;
                }

                 
                sdrstat.fendbuffsize=FILE_BUFFSIZE;  
                sdrstat.buffsize=FILE_BUFFSIZE*MEMBUFFLEN;  

                 
                if (ini->fp!=NULL) {
                        sdrstat.buff=(uint8_t*)malloc(ini->dtype[0]*sdrstat.buffsize);
                        if (NULL==sdrstat.buff) {
                                SDRPRINTF("error: failed to allocate memory for the buffer\n");
                                return -1;
                        }
                }
                break;
        default:
                return -1;
        }
        return 0;
}

 
extern int rcvquit(sdrini_t *ini)
{
        switch (ini->fend) {

         

        #ifdef RTLSDR
         
        case FEND_RTLSDR:
                rtlsdr_quit();
                break;
        #endif

         
        case FEND_FRTLSDR:
        case FEND_FILE:
                if (ini->fp != NULL) {
                        fclose(ini->fp);
                        ini->fp = NULL;
                }
                break;
        default:
                return -1;
        }

         
        if (NULL!=sdrstat.buff) {
          free(sdrstat.buff);
          sdrstat.buff=NULL;
        }
                                if (NULL!=sdrstat.tmpbuff) {
                                        free(sdrstat.tmpbuff);
                                        sdrstat.tmpbuff=NULL;
                                }
        return 0;
}

 
extern int rcvgrabstart(sdrini_t *ini)
{
        switch (ini->fend) {

        default:
                return 0;
        }
        return 0;
}

 
extern int rcvgrabdata(sdrini_t *ini)
{
         

        switch (ini->fend) {

         

        #ifdef RTLSDR
         
        case FEND_RTLSDR:
                if (rtlsdr_start()<0) {
                        SDRPRINTF("error: rtlsdr...\n");
                        return -1;
                }
                break;

         
        case FEND_FRTLSDR:
                frtlsdr_pushtomembuf();  
                sleepms(5);
                break; 
        #endif
        case FEND_FILE:
                file_pushtomembuf();  
                sleepms(5);
                break;
        default:
                return -1;
        }
        return 0;
}

 
extern int rcvgetbuff(sdrini_t *ini, uint64_t buffloc, int n, int ftype,
                      int dtype, char *expbuf)
{
        switch (ini->fend) {

         

        #ifdef RTLSDR
         
        case FEND_RTLSDR:
                rtlsdr_getbuff(buffloc,n,expbuf);
                break;

         
        case FEND_FRTLSDR:
                rtlsdr_getbuff(buffloc,n,expbuf);
                break;
        #endif

         
        case FEND_FILE:
                file_getbuff(buffloc,n,ftype,dtype,expbuf);
                break;
        default:
                return -1;
        }
        return 0;
}

 
extern void file_pushtomembuf(void)
{
        size_t nread=0;

        mlock(hbuffmtx);
        if(sdrini.fp!=NULL) {
                nread=fread(&sdrstat.buff[(sdrstat.buffcnt%MEMBUFFLEN)*
                                           sdrini.dtype[0]*FILE_BUFFSIZE],1,sdrini.dtype[0]*FILE_BUFFSIZE,
                             sdrini.fp);
        }
        unmlock(hbuffmtx);

        if ((sdrini.fp!=NULL&&(int)nread<sdrini.dtype[0]*FILE_BUFFSIZE)) {
                sdrstat.stopflag=ON;
                SDRPRINTF("end of file!\n");
        }

        mlock(hreadmtx);
        sdrstat.buffcnt++;
        unmlock(hreadmtx);
}

 
extern void file_getbuff(uint64_t buffloc, int n, int ftype, int dtype,
                         char *expbuf)
{
        uint64_t membuffloc=dtype*buffloc%(MEMBUFFLEN*dtype*FILE_BUFFSIZE);
        int nout;

        n=dtype*n;
        nout=(int)((membuffloc+n)-(MEMBUFFLEN*dtype*FILE_BUFFSIZE));

        mlock(hbuffmtx);
         
        if (nout>0) {
                memcpy(expbuf,&sdrstat.buff[membuffloc],n-nout);
                memcpy(&expbuf[(n-nout)],&sdrstat.buff[0],nout);
        } else {
                memcpy(expbuf,&sdrstat.buff[membuffloc],n);
        }
        unmlock(hbuffmtx);
}
