#include "sdr.h"

extern void sdrnavigation(sdrch_t *sdr, uint64_t buffloc, uint64_t cnt) {
    int sfn;

    sdr->nav.biti = cnt % sdr->nav.rate;
    sdr->nav.ocodei = (sdr->nav.biti - sdr->nav.synci - 1);
    if (sdr->nav.ocodei < 0)
        sdr->nav.ocodei += sdr->nav.rate;

    if (sdr->nav.rate == 1 && cnt > 2000 / (sdr->ctime * 1000)) {
        sdr->nav.synci = 0;
        sdr->nav.flagsync = ON;
    }

    if (!sdr->nav.flagsync && cnt > 2000 / (sdr->ctime * 1000))
        sdr->nav.flagsync =
            checksync(sdr->trk.II[0], sdr->trk.oldI[0], &sdr->nav);

    if (sdr->nav.flagsync) {

        if (checkbit(sdr->trk.II[0], sdr->trk.loopms, &sdr->nav) == OFF) {
        }

        if (sdr->nav.swsync) {

            if (!sdr->nav.flagtow)
                predecodefec(&sdr->nav);

            if (!sdr->nav.flagtow)
                sdr->nav.flagsyncf = findpreamble(&sdr->nav);

            if (sdr->nav.flagsyncf && !sdr->nav.flagtow) {
                sdr->nav.firstsf = buffloc;
                sdr->nav.firstsfcnt = cnt;
                sdr->nav.flagtow = ON;
            }
        }

        if (sdr->nav.flagtow && sdr->nav.swsync) {

            if ((int)(cnt - sdr->nav.firstsfcnt) % sdr->nav.update == 0) {
                predecodefec(&sdr->nav);
                sfn = decodenav(&sdr->nav);
                
                if (!sfn) {
                    ;
                }

                if (sdr->nav.sdreph.tow_gpst == 0 && sdr->nav.ctype != CTYPE_G1) {
                    /* reset if tow does not decoded (skip for GLONASS - needs 5 strings) */
                    sdr->nav.flagsyncf = OFF;
                    sdr->nav.flagtow = OFF;
                } else if (cnt - sdr->nav.firstsfcnt == 0 || 
                          (sdr->nav.ctype == CTYPE_G1 && sdr->nav.sdreph.eph.week != 0 && !sdr->nav.flagdec)) {
                    /* Set flagdec: for GPS/Galileo on first frame, for GLONASS when ephemeris complete */
                    sdr->nav.flagdec = ON;
                    sdr->nav.sdreph.eph.sat = sdr->sat;
                    sdr->nav.firstsftow = sdr->nav.sdreph.tow_gpst;
                }
            }
        }
    }
}

extern uint32_t getbitu2(const uint8_t *buff, int p1, int l1, int p2, int l2) {
    return (getbitu(buff, p1, l1) << l2) + getbitu(buff, p2, l2);
}
extern int32_t getbits2(const uint8_t *buff, int p1, int l1, int p2, int l2) {
    if (getbitu(buff, p1, 1))
        return (int32_t)((getbits(buff, p1, l1) << l2) + getbitu(buff, p2, l2));
    else
        return (int32_t)getbitu2(buff, p1, l1, p2, l2);
}

extern uint32_t getbitu3(const uint8_t *buff, int p1, int l1, int p2, int l2,
                         int p3, int l3) {
    return (getbitu(buff, p1, l1) << (l2 + l3)) +
           (getbitu(buff, p2, l2) << l3) + getbitu(buff, p3, l3);
}
extern int32_t getbits3(const uint8_t *buff, int p1, int l1, int p2, int l2,
                        int p3, int l3) {
    if (getbitu(buff, p1, 1))
        return (int32_t)((getbits(buff, p1, l1) << (l2 + l3)) +
                         (getbitu(buff, p2, l2) << l3) + getbitu(buff, p3, l3));
    else
        return (int32_t)getbitu3(buff, p1, l1, p2, l2, p3, l3);
}

