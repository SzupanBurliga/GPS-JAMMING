#include "sdr.h"
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>
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

extern void add_message(const char *msg)
{
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

extern void updateNavStatusWin(int counter)
{

  int prn[32] = {0};
  int flagacq[32] = {0};
  int flagsync[32] = {0};
  int flagdec[32] = {0};
  int nsat = 0;
  double lat = 0.0;
  double lon = 0.0;
  double hgt = 0.0;
  double gdop = 0.0;
  double clkBias = 0.0;
  double obs_v[MAXSAT*11] = {0.0};
  double vk1_v[MAXSAT] = {0.0};
  double rk1_v[MAXSAT] = {0.0};
  int gps_week;
  double gps_tow;
  char bufferNav[256];
  char str1[10];
  char json_buffer[16384];
  int json_pos = 0;

   
  mlock(hobsvecmtx);
  for (int i=0; i<32; i++) {
    prn[i] = sdrch[i].prn;
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
  int numIter = 32*11;
  for (int m=0; m<numIter; m++) {
    obs_v[m] = sdrstat.obs_v[m];
  }
  for (int n=0; n<32; n++) {
    vk1_v[n] = sdrstat.vk1_v[n];
    rk1_v[n] = sdrekf.rk1_v[n];
  }
  gps_tow = sdrstat.obs_v[(sdrstat.obsValidList[0]-1)*11+6] ;
  gps_week = (int)sdrstat.obs_v[(sdrstat.obsValidList[0]-1)*11+7];
  unmlock(hobsvecmtx);


  time_t utc_time_seconds = gps_to_utc(gps_week, gps_tow+clkBias/CTIME);
  struct tm utc_tm;
  gmtime_r(&utc_time_seconds, &utc_tm);
  sprintf(bufferNav,"%04d-%02d-%02d %02d:%02d:%02d.%03d",
     utc_tm.tm_year + 1900, utc_tm.tm_mon + 1, utc_tm.tm_mday,
     utc_tm.tm_hour, utc_tm.tm_min, utc_tm.tm_sec, (int)(gps_tow * 1000) % 1000);

  json_pos = 0;
  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "{");
  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos,
    "\"elapsed_time\":%.3f,", sdrstat.elapsedTime);
  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos,
    "\"time\":\"%s\",", bufferNav);

  printf("ETIME|%.3f\n", sdrstat.elapsedTime);
  printf("TIME|%s\n", bufferNav);


  if (sdrini.ekfFilterOn) {
    json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos,
      "\"filter\":\"EKF\",");
    printf("FILTER|EKF\n");
  } else {
    json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos,
      "\"filter\":\"WLS\",");
    printf("FILTER|WLS\n");
  }


  sprintf(bufferNav, "");
  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "\"acq_sv\":[");
  int first_acq = 1;
  for (int i=0; i<32; i++) {
    if (flagacq[i] ==1) {
      if (!first_acq) {
        json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, ",");
      }
      json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "%d", prn[i]);
      first_acq = 0;
      sprintf(str1, "%02d ", prn[i]);
      strcat(bufferNav, str1);
    }
  }
  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "],");
  printf("ACQSV|%s\n", bufferNav);


  sprintf(bufferNav, "");
  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "\"tracked\":[");
  int first_tracked = 1;
  for (int i=0; i<32; i++) {
    if (flagsync[i] ==1) {
      if (!first_tracked) {
        json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, ",");
      }
      json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "%d", prn[i]);
      first_tracked = 0;
      sprintf(str1, "%02d ", prn[i]);
      strcat(bufferNav, str1);
    }
  }
  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "],");
  printf("TRACKED|%s\n", bufferNav);


  sprintf(bufferNav, "");
  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "\"decoded\":[");
  int first_decoded = 1;
  for (int i=0; i<32; i++) {
    if (flagdec[i] ==1) {
      if (!first_decoded) {
        json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, ",");
      }
      json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "%d", prn[i]);
      first_decoded = 0;
      sprintf(str1, "%02d ", prn[i]);
      strcat(bufferNav, str1);
    }
  }
  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "],");
  printf("DECODED|%s\n", bufferNav);



  sprintf(bufferNav, "%.7f|%.7f|%.1f|%.2f|%.5e|%llu",
    lat, lon, hgt, gdop, clkBias/CTIME, (unsigned long long)sdrstat.buffcnt*RTLSDR_DATABUFF_SIZE);

  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos,
    "\"position\":{\"nsat\":%d,\"lat\":%.7f,\"lon\":%.7f,\"hgt\":%.1f,\"gdop\":%.2f,\"clk_bias\":%.5e,\"buffcnt\":%llu},",
    nsat, lat, lon, hgt, gdop, clkBias/CTIME, (unsigned long long)sdrstat.buffcnt*RTLSDR_DATABUFF_SIZE);

  printf("LLA|%02d|%s\n", nsat, bufferNav);


  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "\"observations\":[");
  for (int i=0; i<nsat; i++) {
    int prn = sdrstat.obsValidList[i];

    sprintf(bufferNav, "%02d|%.1f|%d|%.1f|%.1f|%05.1f|%04.1f|%05.1f|%7.1f",
      (int)obs_v[(prn-1)*11+0],
      obs_v[(prn-1)*11+6],
      (int)obs_v[(prn-1)*11+7],
      obs_v[(prn-1)*11+8],
      obs_v[(prn-1)*11+5],
      obs_v[(prn-1)*11+9],
      obs_v[(prn-1)*11+10],
      rk1_v[(prn-1)],
      vk1_v[(prn-1)]);

    if (i > 0) {
      json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, ",");
    }
    json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos,
      "{\"prn\":%d,\"tow\":%.1f,\"week\":%d,\"snr\":%.1f,\"doppler\":%.1f,\"az\":%.1f,\"el\":%.1f,\"residual\":%.1f,\"innovation\":%.1f}",
      (int)obs_v[(prn-1)*11+0],
      obs_v[(prn-1)*11+6],
      (int)obs_v[(prn-1)*11+7],
      obs_v[(prn-1)*11+8],
      obs_v[(prn-1)*11+5],
      obs_v[(prn-1)*11+9],
      obs_v[(prn-1)*11+10],
      rk1_v[(prn-1)],
      vk1_v[(prn-1)]);

    printf("OBS|%s\n", bufferNav);
  }
  json_pos += snprintf(json_buffer + json_pos, sizeof(json_buffer) - json_pos, "]}");

  send_json_http(json_buffer);
}

