#include "sdr.h"
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#define HTTP_HOST "127.0.0.1"
#define HTTP_PORT 1234

static int send_json_http(const char *json_data) {
    int sock;
    struct sockaddr_in server;
    char request[8192];
    int json_len = strlen(json_data);

    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == -1) {
        return -1;
    }

    struct timeval timeout;
    timeout.tv_sec = 1;
    timeout.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));

    server.sin_family = AF_INET;
    server.sin_port = htons(HTTP_PORT);
    server.sin_addr.s_addr = inet_addr(HTTP_HOST);

    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
        close(sock);
        return -1;
    }

    snprintf(request, sizeof(request),
             "POST /data HTTP/1.1\r\n"
             "Host: %s:%d\r\n"
             "Content-Type: application/json\r\n"
             "Content-Length: %d\r\n"
             "Connection: close\r\n"
             "\r\n"
             "%s",
             HTTP_HOST, HTTP_PORT, json_len, json_data);

    if (send(sock, request, strlen(request), 0) < 0) {
        close(sock);
        return -1;
    }

    // Odczytaj odpowiedź (żeby uniknąć BrokenPipe po stronie serwera)
    char response[256];
    recv(sock, response, sizeof(response) - 1, 0);

    close(sock);
    return 0;
}

void init_sdrgui_messages() {
    for (int i = 0; i < MAX_MESSAGES; i++) {
        sdrgui.messages[i] = NULL;
    }
    sdrgui.message_count = 0;
}

extern void add_message(const char *msg) {
    pthread_mutex_lock(&hmsgmtx);
    if (sdrgui.message_count < MAX_MESSAGES) {
        sdrgui.messages[sdrgui.message_count++] = strdup(msg);
    } else {
        if (sdrgui.messages[0] != NULL) {
            free(sdrgui.messages[0]);
            sdrgui.messages[0] = NULL;
        }
        for (int i = 1; i < MAX_MESSAGES; i++) {
            sdrgui.messages[i - 1] = sdrgui.messages[i];
        }
        sdrgui.messages[MAX_MESSAGES - 1] = strdup(msg);
    }
    pthread_mutex_unlock(&hmsgmtx);
}