extern uint32_t merge_two_u(const uint32_t a, const uint32_t b, int n) {
    return (a << n) + b;
}
extern int32_t merge_two_s(const int32_t a, const uint32_t b, int n) {
    return (int32_t)((a << n) + b);
}

extern void bits2byte(int *bits, int nbits, int nbin, int right, uint8_t *bin) {
    int i, j, rem, bitscpy[MAXBITS] = {0};
    unsigned char b;
    rem = 8 * nbin - nbits;

    memcpy(&bitscpy[right ? rem : 0], bits, sizeof(int) * nbits);

    for (i = 0; i < nbin; i++) {
        b = 0;
        for (j = 0; j < 8; j++) {
            b <<= 1;
            if (bitscpy[i * 8 + j] < 0)
                b |= 0x01;
        }
        bin[i] = b;
    }
}

extern void interleave(const int *in, int row, int col, int *out) {
    int r, c;
    int tmp[MAXBITS];
    memcpy(tmp, in, sizeof(int) * row * col);
    for (r = 0; r < row; r++) {
        for (c = 0; c < col; c++) {
            out[r * col + c] = tmp[c * row + r];
        }
    }
}

extern int checksync(double IP, double IPold, sdrnav_t *nav) {
    int maxi;

    if (IPold * IP < 0) {
        nav->bitsync[nav->biti] += 1;

        maxi = maxvi(nav->bitsync, nav->rate, -1, -1, &nav->synci);

        if (maxi > NAVSYNCTH) {

            nav->synci--;
            if (nav->synci < 0)
                nav->synci = nav->rate - 1;
            return 1;
        }
    }

    return 0;
}

extern int checkbit(double IP, int loopms, sdrnav_t *nav) {
    int diffi = nav->biti - nav->synci, syncflag = ON, polarity = 1;

    nav->swreset = OFF;
    nav->swsync = OFF;

    /* if synchronization is started */
    if (diffi == 1 || diffi == -nav->rate + 1) {
        nav->bitIP = IP; /* reset */
        nav->swreset = ON;
        nav->cnt = 1;
    }
    /* after synchronization */
    else {
        nav->bitIP += IP; /* cumsum */
        if (nav->bitIP * IP < 0)
            syncflag = OFF;
    }

    if (nav->cnt % loopms == 0)
        nav->swloop = ON;
    else
        nav->swloop = OFF;

    if (nav->ctype == CTYPE_E1B) {
        nav->bitIP = IP;
        diffi = 0;
        nav->swloop = ON;
    }

    if (diffi == 0) {
        if (nav->flagpol) {
            polarity = -1;
        } else {
            polarity = 1;
        }
        nav->bit = (nav->bitIP < 0) ? -polarity : polarity;

        shiftdata(&nav->fbits[0], &nav->fbits[1], sizeof(int),
                  nav->flen + nav->addflen - 1);
        nav->fbits[nav->flen + nav->addflen - 1] = nav->bit;
        nav->swsync = ON;
    }
    nav->cnt++;

    return syncflag;
}

extern void predecodefec(sdrnav_t *nav) {
    int i, j;
    unsigned char enc[NAVFLEN_SBAS + NAVADDFLEN_SBAS];
    unsigned char dec[94];
    int dec2[NAVFLEN_SBAS / 2];

    if (nav->ctype == CTYPE_L1CA) {

        memcpy(nav->fbitsdec, nav->fbits,
               sizeof(int) * (nav->flen + nav->addflen));
    }

    if (nav->ctype == CTYPE_G1) {
        /* FEC is not used before preamble detection */
        memcpy(nav->fbitsdec, nav->fbits,
               sizeof(int) * (nav->flen + nav->addflen));
    }

    if (nav->ctype == CTYPE_E1B) {
        /* FEC is not used before preamble detection */
        memcpy(nav->fbitsdec, nav->fbits,
               sizeof(int) * (nav->flen + nav->addflen));
    }

    if (nav->ctype == CTYPE_L1SBAS) {

        init_viterbi27_port(nav->fec, 0);
        for (i = 0; i < NAVFLEN_SBAS + NAVADDFLEN_SBAS; i++)
            enc[i] = (nav->fbits[i] == 1) ? 0 : 255;
        update_viterbi27_blk_port(nav->fec, enc,
                                  (nav->flen + nav->addflen) / 2);
        chainback_viterbi27_port(nav->fec, dec, nav->flen / 2, 0);
        for (i = 0; i < 94; i++) {
            for (j = 0; j < 8; j++) {
                dec2[8 * i + j] = ((dec[i] << j) & 0x80) >> 7;
                nav->fbitsdec[8 * i + j] = (dec2[8 * i + j] == 0) ? 1 : -1;
                if (8 * i + j == NAVFLEN_SBAS / 2 - 1) {
                    break;
                }
            }
        }
    }
}

