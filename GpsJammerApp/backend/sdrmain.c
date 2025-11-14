#include "sdr.h"

thread_t hmainthread;
thread_t hsyncthread;
thread_t hdatathread;
thread_t hguithread;

mlock_t hbuffmtx;
mlock_t hreadmtx;
mlock_t hfftmtx;
mlock_t hobsmtx;
mlock_t hresetmtx;
mlock_t hobsvecmtx;
mlock_t hmsgmtx;

sdrini_t sdrini = {0};
sdrstat_t sdrstat = {0};
sdrch_t sdrch[MAXSAT] = {{0}};
sdrekf_t sdrekf = {0};
sdrgui_t sdrgui = {0};

int main(int argc, char **argv) {
    int sys_type = SYS_GPS;  /* default to GPS */
    char *input_file = NULL;
    int opt;

    if (argc < 2) {
        printf("Użycie: %s [-g|-a|-l] <plik_do_analizy>\n", argv[0]);
        printf("  -g    tryb GPS (domyślny)\n");
        printf("  -a    tryb Galileo\n");
        printf("  -l    tryb GLONASS\n");
        return 1;
    }

    while ((opt = getopt(argc, argv, "gal")) != -1) {
        switch (opt) {
        case 'g':
            sys_type = SYS_GPS;
            break;
        case 'a':
            sys_type = SYS_GAL;
            break;
        case 'l':
            sys_type = SYS_GLO;
            break;
        default:
            printf("Użycie: %s [-g|-a|-l] <plik_do_analizy>\n", argv[0]);
            return 1;
        }
    }

    if (optind >= argc) {
        printf("Błąd: brak nazwy pliku\n");
        printf("Użycie: %s [-g|-a|-l] <plik_do_analizy>\n", argv[0]);
        return 1;
    }

    input_file = argv[optind];

    if (loadinit(&sdrini, input_file, sys_type) < 0) {
        return -1;
    }

    int num_cpus;
    cpu_set_t cpu_set;
    num_cpus = sysconf(_SC_NPROCESSORS_ONLN);
    for (int n=0;n<(num_cpus-2);n++) {
      CPU_SET(n, &cpu_set);
    }
    if (sched_setaffinity(getpid(), sizeof(cpu_set_t), &cpu_set) == -1) {
      perror("error: sched_setaffinity\n");
    }

    startsdr();

    return 0;
}

