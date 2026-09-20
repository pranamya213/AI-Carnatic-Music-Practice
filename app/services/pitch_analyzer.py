import os
import json
import librosa
import librosa.display
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def extract_pitch_contour(y, sr, fmin=80, fmax=1000):
    """
    Extract fundamental frequency (F0) using librosa.pyin.
    Returns times, f0, voiced_flag, voiced_probs.
    """
    # Use standard pyin parameters
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y, 
        fmin=fmin, 
        fmax=fmax, 
        sr=sr,
        fill_na=None # Leaves NaN for unvoiced
    )
    times = librosa.times_like(f0, sr=sr)
    return times, f0, voiced_flag, voiced_probs

def calculate_basic_pitch_statistics(f0, voiced_flag):
    """
    Calculate basic statistics for the pitch contour.
    Returns (median, min, max, voiced_percentage).
    """
    if f0 is None or len(f0) == 0:
        return None, None, None, 0.0
        
    voiced_f0 = f0[voiced_flag]
    
    if len(voiced_f0) == 0:
        return None, None, None, 0.0
        
    median_f0 = float(np.median(voiced_f0))
    min_f0 = float(np.min(voiced_f0))
    max_f0 = float(np.max(voiced_f0))
    voiced_percentage = float(len(voiced_f0) / len(f0) * 100)
    
    return median_f0, min_f0, max_f0, voiced_percentage

def save_pitch_data(times, f0, voiced_flag, voiced_probs, sample_rate, method, output_path):
    """
    Save the extracted pitch information as JSON.
    Converts NaN to None (null in JSON).
    """
    # Replace NaN with None
    f0_clean = [float(x) if not np.isnan(x) else None for x in f0]
    probs_clean = [float(x) if not np.isnan(x) else None for x in voiced_probs]
    
    data = {
        "sample_rate": sample_rate,
        "method": method,
        "times": [float(x) for x in times],
        "f0": f0_clean,
        "voiced_flag": [bool(x) for x in voiced_flag],
        "voiced_probability": probs_clean
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(data, f)

def generate_pitch_plot(times, f0, output_path):
    """
    Create a static pitch contour graph using Matplotlib.
    Matches CarnaticAI dark/gold styling.
    """
    plt.figure(figsize=(10, 3))
    plt.style.use('dark_background')
    
    # Plot only voiced regions (f0 contains NaN where unvoiced, so plt handles it correctly)
    plt.plot(times, f0, color='#d4af37', linewidth=2, alpha=0.9)
    
    plt.title("Teacher Reference Pitch Contour", color='#f5ebd5', fontsize=12, pad=10)
    plt.xlabel("Time (s)", color='#a99d8e', fontsize=10)
    plt.ylabel("Frequency (Hz)", color='#a99d8e', fontsize=10)
    
    # Style axes
    ax = plt.gca()
    ax.tick_params(colors='#a99d8e')
    for spine in ax.spines.values():
        spine.set_color('#5c4d3c')
        
    plt.grid(True, color='#5c4d3c', linestyle=':', alpha=0.5)
    plt.tight_layout(pad=1)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    plt.savefig(output_path, transparent=True, bbox_inches='tight', dpi=100)
    plt.close()

def analyze_pitch_for_lesson(audio_path, upload_folder, base_filename):
    """
    Orchestrates Phase 6 pitch analysis.
    Returns metadata dict to update the Lesson.
    """
    from app.services.audio_processor import load_audio, validate_audio_file
    
    is_valid, error_msg = validate_audio_file(audio_path)
    if not is_valid:
        raise ValueError(error_msg)
        
    target_sr = 22050
    # Reload audio to standard representation
    y, sr, _, _, _ = load_audio(audio_path, target_sr=target_sr)
    
    # Configurations
    fmin = 80
    fmax = 1000
    method = "librosa.pyin"
    
    times, f0, voiced_flag, voiced_probs = extract_pitch_contour(y, sr, fmin=fmin, fmax=fmax)
    
    median_f0, min_f0, max_f0, voiced_percentage = calculate_basic_pitch_statistics(f0, voiced_flag)
    
    # Filenames
    filename_without_ext = os.path.splitext(base_filename)[0]
    data_filename = f"{filename_without_ext}_pitch.json"
    plot_filename = f"{filename_without_ext}_pitch_plot.png"
    
    # Paths (store pitch data in uploads/lessons/pitch/ to avoid cluttering main folder)
    pitch_folder = os.path.join(upload_folder, 'pitch')
    data_path = os.path.join(pitch_folder, data_filename)
    plot_path = os.path.join(upload_folder, plot_filename) # Plot goes to main upload folder for easy serving
    
    save_pitch_data(times, f0, voiced_flag, voiced_probs, sr, method, data_path)
    generate_pitch_plot(times, f0, plot_path)
    
    # Return metadata
    # We prefix pitch_data_filename with 'pitch/' so it can be served or referenced cleanly if needed
    return {
        "pitch_analysis_status": "Ready",
        "pitch_data_filename": f"pitch/{data_filename}",
        "pitch_plot_filename": plot_filename,
        "pitch_analysis_method": method,
        "pitch_fmin": float(fmin),
        "pitch_fmax": float(fmax),
        "pitch_median": median_f0,
        "pitch_min": min_f0,
        "pitch_max": max_f0,
        "pitch_voiced_percentage": voiced_percentage
    }
