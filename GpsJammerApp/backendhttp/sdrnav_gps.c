#include "sdr.h"

 
void decode_subfrm1(const uint8_t *buff, sdreph_t *eph)
{
    double toc;
    int week;

    eph->tow_gpst  =getbitu( buff, 30,17)*6.0;
    week           =getbitu( buff, 60,10)+1024;
    eph->eph.code  =getbitu( buff, 70, 2);
    eph->eph.sva   =getbitu( buff, 72, 4);
    eph->eph.svh   =getbitu( buff, 76, 6);
    eph->eph.iodc  =getbitu2(buff, 82, 2,210, 8);
    eph->eph.flag  =getbitu( buff, 90, 1);
    eph->eph.tgd[0]=getbits( buff,196, 8)*P2_31;
    toc            =getbitu( buff,218,16)*16.0;
    eph->eph.f2    =getbits( buff,240, 8)*P2_55;
    eph->eph.f1    =getbits( buff,248,16)*P2_43;
    eph->eph.f0    =getbits( buff,270,22)*P2_31;

    eph->eph.week=adjgpsweek(week);
    eph->week_gpst=eph->eph.week;
    eph->eph.ttr=gpst2time(eph->eph.week,eph->tow_gpst);
    eph->eph.toc=gpst2time(eph->eph.week,toc);

     
    eph->cnt++;
}
 
void decode_subfrm2(const uint8_t *buff, sdreph_t *eph)
{
    double sqrtA;
    int oldiode=eph->eph.iode;

    eph->tow_gpst=getbitu( buff, 30,17)*6.0;
    eph->eph.iode=getbitu( buff, 60, 8);
    eph->eph.crs =getbits( buff, 68,16)*P2_5;
    eph->eph.deln=getbits( buff, 90,16)*P2_43*SC2RAD;
    eph->eph.M0  =getbits2(buff,106, 8,120,24)*P2_31*SC2RAD;
    eph->eph.cuc =getbits( buff,150,16)*P2_29;
    eph->eph.e   =getbitu2(buff,166, 8,180,24)*P2_33;
    eph->eph.cus =getbits( buff,210,16)*P2_29;
    sqrtA        =getbitu2(buff,226, 8,240,24)*P2_19;
    eph->eph.toes=getbitu( buff,270,16)*16.0;
    eph->eph.fit =getbitu( buff,286, 1);
    eph->eph.A   =sqrtA*sqrtA;

     
    if (oldiode-eph->eph.iode!=0) eph->update=ON; 
    
     
    eph->cnt++;
}
 
void decode_subfrm3(const uint8_t *buff, sdreph_t *eph)
{
    int oldiode=eph->eph.iode;

    eph->tow_gpst=getbitu( buff, 30,17)*6.0;
    eph->eph.cic =getbits( buff, 60,16)*P2_29;
    eph->eph.OMG0=getbits2(buff, 76, 8, 90,24)*P2_31*SC2RAD;
    eph->eph.cis =getbits( buff,120,16)*P2_29;
    eph->eph.i0  =getbits2(buff,136, 8,150,24)*P2_31*SC2RAD;
    eph->eph.crc =getbits( buff,180,16)*P2_5;
    eph->eph.omg =getbits2(buff,196, 8,210,24)*P2_31*SC2RAD;
    eph->eph.OMGd=getbits( buff,240,24)*P2_43*SC2RAD;
    eph->eph.iode=getbitu( buff,270, 8);
    eph->eph.idot=getbits( buff,278,14)*P2_43*SC2RAD;

     
    if (oldiode-eph->eph.iode!=0) eph->update=ON; 

     
    eph->cnt++;
}
 
void decode_subfrm4(const uint8_t *buff, sdreph_t *eph)
{
    eph->tow_gpst=getbitu(buff,30,17)*6.0;  
}
 
void decode_subfrm5(const uint8_t *buff, sdreph_t *eph)
{
    eph->tow_gpst=getbitu(buff,30,17)*6.0;  
}
 
int decode_frame_l1ca(const uint8_t *buff, sdreph_t *eph)
{
    int id=getbitu(buff,49,3);  

    switch (id) {
    case 1: decode_subfrm1(buff,eph); break;
    case 2: decode_subfrm2(buff,eph); break;
    case 3: decode_subfrm3(buff,eph); break;
    case 4: decode_subfrm4(buff,eph); break;
    case 5: decode_subfrm5(buff,eph); break;
    }
    return id;
}
 
extern int paritycheck_l1ca(int *bits)
{
    int i,stat=0;
    int pbits[6];

     
    pbits[0]=bits[0]*bits[2]*bits[3]*bits[4]*bits[6]*bits[7 ]*bits[11]*bits[12]*
        bits[13]*bits[14]*bits[15]*bits[18]*bits[19]*bits[21]*bits[24];
    pbits[1]=bits[1]*bits[3]*bits[4]*bits[5]*bits[7]*bits[8 ]*bits[12]*bits[13]*
        bits[14]*bits[15]*bits[16]*bits[19]*bits[20]*bits[22]*bits[25];
    pbits[2]=bits[0]*bits[2]*bits[4]*bits[5]*bits[6]*bits[8 ]*bits[9 ]*bits[13]*
        bits[14]*bits[15]*bits[16]*bits[17]*bits[20]*bits[21]*bits[23];
    pbits[3]=bits[1]*bits[3]*bits[5]*bits[6]*bits[7]*bits[9 ]*bits[10]*bits[14]*
        bits[15]*bits[16]*bits[17]*bits[18]*bits[21]*bits[22]*bits[24];
    pbits[4]=bits[1]*bits[2]*bits[4]*bits[6]*bits[7]*bits[8 ]*bits[10]*bits[11]*
        bits[15]*bits[16]*bits[17]*bits[18]*bits[19]*bits[22]*bits[23]*bits[25];
    pbits[5]=bits[0]*bits[4]*bits[6]*bits[7]*bits[9]*bits[10]*bits[11]*bits[12]*
        bits[14]*bits[16]*bits[20]*bits[23]*bits[24]*bits[25];

    for (i=0;i<6;i++) stat+=(pbits[i]-bits[26+i]);
    if (stat==0) return 1;  

    return 0;
}
 
extern int decode_l1ca(sdrnav_t *nav)
{
    int i,j,id=0;
    uint8_t bin[38];

     
    for (i=0;i<10;i++) {
        if (nav->fbitsdec[i*30+1]==-1) {
            for (j=2;j<26;j++) 
                nav->fbitsdec[i*30+j]*=-1;
        }
    }
    bits2byte(&nav->fbitsdec[nav->addflen],nav->flen,38,0,bin);

     
    id=decode_frame_l1ca(bin,&nav->sdreph);
    if (id<1||id>5) {
     
    }
    return id;
}
