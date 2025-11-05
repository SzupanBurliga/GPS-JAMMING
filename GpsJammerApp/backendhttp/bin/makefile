#
# makefile for gnss-sdrlib-pvt
#

SRC=../
RTKLIB=../lib/rtklib
NMLLIB=../lib/nml
RTLSDR=../rcv/rtlsdr

INCLUDE=-I$(SRC) -I$(RTKLIB) -I$(RTLSDR) -I$(NMLLIB)

CC=gcc
OPTIONS=-DSSE2_ENABLE -DFFTMTX -ggdb -DRTLSDR

LIBS=-lfec -lusb-1.0 -lrtlsdr

OBS= sdrmain.o sdrcmn.o sdracq.o sdrcode.o sdrinit.o sdrnav.o\
     sdrnav_gps.o sdrnav_sbs.o sdrpvt.o sdrrcv.o sdrtrk.o sdrsync.o sdrout.o\
     nml.o nml_util.o rtkcmn.o rtlsdr.o convenience.o


# Compile flag options:
# Set -O3 to -O0 to use GDB. Leave as -O3 for best real-time performance.
# Use -Wno-stringop-truncation to stop string warnings in rinex.c and others
# Add -g and -O0 or -O1 for running valgrind
#CFLAGS=-Wall -O0 -march=native $(INCLUDE) $(OPTIONS) -Wno-stringop-truncation -g
CFLAGS=-Wall -O3 -march=native $(INCLUDE) $(OPTIONS) -Wno-stringop-truncation
LDLIBS=-lm -lrt -lfftw3f -lfftw3f_threads -lpthread $(LIBS)

BIN= gnssdec
$(BIN): $(OBS)
	 $(CC) -o $(BIN) $(OBS) $(CFLAGS) $(LDLIBS)

sdrmain.o: $(SRC)/sdrmain.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrmain.c
sdrcmn.o : $(SRC)/sdrcmn.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrcmn.c
sdracq.o : $(SRC)/sdracq.c
	$(CC) -c $(CFLAGS) $(SRC)/sdracq.c
sdrcode.o: $(SRC)/sdrcode.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrcode.c
#sdrekf.o: $(SRC)/sdrekf.c
#	$(CC) -c $(CFLAGS) $(SRC)/sdrekf.c
sdrout.o: $(SRC)/sdrout.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrout.c
sdrinit.o: $(SRC)/sdrinit.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrinit.c
#sdrmsg.o: $(SRC)/sdrmsg.c
#	$(CC) -c $(CFLAGS) $(SRC)/sdrmsg.c
sdrnav.o : $(SRC)/sdrnav.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrnav.c
sdrnav_gps.o : $(SRC)/sdrnav_gps.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrnav_gps.c
sdrnav_sbs.o : $(SRC)/sdrnav_sbs.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrnav_sbs.c
sdrpvt.o: $(SRC)/sdrpvt.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrpvt.c
sdrrcv.o : $(SRC)/sdrrcv.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrrcv.c
sdrtrk.o : $(SRC)/sdrtrk.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrtrk.c
sdrsync.o : $(SRC)/sdrsync.c
	$(CC) -c $(CFLAGS) $(SRC)/sdrsync.c
rtkcmn.o   : $(RTKLIB)/rtkcmn.c
	$(CC) -c $(CFLAGS) $(RTKLIB)/rtkcmn.c
nml.o    : $(NMLLIB)/nml.c
	$(CC) -c $(CFLAGS) $(NMLLIB)/nml.c
nml_util.o    : $(NMLLIB)/nml_util.c
	$(CC) -c $(CFLAGS) $(NMLLIB)/nml_util.c
rtlsdr.o : $(RTLSDR)/rtlsdr.c
	$(CC) -c $(CFLAGS) $(RTLSDR)/rtlsdr.c
# convenience frontend
convenience.o : $(RTLSDR)/convenience.c
	$(CC) -c $(CFLAGS) $(RTLSDR)/convenience.c

sdrmain.o: $(SRC)/sdr.h
sdrcmn.o : $(SRC)/sdr.h
sdracq.o : $(SRC)/sdr.h
sdrcode.o: $(SRC)/sdr.h
#sdrekf.o: $(SRC)/sdr.h
sdrgui.o:  $(SRC)/sdr.h
sdrinit.o: $(SRC)/sdr.h
#sdrmsg.o: $(SRC)/sdr.h
sdrnav.o : $(SRC)/sdr.h
sdrnav_gps.o : $(SRC)/sdr.h
sdrnav_sbs.o : $(SRC)/sdr.h
sdrrcv.o : $(SRC)/sdr.h
sdrtrk.o : $(SRC)/sdr.h
sdrsync.o: $(SRC)/sdr.h
rtkcmn.o : $(SRC)/sdr.h
rtlsdr.o : $(SRC)/sdr.h
convenience.o : $(SRC)/sdr.h


clean:
	rm -f *.o $(BIN)