extern void startsdr(void) {
    int i;
    SDRPRINTF("GNSS-SDRLIB start!\n");

    struct sched_param param1;
    struct sched_param param2;
    pthread_attr_t attr1;
    pthread_attr_t attr2;
    int ret;

    ret = pthread_attr_init(&attr1);
    if (ret) {
        printf("Init for thread attr1 failed: %s\n", strerror(ret));
    }
    ret = pthread_attr_init(&attr2);
    if (ret) {
        printf("Init for thread attr2 failed: %s\n", strerror(ret));
    }

    ret = pthread_attr_setstacksize(&attr1, PTHREAD_STACK_MIN);
    if (ret) {
        printf("Stack size for thread attr1 failed: %s\n", strerror(ret));
    }
    ret = pthread_attr_setstacksize(&attr2, PTHREAD_STACK_MIN);
    if (ret) {
        printf("Stack size for thread attr2 failed: %s\n", strerror(ret));
    }

    ret = pthread_attr_setschedpolicy(&attr1, SCHED_FIFO);
    if (ret) {
        printf("Policy for thread attr1 failed: %s\n", strerror(ret));
    }
    ret = pthread_attr_setschedpolicy(&attr2, SCHED_OTHER);
    if (ret) {
        printf("Policy for thread attr2 failed: %s\n", strerror(ret));
    }

    param1.sched_priority = 40;
    ret = pthread_attr_setschedparam(&attr1, &param1);
    if (ret) {
        printf("Priority for thread attr1 failed: %s\n", strerror(ret));
    }
    param2.sched_priority = 0;
    ret = pthread_attr_setschedparam(&attr2, &param2);
    if (ret) {
        printf("Priority for thread attr2 failed: %s\n", strerror(ret));
    }

    ret = pthread_attr_setinheritsched(&attr1, PTHREAD_EXPLICIT_SCHED);
    if (ret) {
        printf("Inherit for thread attr1 failed: %s\n", strerror(ret));
    }
    ret = pthread_attr_setinheritsched(&attr2, PTHREAD_EXPLICIT_SCHED);
    if (ret) {
        printf("Inherit for thread attr2 failed: %s\n", strerror(ret));
    }

    if (chk_initvalue(&sdrini) < 0) {
        SDRPRINTF("error: chk_initvalue\n");
        quitsdr(&sdrini, 1);
        return;
    }

    if (rcvinit(&sdrini) < 0) {
        SDRPRINTF("error: rcvinit\n");
        quitsdr(&sdrini, 1);
        return;
    }

    for (i = 0; i < sdrini.nch; i++) {
        if (initsdrch(i + 1, sdrini.sys[i], sdrini.prn[i], sdrini.ctype[i],
                      sdrini.dtype[sdrini.ftype[i] - 1], sdrini.ftype[i],
                      sdrini.f_gain[sdrini.ftype[i] - 1],
                      sdrini.f_bias[sdrini.ftype[i] - 1],
                      sdrini.f_clock[sdrini.ftype[i] - 1],
                      sdrini.f_cf[sdrini.ftype[i] - 1],
                      sdrini.f_sf[sdrini.ftype[i] - 1],
                      sdrini.f_if[sdrini.ftype[i] - 1], &sdrch[i]) < 0) {

            SDRPRINTF("error: initsdrch\n");
            quitsdr(&sdrini, 2);
            return;
        }
    }

    openhandles();

    ret = pthread_create(&hsyncthread, NULL, syncthread, NULL);
    if (ret) {
        printf("Create for sync thread failed: %s\n", strerror(ret));
    }

    for (i = 0; i < sdrini.nch; i++) {

        if (sdrch[i].ctype == CTYPE_L1CA || sdrch[i].ctype == CTYPE_L1SBAS ||
            sdrch[i].ctype == CTYPE_E1B || sdrch[i].ctype == CTYPE_G1) {

            ret = pthread_create(&sdrch[i].hsdr, NULL, sdrthread, &sdrch[i]);
            if (ret) {
                printf("Create for sdr thread failed: %s\n", strerror(ret));
            }
        }
    }

    ret = pthread_create(&hdatathread, NULL, datathread, NULL);
    if (ret) {
        printf("Create for data thread failed: %s\n", strerror(ret));
    }

    int counter = 0;

    struct timespec start_time, current_time;
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    sdrstat.elapsedTime = 0.0;

    while (!sdrstat.stopflag) {

        clock_gettime(CLOCK_MONOTONIC, &current_time);
        long seconds = current_time.tv_sec - start_time.tv_sec;
        long ns = current_time.tv_nsec - start_time.tv_nsec;
        sdrstat.elapsedTime = ((seconds * 1000) + (ns / 1e6)) / 1000.0;

        updateNavStatusWin(counter);

        counter++;

        usleep(100000);
    }

    for (int i = 0; i < sdrgui.message_count; i++) {
        free(sdrgui.messages[i]);
    }

    waitthread(hsyncthread);
    for (i = 0; i < sdrini.nch; i++) {
        waitthread(sdrch[i].hsdr);
    }
    waitthread(hdatathread);

    quitsdr(&sdrini, 0);

    SDRPRINTF("GNSS-SDRLIB is finished!\n");
}

extern void quitsdr(sdrini_t *ini, int stop) {
    int i;

    if (stop == 1)
        return;

    rcvquit(ini);
    if (stop == 2)
        return;

    for (i = 0; i < ini->nch; i++)
        freesdrch(&sdrch[i]);
    if (stop == 3)
        return;

    closehandles();
    if (stop == 4)
        return;
}