extern int paritycheck(sdrnav_t *nav) {
    int i, j, stat = 0, crc, bits[MAXBITS];
    unsigned char bin[29] = {0}, pbin[3];

    for (i = 0; i < nav->flen + nav->addflen; i++)
        bits[i] = nav->polarity * nav->fbitsdec[i];

    if (nav->ctype == CTYPE_L1CA) {

        for (i = 0; i < 10; i++) {

            if (bits[i * 30 + 1] == -1) {
                for (j = 2; j < 26; j++)
                    bits[i * 30 + j] *= -1;
            }
            stat += paritycheck_l1ca(&bits[i * 30]);
        }

        if (stat == 10) {
            return 1;
        }
    }

    if (nav->ctype == CTYPE_L1SBAS) {
        bits2byte(&bits[0], 226, 29, 1, bin);
        bits2byte(&bits[226], 24, 3, 0, pbin);

        crc = crc24q(bin, 29);
        if (crc == getbitu(pbin, 0, 24)) {
            return 1;
        }
    }

    if (nav->ctype == CTYPE_E1B) {
        /* parity check is done in decode_e1b */
        return 1;
    }

    if (nav->ctype == CTYPE_G1) {
        /* parity check is done in decode_g1 */
        return 1;
    }

    return 0;
}

extern int findpreamble(sdrnav_t *nav) {
    int i, corr = 0;

    if (nav->ctype == CTYPE_L1CA) {
        for (i = 0; i < nav->prelen; i++)
            corr += (nav->fbitsdec[nav->addflen + i] * nav->prebits[i]);
    }

    if (nav->ctype == CTYPE_L1SBAS) {
        for (i = 0; i < nav->prelen / 2; i++) {
            corr += (nav->fbitsdec[i] * nav->prebits[0 + i]);
            corr += (nav->fbitsdec[i + 250] * nav->prebits[8 + i]);
        }
    }

    if (nav->ctype == CTYPE_E1B) {
        for (i = 0; i < nav->prelen; i++)
            corr += (nav->fbitsdec[i] * nav->prebits[i]);
        for (i = 0; i < nav->prelen; i++)
            corr += (nav->fbitsdec[i + 250] * nav->prebits[i]);
        corr = (int)(corr / 2);
    }

    if (nav->ctype == CTYPE_G1) {
        /* time mark is last in word */
        for (i = 0; i < nav->prelen; i++)
            corr += (nav->fbitsdec[nav->flen - nav->prelen + i] * nav->prebits[i]);
    }

    int threshold = nav->prelen;
    
    if (abs(corr) >= threshold) {
        nav->polarity = corr > 0 ? 1 : -1;
        if (paritycheck(nav)) {
            return 1;
        } else {
            if (nav->ctype == CTYPE_L1SBAS) {
                if (nav->polarity == 1)
                    nav->flagpol = ON;
            }
        }
    }

    return 0;
}

extern int decodenav(sdrnav_t *nav) {
    switch (nav->ctype) {

    case CTYPE_L1CA:
        return decode_l1ca(nav);

    case CTYPE_L1SBAS:
        return decode_l1sbas(nav);

    case CTYPE_E1B:
        return decode_e1b(nav);

    case CTYPE_G1:
        return decode_g1(nav);

    default:
        return -1;
    }
}