extern void updateNavStatusWin(int counter) {

    int prn[MAXSAT] = {0};
    int flagacq[MAXSAT] = {0};
    int flagsync[MAXSAT] = {0};
    int flagdec[MAXSAT] = {0};
    int nsat = 0;
    double lat = 0.0;
    double lon = 0.0;
    double hgt = 0.0;
    double gdop = 0.0;
    double clkBias = 0.0;
    double obs_v[MAXSAT * 11] = {0.0};
    double vk1_v[MAXSAT] = {0.0};
    double rk1_v[MAXSAT] = {0.0};
    int gps_week = 0;
    double gps_tow = 0.0;
    char bufferNav[256];
    char str1[10];
    char json_buffer[16384];
    int json_pos = 0;

    mlock(hobsvecmtx);
    int used_ch = sdrini.nch < MAXSAT ? sdrini.nch : MAXSAT;
    for (int i = 0; i < used_ch; i++) {
        /* For GLONASS, display frequency number instead of channel index */
        if (sdrch[i].sys == SYS_GLO) {
            prn[i] = sdrch[i].nav.sdreph.geph.frq;
        } else {
            prn[i] = sdrch[i].prn;
        }
        flagacq[i] = sdrch[i].flagacq;
        flagsync[i] = sdrch[i].nav.flagsync;
        flagdec[i] = sdrch[i].nav.flagdec;
    }
    nsat = sdrstat.nsatValid;
    lat = sdrstat.lat;
    lon = sdrstat.lon;
    hgt = sdrstat.hgt;
    gdop = sdrstat.gdop;
    clkBias = sdrstat.xyzdt[3];
    memcpy(obs_v, sdrstat.obs_v, sizeof(obs_v));
    memcpy(vk1_v, sdrstat.vk1_v, sizeof(vk1_v));
    memcpy(rk1_v, sdrekf.rk1_v, sizeof(rk1_v));
    if (nsat > 0) {
        int ref_prn = sdrstat.obsValidList[0];
        if (ref_prn >= 1 && ref_prn <= MAXSAT) {
            gps_tow = sdrstat.obs_v[(ref_prn - 1) * 11 + 6];
            gps_week = (int)sdrstat.obs_v[(ref_prn - 1) * 11 + 7];
        }
    }
    unmlock(hobsvecmtx);

    if (nsat == 0) {
        gps_tow = 0.0;
        gps_week = 0;
    }

    static int hold_valid = 0;
    static double hold_lat = 0.0, hold_lon = 0.0, hold_hgt = 0.0;
    static double hold_time = 0.0;
    const int MIN_VALID_NSAT = 4;
    const double MAX_JUMP_SPEED = 500.0; /* m/s */
    double current_time = sdrstat.elapsedTime;
    int fix_valid = (nsat >= MIN_VALID_NSAT);

    if (fix_valid && hold_valid) {
        double dt = current_time - hold_time;
        if (dt > 0.0) {
            double lat1 = hold_lat * PI / 180.0;
            double lat2 = lat * PI / 180.0;
            double dlat = lat2 - lat1;
            double dlon = (lon - hold_lon) * PI / 180.0;
            double sin_dlat = sin(dlat / 2.0);
            double sin_dlon = sin(dlon / 2.0);
            double a = sin_dlat * sin_dlat +
                       cos(lat1) * cos(lat2) * sin_dlon * sin_dlon;
            double c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a));
            double distance = 6371000.0 * c;
            double speed = distance / dt;
            if (speed > MAX_JUMP_SPEED) {
                fix_valid = 0;
            }
        }
    }

    int hold_applied = 0;
    if (!fix_valid && hold_valid) {
        lat = hold_lat;
        lon = hold_lon;
        hgt = hold_hgt;
        hold_applied = 1;
    } else if (fix_valid) {
        hold_lat = lat;
        hold_lon = lon;
        hold_hgt = hgt;
        hold_time = current_time;
        hold_valid = 1;
    }

    #define JSON_APPEND(fmt, ...)                                                          \
    do {                                                                                  \
        int _n = snprintf(json_buffer + json_pos,                                          \
                           sizeof(json_buffer) - json_pos, fmt, ##__VA_ARGS__);           \
        if (_n < 0) _n = 0;                                                               \
        if ((size_t)_n >= sizeof(json_buffer) - json_pos) {                                \
            json_pos = sizeof(json_buffer) - 1;                                           \
        } else {                                                                          \
            json_pos += _n;                                                               \
        }                                                                                 \
    } while (0)

    time_t utc_time_seconds = gps_to_utc(gps_week, gps_tow + clkBias / CTIME);
    struct tm utc_tm;
    gmtime_r(&utc_time_seconds, &utc_tm);
    sprintf(bufferNav, "%04d-%02d-%02d %02d:%02d:%02d.%03d",
            utc_tm.tm_year + 1900, utc_tm.tm_mon + 1, utc_tm.tm_mday,
            utc_tm.tm_hour, utc_tm.tm_min, utc_tm.tm_sec,
            (int)(gps_tow * 1000) % 1000);

    json_pos = 0;
    JSON_APPEND("{");
    JSON_APPEND("\"elapsed_time\":%.3f,", sdrstat.elapsedTime);
    JSON_APPEND("\"time\":\"%s\",", bufferNav);

    printf("ETIME|%.3f\n", sdrstat.elapsedTime);
    printf("TIME|%s\n", bufferNav);

    if (sdrini.ekfFilterOn) {
        JSON_APPEND("\"filter\":\"EKF\",");
        printf("FILTER|EKF\n");
    } else {
        JSON_APPEND("\"filter\":\"WLS\",");
        printf("FILTER|WLS\n");
    }

    bufferNav[0] = '\0';
    JSON_APPEND("\"acq_sv\":[");
    int first_acq = 1;
    for (int i = 0; i < used_ch; i++) {
        if (flagacq[i] == 1) {
            if (!first_acq) {
                JSON_APPEND(",");
            }
            JSON_APPEND("%d", prn[i]);
            first_acq = 0;
            sprintf(str1, "%02d ", prn[i]);
            strcat(bufferNav, str1);
        }
    }
    JSON_APPEND("],");
    printf("ACQSV|%s\n", bufferNav);

    bufferNav[0] = '\0';
    JSON_APPEND("\"tracked\":[");
    int first_tracked = 1;
    for (int i = 0; i < used_ch; i++) {
        if (flagsync[i] == 1) {
            if (!first_tracked) {
                JSON_APPEND(",");
            }
            JSON_APPEND("%d", prn[i]);
            first_tracked = 0;
            sprintf(str1, "%02d ", prn[i]);
            strcat(bufferNav, str1);
        }
    }
    JSON_APPEND("],");
    printf("TRACKED|%s\n", bufferNav);

    bufferNav[0] = '\0';
    JSON_APPEND("\"decoded\":[");
    int first_decoded = 1;
    for (int i = 0; i < used_ch; i++) {
        if (flagdec[i] == 1) {
            if (!first_decoded) {
                JSON_APPEND(",");
            }
            JSON_APPEND("%d", prn[i]);
            first_decoded = 0;
            sprintf(str1, "%02d ", prn[i]);
            strcat(bufferNav, str1);
        }
    }
    JSON_APPEND("],");
    printf("DECODED|%s\n", bufferNav);

    sprintf(bufferNav, "%.7f|%.7f|%.1f|%.2f|%.5e|%llu", lat, lon, hgt, gdop,
            clkBias / CTIME,
            (unsigned long long)sdrstat.buffcnt * FILE_BUFFSIZE);

    JSON_APPEND("\"position\":{\"nsat\":%d,\"lat\":%.7f,\"lon\":%.7f,\"hgt\":%"
                 ".1f,\"gdop\":%.2f,\"clk_bias\":%.5e,\"buffcnt\":%llu,\"hold\":%s},",
                 nsat, lat, lon, hgt, gdop, clkBias / CTIME,
                 (unsigned long long)sdrstat.buffcnt * FILE_BUFFSIZE,
                 hold_applied ? "true" : "false");

    printf("LLA|%02d|%s\n", nsat, bufferNav);

    JSON_APPEND("\"observations\":[");
    for (int i = 0; i < nsat; i++) {
        int prn_val = sdrstat.obsValidList[i];
        if (prn_val < 1 || prn_val > MAXSAT) {
            continue;
        }
        sprintf(bufferNav, "%02d|%.1f|%d|%.1f|%.1f|%05.1f|%04.1f|%05.1f|%7.1f",
                (int)obs_v[(prn_val - 1) * 11 + 0],
                obs_v[(prn_val - 1) * 11 + 6],
                (int)obs_v[(prn_val - 1) * 11 + 7],
                obs_v[(prn_val - 1) * 11 + 8],
                obs_v[(prn_val - 1) * 11 + 5],
                obs_v[(prn_val - 1) * 11 + 9],
                obs_v[(prn_val - 1) * 11 + 10], rk1_v[(prn_val - 1)],
                vk1_v[(prn_val - 1)]);

        if (i > 0) {
            JSON_APPEND(",");
        }
        JSON_APPEND(
            "{\"prn\":%d,\"tow\":%.1f,\"week\":%d,\"snr\":%.1f,\"doppler\":%"
            ".1f,\"az\":%.1f,\"el\":%.1f,\"residual\":%.1f,\"innovation\":%.1f}",
            (int)obs_v[(prn_val - 1) * 11 + 0],
            obs_v[(prn_val - 1) * 11 + 6],
            (int)obs_v[(prn_val - 1) * 11 + 7],
            obs_v[(prn_val - 1) * 11 + 8],
            obs_v[(prn_val - 1) * 11 + 5],
            obs_v[(prn_val - 1) * 11 + 9],
            obs_v[(prn_val - 1) * 11 + 10], rk1_v[(prn_val - 1)],
            vk1_v[(prn_val - 1)]);

        printf("OBS|%s\n", bufferNav);
    }
    JSON_APPEND("]}");

    if (json_pos >= (int)sizeof(json_buffer)) {
        json_buffer[sizeof(json_buffer) - 1] = '\0';
    }

    send_json_http(json_buffer);

#undef JSON_APPEND
}
