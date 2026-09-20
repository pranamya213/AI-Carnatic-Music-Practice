import os
import librosa
import librosa.display
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend for server
import matplotlib.pyplot as plt
import numpy as np
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
    Load audio, resample, and convert to mono using librosa.
    Returns (y, sr, orig_sr, duration, channels).
    """
    import soundfile as sf
    import warnings
    
    orig_sr = None
    channels = 1
    duration = 0.0
    
    try:
        info = sf.info(file_path)
        orig_sr = info.samplerate
        channels = info.channels
        duration = info.frames / float(info.samplerate)
    except Exception as e:
        # Fallback if sf.info fails
        pass

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        y, sr = librosa.load(file_path, sr=target_sr, mono=True)
        
    if orig_sr is None:
        duration = librosa.get_duration(y=y, sr=sr)
        # Attempt to get original sr via librosa
        try:
            _, orig_sr_fallback = librosa.load(file_path, sr=None, duration=0.1)
            orig_sr = orig_sr_fallback
        except:
            orig_sr = sr # fallback to target sr if original cannot be determined
            
    return y, sr, orig_sr, duration, channels

def trim_silence(y):
    """
    Conservatively trim leading and trailing silence.
    Uses a very low threshold so it only removes absolute silence.
    """
    y_trimmed, index = librosa.effects.trim(y, top_db=40)
    return y_trimmed

def generate_waveform(y, sr, output_path):
    """
    Generate and save a waveform plot using matplotlib.
    """
    plt.figure(figsize=(10, 3))
    
    # Use dark theme matching CarnaticAI
    plt.style.use('dark_background')
    
    # Plot waveform with amber/gold color
    librosa.display.waveshow(y, sr=sr, color='#d4af37', alpha=0.8)
    
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
