#!/usr/bin/env python3
"""
Simple GPS Jammer - adds interference to GPS IQ files (int8 format)
"""
import numpy as np
import matplotlib.pyplot as plt

def generate_gps_jammer_iq(length, amplitude, frequency, sample_rate, jammer_type="noise"):
    """
    Generate a GPS jammer signal as complex IQ data (int8 format).

    Args:
        length (int): Number of IQ samples.
        amplitude (float): Jammer amplitude (can be > 1.0 for strong jamming).
        frequency (float): Jammer frequency offset in Hz.
        sample_rate (float): Sample rate in Hz.
        jammer_type (str): "noise" or "tone"

    Returns:
        tuple: (I_samples, Q_samples) as int8 arrays.
    """
    # Scale amplitude - allow values > 1.0 for stronger jamming
    amp = int(min(127 * amplitude, 127))
    
    if jammer_type == "noise":
        # Generate white noise - more effective for GPS jamming
        np.random.seed(42)  # Reproducible results
        I_signal = amp * np.random.randn(length)
        Q_signal = amp * np.random.randn(length)
    else:  # tone
        t = np.arange(length) / sample_rate
        phase = 2 * np.pi * frequency * t
        I_signal = amp * np.cos(phase)
        Q_signal = amp * np.sin(phase)
    
    # Clip to int8 range and convert
    I_signal = np.clip(I_signal, -127, 127).astype(np.int8)
    Q_signal = np.clip(Q_signal, -127, 127).astype(np.int8)
    
    return I_signal, Q_signal

