 
 
 
 
 
 
#ifndef SDR_H
#define SDR_H

#define _CRT_SECURE_NO_WARNINGS
#define _GNU_SOURCE   

 
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdint.h>
#include <string.h>
#include <signal.h>
#include <time.h>
#include <stdarg.h>
#include <ctype.h>
#include <unistd.h>  

 
#if defined(SSE2_ENABLE)
  #include <emmintrin.h>
  #include <tmmintrin.h>
#endif

 
#if defined(AVX_ENABLE)||defined(AVX2_ENABLE)
  #include <immintrin.h>
#endif

 
#include <sys/socket.h>
#include <stdbool.h>
#include <inttypes.h>
#include <fec.h>
#include <fftw3.h>
#include "rtklib.h"
#include <libusb-1.0/libusb.h>
#include <pthread.h>
 

 

 
#ifdef RTLSDR
  #include "rtl-sdr.h"
#endif

#define SDRPRINTF printf

#ifdef __cplusplus
  extern "C" {
#endif

 
#define ROUND(x)      ((int)floor((x)+0.5))  
#define PI            3.1415926535897932  
#define DPI           (2.0*PI)          
#define D2R           (PI/180.0)        
#define R2D           (180.0/PI)        
#define CLIGHT        299792458.0       
#define ON            1                 
#define OFF           0                 
#define MAXBITS       3000              

 
#define GPS_PI                  3.1415926535897932
#define MU                      3.986005e14
#define OMEGAEDOT               7.2921151467e-5
#define CTIME				    2.99792458e8

 
#define FEND_RTLSDR   3                 
#define FEND_FRTLSDR  8                 
#define FEND_FILE     10                
#define FTYPE1        1                 
#define DTYPEI        1                 
#define DTYPEIQ       2                 

#define MEMBUFFLEN    5000              

#define FILE_BUFFSIZE 65536             

 
#define NFFTTHREAD    4                 
#define ACQINTG_L1CA  10                
#define ACQINTG_G1    10                
#define ACQINTG_E1B   4                 
#define ACQINTG_B1I   10                
#define ACQINTG_SBAS  10                
#define ACQHBAND      7000              
#define ACQSTEP       200               
#define ACQTH         3.0               
#define ACQSLEEP      2000              

 
#define LOOP_L1CA     10                
#define LOOP_G1       10                
#define LOOP_E1B      1                 
#define LOOP_B1I      10                
#define LOOP_B1IG     2                 
#define LOOP_SBAS     2                 
#define LOOP_LEX      4                 

 
#define NAVSYNCTH       50              

 
#define NAVRATE_L1CA    20              
#define NAVFLEN_L1CA    300             
#define NAVADDFLEN_L1CA 2               
#define NAVPRELEN_L1CA  8               
#define NAVEPHCNT_L1CA  3               

 
#define NAVRATE_SBAS    2               
#define NAVFLEN_SBAS    1500            
#define NAVADDFLEN_SBAS 12              
#define NAVPRELEN_SBAS  16              
#define NAVEPHCNT_SBAS  3               

 
#define PTIMING       68.802            
#define OBSINTERPN    80                
#define SNSMOOTHMS    100               

 
#define MAXGPSSATNO   210               
#define MAXGALSATNO   50                
#define MAXCMPSATNO   37                

 
#define CTYPE_L1CA    1                 
#define CTYPE_L1CP    2                 
#define CTYPE_L1CD    3                 
#define CTYPE_L1CO    4                 
#define CTYPE_L1SBAS  27                
#define CTYPE_NH10    28                
#define CTYPE_NH20    29                

 
#define LENSBASMSG    32                
#define LENSBASNOV    80                

 
 
#define LOW_PR        00e-3 * CTIME  
#define HIGH_PR       92e-3 * CTIME

 
#define SNR_RESET_THRES		15  	 
#define SNR_PVT_THRES 		19       

 
 
 
#define GPS_WEEK      2360

 
 

 
#define GPS_EPOCH_SECONDS 315964800

 
#define ET_TIMER  	60.0
#define SV_EL_PVT_MASK    15.0   
#define SV_EL_RESET_MASK  12.0   

 
#define MAX_MESSAGES 100   
#define MSG_LENGTH   128   
#define PUR1 1
#define PUR2 2

 
#define mlock_t       pthread_mutex_t
#define initmlock(f)  pthread_mutex_init(&f,NULL)
#define mlock(f)      pthread_mutex_lock(&f)
#define unmlock(f)    pthread_mutex_unlock(&f)
#define delmlock(f)   pthread_mutex_destroy(&f)
#define event_t       pthread_cond_t
#define initevent(f)  pthread_cond_init(&f,NULL)
#define setevent(f)   pthread_cond_signal(&f)
#define waitevent(f,m) pthread_cond_wait(&f,&m)
#define delevent(f)   pthread_cond_destroy(&f)
#define waitthread(f) pthread_join(f,NULL)
#define cratethread(f,func,arg) pthread_create(&f,NULL,func,arg)
#define THRETVAL      NULL

 
typedef fftwf_complex cpx_t;  

 
typedef struct {
        int fend;         
        int f_gain[2];  
        int f_bias[2];  
        int f_clock[2];  
        double f_cf[2];   
        double f_sf[2];   
        double f_if[2];   
        int dtype[2];     
        FILE *fp;        
        char file[1024];  
        int useif;       
        int nch;          
        int nchL1;        
        int nchL2;        
        int nchL5;        
        int nchL6;        
        int prn[MAXSAT];  
        int sys[MAXSAT];  
        int ctype[MAXSAT];  
        int ftype[MAXSAT];  
        int pltacq;       
        int plttrk;       
        int pltspec;      
        int outms;        
        int sbas;         
        int snrThreshold;  
        int xu0_v[3];      
        int sbasport;     
        int trkcorrn;     
        int trkcorrd;     
        int trkcorrp;     
        double trkdllb[2];  
        double trkpllb[2];  
        double trkfllb[2];  
        int rtlsdrppmerr;  
        int ekfFilterOn;   
} sdrini_t;

 
typedef struct {
        int stopflag;     
        int resetsyncthreadflag;    
        int specflag;     
        int buffsize;     
        int fendbuffsize;  
        unsigned char *buff;  
        unsigned char *tmpbuff;  
        uint64_t buffcnt;  
        int printflag;  
        double lat;
        double lon;
        double hgt;
        double gdop;
        int nsat;
        int nsatRaw;
        int nsatValid;
        int satList[MAXSAT];
        int obsValidList[MAXSAT];
        double obs_v[11*MAXSAT];  
        double vk1_v[MAXSAT];  
        double clkBias;
        double xyzdt[4];
        double elapsedTime;
        int azElCalculatedflag;
} sdrstat_t;

 
typedef struct {
        int prn;          
        int sys;          
        double tow;       
        int week;         
        double P;         
        double L;         
        double D;         
        double S;         
} sdrobs_t;

 
typedef struct {
        int intg;         
        double hband;     
        double step;      
        int nfreq;        
        double *freq;     
        int acqcodei;     
        int freqi;        
        double acqfreq;   
        int nfft;         
        double cn0;       
        double peakr;     
} sdracq_t;

 
typedef struct {
        double pllb;      
        double dllb;      
        double fllb;      
        double dllw2;     
        double dllaw;     
        double pllw2;     
        double pllaw;     
        double fllw;      
} sdrtrkprm_t;

 
typedef struct {
        double codefreq;  
        double carrfreq;  
        double remcode;   
        double remcarr;   
        double oldremcode;  
        double oldremcarr;  
        double codeNco;   
        double codeErr;   
        double carrNco;   
        double carrErr;   
        double freqErr;   
        uint64_t buffloc;  
        double tow[OBSINTERPN];  
        uint64_t codei[OBSINTERPN];  
        uint64_t codeisum[OBSINTERPN];  
        uint64_t cntout[OBSINTERPN];  
        double remcout[OBSINTERPN];  
        double L[OBSINTERPN]; 
        double D[OBSINTERPN]; 
        double S[OBSINTERPN]; 
        double *II;       
        double *QQ;       
        double *oldI;     
        double *oldQ;     
        double *sumI;     
        double *sumQ;     
        double *oldsumI;  
        double *oldsumQ;  
        double Isum;      
        int loop;         
        int loopms;       
        int flagpolarityadd;  
        int flagremcarradd;  
        int flagloopfilter;  
        int corrn;        
        int *corrp;       
        double *corrx;    
        int ne,nl;        
        sdrtrkprm_t prm1;  
        sdrtrkprm_t prm2;  
} sdrtrk_t;

 
typedef struct {
        eph_t eph;        
         
        int ctype;        
        double tow_gpst;  
        int week_gpst;    
        int cnt;          
        int cntth;        
        int update;       
        int prn;          
        int tk[3],nt,n4,s1cnt;  
        double toc_gst;   
        int week_gst;
} sdreph_t;

 
typedef struct {
        unsigned char msg[LENSBASMSG];  
        unsigned char novatelmsg[LENSBASNOV];  
        int id;           
        int week;         
        double tow;       
} sdrsbas_t;

 
typedef struct {
        FILE *fpnav;      
        int ctype;        
        int rate;         
        int flen;         
        int addflen;      
        int prebits[32];  
        int prelen;       
        int bit;          
        int biti;         
        int cnt;          
        double bitIP;     
        int *fbits;       
        int *fbitsdec;    
        int update;       
        int *bitsync;     
        int synci;        
        uint64_t firstsf;  
        uint64_t firstsfcnt;  
        double firstsftow;  
        int polarity;     
        int flagpol;      
        void *fec;        
        short *ocode;     
        int ocodei;       
        int swsync;       
        int swreset;      
        int swloop;       
        int flagsync;     
        int flagsyncf;    
        int flagtow;      
        int flagdec;      
        sdreph_t sdreph;  
        sdrsbas_t sbas;   
} sdrnav_t;

 
typedef struct {
        thread_t hsdr;    
        int no;           
        int sat;          
        int sys;          
        int prn;          
        char satstr[5];   
        int ctype;        
        int dtype;        
        int ftype;        
        double f_cf;      
        double f_sf;      
        double f_if;      
        int f_gain;   
        int f_bias;   
        int f_clock;  
        double foffset;   
        short *code;      
        cpx_t *xcode;     
        int clen;         
        double crate;     
        double ctime;     
        double ti;        
        double ci;        
        int nsamp;        
        int currnsamp;    
        int nsampchip;    
        sdracq_t acq;     
        sdrtrk_t trk;     
        sdrnav_t nav;     
        int flagacq;      
        int flagtrk;      
        double elapsed_time_snr;
        double elapsed_time_nav;
} sdrch_t;

 
typedef struct {
  double rk1_v[MAXSAT];
  double varR;
} sdrekf_t;

 
typedef struct {
  int message_count;
  char *messages[100];
} sdrgui_t;

 
extern thread_t hmainthread;   
extern thread_t hsyncthread;   
extern thread_t hdatathread;    
extern thread_t hmsgthread;    

extern mlock_t hbuffmtx;       
extern mlock_t hreadmtx;       
extern mlock_t hfftmtx;        
extern mlock_t hobsmtx;        
extern mlock_t hresetmtx;      
extern mlock_t hobsvecmtx;     
extern mlock_t hmsgmtx;        

extern sdrini_t sdrini;        
extern sdrstat_t sdrstat;      
extern sdrch_t sdrch[MAXSAT];  
extern sdrekf_t sdrekf;        
extern sdrgui_t sdrgui;        

 
extern void startsdr(void);
extern void quitsdr(sdrini_t *ini, int stop);
extern void *sdrthread(void *arg);
extern void *datathread(void *arg);
extern int resetStructs(void *arg);
extern int checkObsDelay(int prn);

 
extern void *syncthread(void * arg);

 
extern uint64_t sdraqcuisition(sdrch_t *sdr, double *power);
extern int checkacquisition(double *P, sdrch_t *sdr);

 
extern uint64_t sdrtracking(sdrch_t *sdr, uint64_t buffloc, uint64_t cnt);
extern void cumsumcorr(sdrtrk_t *trk, int polarity);
extern void clearcumsumcorr(sdrtrk_t *trk);
extern void pll(sdrch_t *sdr, sdrtrkprm_t *prm, double dt);
extern void dll(sdrch_t *sdr, sdrtrkprm_t *prm, double dt);
extern void setobsdata(sdrch_t *sdr, uint64_t buffloc, uint64_t cnt,
                       sdrtrk_t *trk, int flag);

 
extern int loadinit(sdrini_t *ini, const char *filename);
extern int chk_initvalue(sdrini_t *ini);
extern void openhandles(void);
extern void closehandles(void);
extern void initacqstruct(int sys, int ctype, int prn, sdracq_t *acq);
extern void inittrkprmstruct(sdrtrk_t *trk);
extern int inittrkstruct(int sat, int ctype, double ctime, sdrtrk_t *trk);
extern int initnavstruct(int sys, int ctype, int prn, sdrnav_t *nav);
extern int initsdrch(int chno, int sys, int prn, int ctype, int dtype,
                     int ftype, int f_gain, int f_bias, int f_clock,
                     double f_cf, double f_sf, double f_if,
                     sdrch_t *sdr);
extern void freesdrch(sdrch_t *sdr);

 
extern int getfullpath(char *relpath, char *abspath);
extern unsigned long tickgetus(void);
extern void sleepus(int usec);
extern void settimeout(struct timespec *timeout, int waitms);
extern double log2(double n);
extern int calcfftnum(double x, int next);
extern void *sdrmalloc(size_t size);
extern void sdrfree(void *p);
extern cpx_t *cpxmalloc(int n);
extern void cpxfree(cpx_t *cpx);
extern void cpxfft(fftwf_plan plan, cpx_t *cpx, int n);
extern void cpxifft(fftwf_plan plan, cpx_t *cpx, int n);
extern void cpxcpx(const short *II, const short *QQ, double scale, int n,
                   cpx_t *cpx);
extern void cpxcpxf(const float *II, const float *QQ, double scale,  int n,
                    cpx_t *cpx);
extern void cpxconv(fftwf_plan plan, fftwf_plan iplan, cpx_t *cpxa, cpx_t *cpxb,
                    int m, int n, int flagsum, double *conv);
extern void cpxpspec(fftwf_plan plan, cpx_t *cpx, int n, int flagsum,
                     double *pspec);
extern void dot_21(const short *a1, const short *a2, const short *b, int n,
                   double *d1, double *d2);
extern void dot_22(const short *a1, const short *a2, const short *b1,
                   const short *b2, int n, double *d1, double *d2);
extern void dot_23(const short *a1, const short *a2, const short *b1,
                   const short *b2, const short *b3, int n, double *d1,
                   double *d2);
extern double mixcarr(const char *data, int dtype, double ti, int n,
                      double freq, double phi0, short *II, short *QQ);
extern void mulvcs(const char *data1, const short *data2, int n, short *out);
extern void sumvf(const float *data1, const float *data2, int n, float *out);
extern void sumvd(const double *data1, const double *data2, int n, double *out);
extern int maxvi(const int *data, int n, int exinds, int exinde, int *ind);
extern float maxvf(const float *data, int n, int exinds, int exinde, int *ind);
extern double maxvd(const double *data, int n, int exinds, int exinde,int *ind);
extern double meanvd(const double *data, int n, int exinds, int exinde);
extern double interp1(double *x, double *y, int n, double t);
extern void uint64todouble(uint64_t *data, uint64_t base, int n, double *out);
extern void ind2sub(int ind, int nx, int ny, int *subx, int *suby);
extern void shiftdata(void *dst, void *src, size_t size, int n);
extern double rescode(const short *code, int len, double coff, int smax,
                      double ci, int n, short *rcode);
extern void pcorrelator(const char *data, int dtype, double ti, int n,
                        double *freq, int nfreq, double crate, int m,
                        cpx_t* codex, double *P);
extern void correlator(const char *data, int dtype, double ti, int n,
                       double freq, double phi0, double crate, double coff,
                       int* s, int ns, double *II, double *QQ, double *remc,
                       double *remp, short* codein, int coden);
extern int leap_seconds(long gps_seconds);
extern time_t gps_to_utc(int gps_week, double gps_tow);

 
extern short *gencode(int prn, int ctype, int *len, double *crate);

 
extern int pvtProcessor(void);
extern int blsFilter(double *xs_v, double *pr_v, int numSat,
                 double xyzdt_v[], double *gdop);
extern void ecef2lla(double x, double y, double z,
                    double *latitude, double *longitude, double *height);
extern void check_t(double time, double *corrTime);
extern int satPos(sdreph_t *sdreph, double transmitTime, double svPos[3],
            double *svClkCorr);
extern void rot(double R[9], double angle, int axis);
extern void precheckObs();
extern int tropo(double sinel, double hsta, double p, double tkel,
                 double hum, double hp, double htkel, double hhum,
                 double *ddr);
extern int togeod(double a, double finv, double X, double Y, double Z,
                  double *dphi, double *dlambda, double *h);
extern int topocent(double X[], double dx[], double *Az, double *El, double *D);
extern int updateObsList(void);

 

 
extern void sdrnavigation(sdrch_t *sdr, uint64_t buffloc, uint64_t cnt);
extern uint32_t getbitu2(const uint8_t *buff, int p1, int l1, int p2, int l2);
extern int32_t getbits2(const uint8_t *buff, int p1, int l1, int p2, int l2);
extern uint32_t getbitu3(const uint8_t *buff, int p1, int l1, int p2, int l2,
                         int p3, int l3);
extern int32_t getbits3(const uint8_t *buff, int p1, int l1, int p2, int l2,
                        int p3, int l3);
extern uint32_t merge_two_u(const uint32_t a, const uint32_t b, int n);
extern int32_t merge_two_s(const int32_t a, const uint32_t b, int n);
extern void bits2byte(int *bits, int nbits, int nbin, int right, uint8_t *bin);
extern void interleave(const int *in, int row, int col, int *out);
extern int checksync(double IP, double IPold, sdrnav_t *nav);
extern int checkbit(double IP, int loopms, sdrnav_t *nav);
extern void predecodefec(sdrnav_t *nav);
extern int paritycheck(sdrnav_t *nav);
extern int findpreamble(sdrnav_t *nav);
extern int decodenav(sdrnav_t *nav);
extern void check_hamming(int *hamming, int n, int parity, int m);

 
extern int decode_l1ca(sdrnav_t *nav);
extern int decode_e1b(sdrnav_t *nav);
extern int decode_g1(sdrnav_t *nav);
extern int decode_b1i(sdrnav_t *nav);
extern int decode_l1sbas(sdrnav_t *nav);
extern int paritycheck_l1ca(int *bits);

 
extern int rcvinit(sdrini_t *ini);
extern int rcvquit(sdrini_t *ini);
extern int rcvgrabstart(sdrini_t *ini);
extern int rcvgrabdata(sdrini_t *ini);
extern int rcvgetbuff(sdrini_t *ini, uint64_t buffloc, int n, int ftype,
                      int dtype, char *expbuf);
extern void file_pushtomembuf(void);
extern void file_getbuff(uint64_t buffloc, int n, int ftype, int dtype,
                         char *expbuf);

 
 
 

 
extern void add_message(const char *msg);
extern void updateNavStatusWin(int counter);

#ifdef __cplusplus
}
#endif
#endif  
