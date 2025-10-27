#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: bradbandJammer
# Author: szymon
# GNU Radio version: 3.10.12.0

from gnuradio import analog
from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import threading




class broadbandJammer(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "bradbandJammer", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 2048000
        self.duration = duration = 120
        self.sweep_time = sweep_time = 2
        self.sweep_bw = sweep_bw = 1e6
        self.num_samp = num_samp = int(samp_rate * duration)

        ##################################################
        # Blocks
        ##################################################

        self.blocks_head_0 = blocks.head(gr.sizeof_char*1, (num_samp * 2))
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_char*1, '/home/szymon/Downloads/GPS_JAMMING/GPS-JAMMING/simulate/frontend/jammers/jammer_file.bin', False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.blocks_complex_to_interleaved_char_0 = blocks.complex_to_interleaved_char(False, 127.0)
        self.analog_noise_source_x_0 = analog.noise_source_c(analog.GR_GAUSSIAN, 1, 0)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_noise_source_x_0, 0), (self.blocks_complex_to_interleaved_char_0, 0))
        self.connect((self.blocks_complex_to_interleaved_char_0, 0), (self.blocks_head_0, 0))
        self.connect((self.blocks_head_0, 0), (self.blocks_file_sink_0, 0))


    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_num_samp(int(self.samp_rate * self.duration))

    def get_duration(self):
        return self.duration

    def set_duration(self, duration):
        self.duration = duration
        self.set_num_samp(int(self.samp_rate * self.duration))

    def get_sweep_time(self):
        return self.sweep_time

    def set_sweep_time(self, sweep_time):
        self.sweep_time = sweep_time

    def get_sweep_bw(self):
        return self.sweep_bw

    def set_sweep_bw(self, sweep_bw):
        self.sweep_bw = sweep_bw

    def get_num_samp(self):
        return self.num_samp

    def set_num_samp(self, num_samp):
        self.num_samp = num_samp
        self.blocks_head_0.set_length((self.num_samp * 2))




def main(top_block_cls=broadbandJammer, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    tb.flowgraph_started.set()

    tb.wait()


if __name__ == '__main__':
    main()