extern void *sdrthread(void *arg) {
    sdrch_t *sdr = (sdrch_t *)arg;
    uint64_t buffloc = 0, bufflocnow = 0, cnt = 0, loopcnt = 0;
    double *acqpower = NULL;
    double snr, el;
    int ret = 0;
    char bufferSDR[MSG_LENGTH];

    time_t current_time;
    time_t start_acq_timer;
    start_acq_timer = time(NULL);
    double elapsed_acq_time = 0;

    sleepms(sdr->no * 500);

    while (!sdrstat.stopflag) {

        current_time = time(NULL);
        if (sdr->flagacq) {
            elapsed_acq_time = current_time - start_acq_timer;
        }

        if (elapsed_acq_time > 60) {
            mlock(hobsmtx);
            snr = sdr->trk.S[0];
            unmlock(hobsmtx);

            if (snr < SNR_RESET_THRES) {

                snprintf(bufferSDR, sizeof(bufferSDR),
                         "%.3f  G%02d resetting with SNR of %.1f and flagacq "
                         "of %d\n",
                         sdrstat.elapsedTime, sdr->prn, snr, sdr->flagacq);
                add_message(bufferSDR);

                int i = sdr->prn - 1;
                ret = resetStructs(&sdrch[i]);
                elapsed_acq_time = 0;
                if (ret == -1) {
                    printf("resetStructs: error\n");
                }

                continue;
            }
        }

        if (elapsed_acq_time > 60) {

            if (!sdr->nav.flagdec || !sdr->nav.flagsync ||
                (sdr->nav.sdreph.week_gpst < GPS_WEEK)) {

                snprintf(
                    bufferSDR, sizeof(bufferSDR),
                    "%.3f  G%02d resetting, flagdec:%d, flagsync:%d, Week:%d\n",
                    sdrstat.elapsedTime, sdr->prn, sdr->nav.flagdec,
                    sdr->nav.flagsync, sdr->nav.sdreph.week_gpst);
                add_message(bufferSDR);

                int i = sdr->prn - 1;
                ret = resetStructs(&sdrch[i]);
                elapsed_acq_time = 0;
                if (ret == -1) {
                    printf("resetStructs: error\n");
                }

                continue;
            }
        }

        if (elapsed_acq_time > 60) {

            mlock(hobsmtx);
            int i = sdr->prn - 1;
            el = sdrstat.obs_v[i * 11 + 10];
            unmlock(hobsmtx);

            if (el < SV_EL_RESET_MASK) {

                snprintf(bufferSDR, sizeof(bufferSDR),
                         "%.3f  G%02d resetting, SV el: %.1f\n",
                         sdrstat.elapsedTime, i + 1, el);
                add_message(bufferSDR);

                int i = sdr->prn - 1;
                ret = resetStructs(&sdrch[i]);
                elapsed_acq_time = 0;
                if (ret == -1) {
                    printf("resetStructs: error\n");
                }

                continue;
            }
        }

        if (!sdr->flagacq) {

            if (acqpower != NULL)
                free(acqpower);
            acqpower =
                (double *)calloc(sizeof(double), sdr->nsamp * sdr->acq.nfreq);

            buffloc = sdraqcuisition(sdr, acqpower);

            start_acq_timer = time(NULL);
        }

        if (sdr->flagacq) {
            bufflocnow = sdrtracking(sdr, buffloc, cnt);
            if (sdr->flagtrk) {

                cumsumcorr(&sdr->trk, sdr->nav.ocode[sdr->nav.ocodei]);

                sdr->trk.flagloopfilter = 0;
                if (!sdr->nav.flagsync) {
                    pll(sdr, &sdr->trk.prm1, sdr->ctime);
                    dll(sdr, &sdr->trk.prm1, sdr->ctime);
                    sdr->trk.flagloopfilter = 1;
                } else if (sdr->nav.swloop) {
                    pll(sdr, &sdr->trk.prm2, (double)sdr->trk.loopms / 1000);
                    dll(sdr, &sdr->trk.prm2, (double)sdr->trk.loopms / 1000);
                    sdr->trk.flagloopfilter = 2;

                    mlock(hobsmtx);

                    if (loopcnt % (SNSMOOTHMS / sdr->trk.loopms) == 0) {
                        setobsdata(sdr, buffloc, cnt, &sdr->trk, 1);
                    } else {
                        setobsdata(sdr, buffloc, cnt, &sdr->trk, 0);
                    }
                    unmlock(hobsmtx);

                    loopcnt++;
                }

                if (sdr->trk.flagloopfilter)
                    clearcumsumcorr(&sdr->trk);
                cnt++;
                buffloc += sdr->currnsamp;
            }
        }

        sdr->trk.buffloc = buffloc;
    }

    if (sdr->flagacq) {
        SDRPRINTF("SDR channel %s thread finished! Delay=%d [ms]\n",
                  sdr->satstr, (int)(bufflocnow - buffloc) / sdr->nsamp);
    } else {
        SDRPRINTF("SDR channel %s thread finished!\n", sdr->satstr);
    }

    return THRETVAL;
}

