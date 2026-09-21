import os
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend for server
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal
import soundfile as sf
import time

def validate_audio_file(file_path):
    """
    Validate that the audio file exists and is not empty.
    Returns (True, "") if valid, (False, "Error message") otherwise.
    """
    if not os.path.exists(file_path):
        return False, "Audio file does not exist."
    if os.path.getsize(file_path) == 0:
        return False, "Audio file is empty."
    return True, ""

def load_audio(file_path, target_sr=22050):
    """
    Load audio, resample, and convert to mono using soundfile and scipy.
    Returns (y, sr, orig_sr, duration, channels).
    """
    orig_sr = None
    channels = 1
    duration = 0.0
    
    try:
        info = sf.info(file_path)
        orig_sr = info.samplerate
        channels = info.channels
        duration = info.frames / float(info.samplerate)
    except Exception as e:
        raise ValueError(f"Could not read audio info: {e}")

    # Read full audio
    y, sr = sf.read(file_path)
    if orig_sr is None:
        orig_sr = sr
        duration = len(y) / float(sr)
        channels = 1 if len(y.shape) == 1 else y.shape[1]
        
    # Convert to mono if necessary
    if len(y.shape) > 1:
        y = np.mean(y, axis=1)
        
    # Resample if necessary
    if sr != target_sr:
        num_samples = int(len(y) * float(target_sr) / sr)
        if num_samples > 0:
            y = scipy.signal.resample(y, num_samples)
        sr = target_sr
            
    return y, sr, orig_sr, duration, channels

def trim_silence(y, top_db=40):
    """
    Conservatively trim leading and trailing silence using numpy.
    Uses an amplitude threshold equivalent to top_db relative to peak.
    """
    if len(y) == 0:
        return y
        
    peak = np.max(np.abs(y))
    if peak == 0:
        return y
        
    # top_db corresponds to 10**(-top_db/20) amplitude relative to peak
    threshold = peak * (10.0 ** (-top_db / 20.0))
    
    # Find first and last frames above threshold
    non_silent = np.where(np.abs(y) > threshold)[0]
    
    if len(non_silent) > 0:
        start_idx = non_silent[0]
        end_idx = non_silent[-1] + 1
        return y[start_idx:end_idx]
    else:
        return y

def generate_waveform(y, sr, output_path):
    """
    Generate and save a waveform plot using matplotlib.
    Avoids librosa.display.waveshow.
    """
    plt.figure(figsize=(10, 3))
    plt.style.use('dark_background')
    
    # Downsample for faster plotting without losing visual fidelity
    max_points = 20000
    if len(y) > max_points:
        downsample_factor = len(y) // max_points
        y_plot = y[::downsample_factor]
    else:
        y_plot = y
        
    times = np.linspace(0, len(y) / sr, num=len(y_plot))
    
    # Plot waveform with amber/gold color matching CarnaticAI
    plt.plot(times, y_plot, color='#d4af37', alpha=0.8, linewidth=0.5)
    
    # Fill between for a fuller look (simulating waveshow)
    plt.fill_between(times, y_plot, 0, color='#d4af37', alpha=0.3)
    
    plt.axis('off')
    plt.tight_layout(pad=0)
    
    plt.savefig(output_path, transparent=True, bbox_inches='tight', pad_inches=0)
    plt.close()

def process_reference_audio(original_file_path, upload_folder, base_filename):
    """
    Orchestrator function to process a reference audio file.
    Returns a dictionary of metadata if successful, or None if failed.
    """
    is_valid, error_msg = validate_audio_file(original_file_path)
    if not is_valid:
        raise ValueError(error_msg)
        
    target_sr = 22050
    
    # Load and standardize
    y, sr, orig_sr, duration, channels = load_audio(original_file_path, target_sr=target_sr)
    
    # Trim silence only for the analysis representation
    y_trimmed = trim_silence(y)
    
    # Generate waveform image
    # Use same base filename but replace extension with _waveform.png
    filename_without_ext = os.path.splitext(base_filename)[0]
    waveform_filename = f"{filename_without_ext}_waveform.png"
    waveform_path = os.path.join(upload_folder, waveform_filename)
    
    generate_waveform(y_trimmed, sr, waveform_path)
    
    return {
        "audio_duration": duration,
        "audio_original_sr": orig_sr,
        "audio_analysis_sr": sr,
        "audio_channels": channels,
        "audio_waveform_filename": waveform_filename,
        "audio_processing_status": "Ready"
    }
