#include "sdr.h"

#define OEMSYNC1   0xAA         
#define OEMSYNC2   0x44         
#define OEMSYNC3   0x12         
#define OEMHLEN    28           
#define OEMSBASLEN 48           
#define ID_RAWSBASFRAME 973      

 
void setU2(uint8_t *p, uint16_t u)
{
    uint8_t pp[2];
    setbitu(pp,0,16,u);
    p[0]=pp[1]; p[1]=pp[0];
}
void setU4(uint8_t *p, uint32_t u)
{
    uint8_t pp[4];
    setbitu(pp,0,32,u);
    p[0]=pp[3]; p[1]=pp[2];
    p[2]=pp[1]; p[3]=pp[0];
}
 
void gen_novatel_sbasmsg(sdrsbas_t *sbas)
{
    int i;
    memset(sbas->novatelmsg,0,LENSBASNOV);

     
    sbas->novatelmsg[0]=OEMSYNC1;  
    sbas->novatelmsg[1]=OEMSYNC2;  
    sbas->novatelmsg[2]=OEMSYNC3;  
    setU2(&sbas->novatelmsg[4],ID_RAWSBASFRAME);  
    setU2(&sbas->novatelmsg[8],OEMSBASLEN);  
    setU2(&sbas->novatelmsg[14],sbas->week);  
    setU4(&sbas->novatelmsg[16],(int)(sbas->tow*1000));  

     
    setU4(&sbas->novatelmsg[OEMHLEN+4],183);  
    setU4(&sbas->novatelmsg[OEMHLEN+8],sbas->id);  
     
    for (i=0;i<29;i++) sbas->novatelmsg[OEMHLEN+12+i]=sbas->msg[i];

     
    setU4(&sbas->novatelmsg[OEMHLEN+48],crc32(sbas->novatelmsg,(OEMHLEN+48))); 
}
 
void decode_MT12(uint8_t *buff, sdrsbas_t *sbas)
{
    sbas->tow =getbitu(buff,107,20)+1.0;  
    sbas->week=getbitu(buff,127,10)+1024;  
}
 
void decode_msg_sbas(uint8_t *buff, sdrsbas_t *sbas)
{
     
    sbas->id=getbitu(buff,8,6);

     
    switch (sbas->id) {
    case 12:  
        decode_MT12(buff,sbas);
        break;
    default:
        sbas->tow+=1.0;
        break;
    }
}
 
extern int decode_l1sbas(sdrnav_t *nav)
{
    int i,crc,crcmsg,bits[250];
    uint8_t bin[29]={0},pbin[3];

     
    for (i=0;i<250;i++) bits[i]=nav->polarity*nav->fbitsdec[i];
    
    bits2byte(&bits[0],226,29,1,bin);   
    bits2byte(&bits[226],24,3,0,pbin);  

     
    crc=crc24q(bin,29);
    crcmsg=getbitu(pbin,0,24);
    if (crc==crcmsg) {
    } else {
        SDRPRINTF("error: parity mismatch crc=%d msg=%d\n",crc,crcmsg);
    }

     
    bits2byte(bits,250,32,0,nav->sbas.msg);
    decode_msg_sbas(nav->sbas.msg,&nav->sbas);

     
    if (sdrini.nch>1&&sdrch[sdrini.nch-2].nav.sdreph.week_gpst!=0) {
        nav->sbas.tow=sdrch[sdrini.nch-2].trk.tow[0];
        nav->sbas.week=sdrch[sdrini.nch-2].nav.sdreph.week_gpst;
    }

     
    if (nav->sbas.week!=0) {
        gen_novatel_sbasmsg(&nav->sbas);

         
         

        nav->sdreph.tow_gpst=nav->sbas.tow;
        nav->sdreph.week_gpst=nav->sbas.week;
    }

    return nav->sbas.id;
}