def plot_jammer_waterfall(I_jam, Q_jam, sample_rate, duration_ms=10.0, save_plot=True):
    """
    Plot jammer waterfall (spectrogram) focused on GPS L1 frequency region.
    
    Args:
        I_jam, Q_jam: Jammer I/Q signals
        sample_rate: Sample rate in Hz
        duration_ms: How many milliseconds to plot
        save_plot: Whether to save plot to file
    """
    # Calculate number of samples to plot
    num_samples_plot = int(duration_ms * sample_rate / 1000)
    num_samples_plot = min(num_samples_plot, len(I_jam))
    
    # Create complex signal
    complex_jam = I_jam[:num_samples_plot] + 1j * Q_jam[:num_samples_plot]
    
    # Parameters for spectrogram
    window_size = 1024  # FFT window size
    overlap = window_size // 2  # 50% overlap
    
    # Create figure with waterfall plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot 1: Waterfall/Spectrogram
    f, t, Sxx = plt.matplotlib.mlab.specgram(
        complex_jam, NFFT=window_size, Fs=sample_rate, 
        noverlap=overlap, window=np.hanning(window_size)
    )
    
    # Convert to dB and plot
    Sxx_db = 10 * np.log10(np.abs(Sxx) + 1e-12)
    
    # Create waterfall plot
    im1 = ax1.imshow(Sxx_db, aspect='auto', origin='lower', 
                     extent=[t[0]*1000, t[-1]*1000, f[0]/1e6, f[-1]/1e6],
                     cmap='plasma', interpolation='bilinear')
    
    ax1.set_xlabel('Time (ms)')
    ax1.set_ylabel('Frequency (MHz)')
    ax1.set_title('GPS Jammer Waterfall - Frequency vs Time\n(Baseband representation)')
    
    # Add colorbar
    cbar1 = plt.colorbar(im1, ax=ax1)
    cbar1.set_label('Power (dB)')
    
    # Add reference lines for GPS L1 region (in baseband this would be around DC)
    ax1.axhline(y=0, color='red', linestyle='--', alpha=0.7, 
                label='DC (GPS L1 in baseband)')
    ax1.legend()
    
    # Plot 2: Average Power Spectral Density
    # Calculate PSD
    f_psd, psd = plt.matplotlib.mlab.psd(complex_jam, NFFT=window_size, Fs=sample_rate)
    
    ax2.plot(f_psd/1e6, 10*np.log10(psd + 1e-12), 'b-', linewidth=2)
    ax2.set_xlabel('Frequency (MHz)')
    ax2.set_ylabel('Power Spectral Density (dB/Hz)')
    ax2.set_title('GPS Jammer - Average Power Spectral Density')
    ax2.grid(True, alpha=0.3)
    
    # Highlight DC region (where GPS L1 would be in baseband)
    ax2.axvline(x=0, color='red', linestyle='--', alpha=0.7, 
                label='DC (GPS L1 in baseband)')
    ax2.legend()
    
    # Add text with jammer info
    info_text = f"Sample Rate: {sample_rate/1e6:.1f} MHz\n"
    info_text += f"Duration: {duration_ms:.1f} ms\n"
    info_text += f"Note: In baseband, GPS L1 (1575.42 MHz) appears at DC (0 Hz)"
    
    ax2.text(0.02, 0.98, info_text, transform=ax2.transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    if save_plot:
        plt.savefig('jammer_waterfall_gps_l1.png', dpi=300, bbox_inches='tight')
        print("Waterfall plot saved as 'jammer_waterfall_gps_l1.png'")
    
    plt.show()
    
    # Print some statistics
    print(f"\n=== Jammer Signal Analysis ===")
    print(f"Sample rate: {sample_rate/1e6:.2f} MHz")
    print(f"Nyquist frequency: {sample_rate/2/1e6:.2f} MHz")
    print(f"Signal duration: {len(complex_jam)/sample_rate*1000:.2f} ms")
    print(f"Peak power: {np.max(10*np.log10(psd + 1e-12)):.1f} dB/Hz")
    print(f"Note: GPS L1 (1575.42 MHz) in baseband appears at DC (0 Hz)")

def add_gps_jammer_to_bin(input_bin_path, output_bin_path, amplitude=0.5, frequency=10000, sample_rate=2048000):
    """
    Add jammer signal to a GPS .bin file (int8 IQ format).

    Args:
        input_bin_path (str): Path to input GPS .bin file (int8 IQ interleaved).
        output_bin_path (str): Path to output jammed file.
        amplitude (float): Jammer amplitude (0.0 to 1.0).
        frequency (float): Jammer frequency offset in Hz.
        sample_rate (float): Sample rate in Hz.
    """
    # Read GPS IQ data (int8 interleaved I,Q,I,Q...)
    raw_data = np.fromfile(input_bin_path, dtype=np.int8)
    
    # Check if file size is even (should be for IQ data)
    if len(raw_data) % 2 != 0:
        print(f"Warning: File size {len(raw_data)} is odd, truncating...")
        raw_data = raw_data[:-1]
    
    # Split into I and Q samples
    I_gps = raw_data[0::2].astype(np.int16)  # Every even index (I)
    Q_gps = raw_data[1::2].astype(np.int16)  # Every odd index (Q)
    
    # Generate jammer IQ signal
    num_samples = len(I_gps)
    I_jam, Q_jam = generate_gps_jammer_iq(num_samples, amplitude, frequency, sample_rate, "noise")
    
    # Add jammer to GPS signal
    I_mixed = I_gps + I_jam.astype(np.int16)
    Q_mixed = Q_gps + Q_jam.astype(np.int16)
    
    # Clip to int8 range (-128 to 127)
    I_mixed = np.clip(I_mixed, -128, 127).astype(np.int8)
    Q_mixed = np.clip(Q_mixed, -128, 127).astype(np.int8)
    
    # Interleave I,Q back together
    output_data = np.empty(len(I_mixed) * 2, dtype=np.int8)
    output_data[0::2] = I_mixed
    output_data[1::2] = Q_mixed
    
    # Write output file
    output_data.tofile(output_bin_path)
    print(f"GPS jammer added! Input: {len(raw_data)} bytes, Output: {len(output_data)} bytes")
    print(f"Jammer params: amplitude={amplitude}, frequency={frequency}Hz, sample_rate={sample_rate}Hz")

if __name__ == "__main__":
    # GPS Jammer Configuration - STRONG JAMMING
    input_bin = "test_uint8.bin"  # Twój plik GPS (int8 IQ)
    output_bin = "test_gps_jammed_strong.bin"  # Plik z SILNYM jammerem
    amplitude = 10.0  # Jammer strength - VERY STRONG (10x GPS signal)
    frequency = 0 # Jammer frequency offset in Hz (0 = DC, most effective)
    sample_rate = 2048000 # Sample rate in Hz (must match gps-sdr-sim)

    print(f"Adding GPS jammer to {input_bin}...")
    add_gps_jammer_to_bin(input_bin, output_bin, amplitude, frequency, sample_rate)
    print(f"Done! Output saved to {output_bin}")
    
    # Generate and plot jammer signal for analysis
    print("\nGenerating jammer signal for waterfall visualization...")
    plot_samples = min(50000, int(sample_rate * 0.01))  # 10ms of data for better waterfall
    I_jam_plot, Q_jam_plot = generate_gps_jammer_iq(plot_samples, amplitude, frequency, sample_rate, "noise")
    
    print("Creating GPS L1 jammer waterfall plot...")
    plot_jammer_waterfall(I_jam_plot, Q_jam_plot, sample_rate, duration_ms=10.0)
    print("GPS L1 jammer waterfall analysis complete!")