extern void *datathread(void *arg) {

    if (rcvgrabstart(&sdrini) < 0) {
        quitsdr(&sdrini, 4);
    }

    while (!sdrstat.stopflag) {
        if (rcvgrabdata(&sdrini) < 0) {
            sdrstat.stopflag = ON;
        }
    }

    return THRETVAL;
}

extern int resetStructs(void *arg) {

    sdrch_t *sdr = (sdrch_t *)arg;

    mlock(hobsvecmtx);

    int prn = sdr->prn;
    int i = prn - 1;
    char bufferReset[MSG_LENGTH];
    char sat_id[8] = {0};

    memset(&sdrch[i], 0, sizeof(sdrch_t));

    sdrstat.azElCalculatedflag = 0;

    if (initsdrch(i + 1, sdrini.sys[i], sdrini.prn[i], sdrini.ctype[i],
                  sdrini.dtype[sdrini.ftype[i] - 1], sdrini.ftype[i],
                  sdrini.f_gain[sdrini.ftype[i] - 1],
                  sdrini.f_bias[sdrini.ftype[i] - 1],
                  sdrini.f_clock[sdrini.ftype[i] - 1],
                  sdrini.f_cf[sdrini.ftype[i] - 1],
                  sdrini.f_sf[sdrini.ftype[i] - 1],
                  sdrini.f_if[sdrini.ftype[i] - 1], &sdrch[i]) < 0) {

        SDRPRINTF("error: initsdrch call in resetStructs\n");
        quitsdr(&sdrini, 2);
    }
    unmlock(hobsvecmtx);

    int satno_reset = satno(sdrini.sys[i], sdrini.prn[i]);
    if (satno_reset > 0) {
        satno2id(satno_reset, sat_id);
    } else {
        snprintf(sat_id, sizeof(sat_id), "PRN%02d", sdrini.prn[i]);
    }

    snprintf(bufferReset, sizeof(bufferReset),
             "%.3f  resetStructs: %s channel has been reset and will "
             "reacquire in 10s",
             sdrstat.elapsedTime, sat_id);
    add_message(bufferReset);

    sleepms(10000);

    return 0;
}

extern int checkObsDelay(int prn) {

    int i = prn - 1;
    int resetFlag = 0;
    int ret = 0;
    char bufferReset[MSG_LENGTH];

    mlock(hobsvecmtx);
    int nsat = sdrstat.nsatValid;
    if (sdrch[i].flagacq == 1) {
        if (sdrch[i].elapsed_time_nav > 90) {
            resetFlag = 1;
            for (int j = 0; j < nsat; j++) {
                if (prn == sdrstat.obsValidList[j]) {
                    resetFlag = 0;
                }
            }
        }
    }
    unmlock(hobsvecmtx);

    if (resetFlag) {

        char sat_id[8] = {0};
        if (sdrch[i].sat > 0) {
            satno2id(sdrch[i].sat, sat_id);
        } else {
            int satnum = satno(sdrini.sys[i], sdrini.prn[i]);
            if (satnum > 0) {
                satno2id(satnum, sat_id);
            } else {
                snprintf(sat_id, sizeof(sat_id), "PRN%02d", prn);
            }
        }

        snprintf(bufferReset, sizeof(bufferReset),
                 "%.3f  checkObsDelay: resetting %s due to mismatch",
                 sdrstat.elapsedTime, sat_id);
        add_message(bufferReset);

        ret = resetStructs(&sdrch[i]);
        if (ret == -1) {
            printf("resetStructs: error\n");
        }
    }

    return 0;
}
