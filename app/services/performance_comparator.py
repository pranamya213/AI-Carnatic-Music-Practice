import os
import json
import numpy as np
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

from app.services.audio_processor import load_audio
from app.services.pitch_analyzer import extract_pitch_contour
from app.services.swara_mapper import get_tonic_frequency, frequency_to_cents, map_pitch_to_swara

def simple_dtw(s1, s2):
    n, m = len(s1), len(s2)
    dtw_matrix = np.full((n+1, m+1), np.inf)
    dtw_matrix[0, 0] = 0
    
    traceback = np.zeros((n+1, m+1, 2), dtype=int)
    
    for i in range(1, n+1):
        for j in range(1, m+1):
            # Calculate cost
            v1 = s1[i-1]
            v2 = s2[j-1]
            
            if np.isnan(v1) and np.isnan(v2):
                cost = 0.0
            elif np.isnan(v1) or np.isnan(v2):
                cost = 1000.0 # High penalty for voiced/unvoiced mismatch
            else:
                cost = abs(v1 - v2)
                
            choices = [
                dtw_matrix[i-1, j] + cost,
                dtw_matrix[i, j-1] + cost,
                dtw_matrix[i-1, j-1] + cost * 1.5
            ]
            idx = np.argmin(choices)
            dtw_matrix[i, j] = choices[idx]
            
            if idx == 0: traceback[i, j] = [i-1, j]
            elif idx == 1: traceback[i, j] = [i, j-1]
            else: traceback[i, j] = [i-1, j-1]
            
    # Traceback
    path = []
    i, j = n, m
    while i > 0 and j > 0:
        path.append((i-1, j-1))
        i, j = traceback[i, j]
    path.reverse()
    return path

def compare_performances(lesson, attempt, upload_folder, student_shruti):
    # 1. Load Teacher Swara JSON
    if not lesson.swara_data_filename:
        raise ValueError("Teacher Swara analysis is missing. Teacher must analyze swaras first.")
        
    teacher_json_path = os.path.join(upload_folder, lesson.swara_data_filename)
    if not os.path.exists(teacher_json_path):
        raise FileNotFoundError(f"Teacher Swara JSON not found: {teacher_json_path}")
        
    with open(teacher_json_path, 'r') as f:
        teacher_data = json.load(f)
        
    teacher_frames = teacher_data.get('frames', [])
    if not teacher_frames:
        raise ValueError("Teacher Swara data is empty.")
        
    # 2. Extract Student Pitch and map swaras
    audio_path = os.path.join(upload_folder, 'practice', attempt.practice_audio_filename)
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Practice audio not found: {audio_path}")
        
    y, sr, orig_sr, duration, channels = load_audio(audio_path, target_sr=22050)
    times, f0s, voiced_flag, voiced_probs = extract_pitch_contour(y, sr)
    
    student_tonic_freq = get_tonic_frequency(student_shruti)
    
    student_frames = []
    for i in range(len(times)):
        t = times[i]
        f0 = f0s[i] if i < len(f0s) else None
        
        if f0 is not None and f0 > 0 and not np.isnan(f0):
            cents = frequency_to_cents(f0, student_tonic_freq)
            swara_info = map_pitch_to_swara(cents, tolerance=40.0)
            student_frames.append({
                "time": t,
                "frequency": f0,
                "cents_from_tonic": cents,
                "swara": swara_info["swara"],
                "octave": swara_info["octave"]
            })
        else:
            student_frames.append({
                "time": t,
                "frequency": None,
                "cents_from_tonic": None,
                "swara": None,
                "octave": None
            })
            
    # 3. Align sequences using DTW
    # Extract cents sequences, handling NaNs
    teacher_cents = [f.get('cents_from_tonic') for f in teacher_frames]
    teacher_cents = np.array([c if c is not None else np.nan for c in teacher_cents])
    
    student_cents = [f.get('cents_from_tonic') for f in student_frames]
    student_cents = np.array([c if c is not None else np.nan for c in student_cents])
    
    path = simple_dtw(teacher_cents, student_cents)
    
    # 4. Calculate metrics
    deviations = []
    matched_swara_frames = 0
    compared_swara_frames = 0
    
    alignment_data = []
    
    for i, j in path:
        t_frame = teacher_frames[i]
        s_frame = student_frames[j]
        
        t_cents = t_frame.get('cents_from_tonic')
        s_cents = s_frame.get('cents_from_tonic')
        
        t_swara = t_frame.get('swara')
        s_swara = s_frame.get('swara')
        
        diff = None
        if t_cents is not None and s_cents is not None:
            diff = s_cents - t_cents
            deviations.append(abs(diff))
            
            # Compare swaras
            if t_swara and not t_swara.startswith('~') and s_swara and not s_swara.startswith('~'):
                compared_swara_frames += 1
                if t_swara == s_swara:
                    matched_swara_frames += 1
        
        alignment_data.append({
            "teacher_time": t_frame['time'],
            "student_time": s_frame['time'],
            "teacher_swara": t_swara,
            "student_swara": s_swara,
            "teacher_relative_pitch": t_cents,
            "student_relative_pitch": s_cents,
            "pitch_difference_cents": diff
        })
        
    swara_match_percentage = (matched_swara_frames / compared_swara_frames * 100.0) if compared_swara_frames > 0 else 0.0
    mean_deviation = float(np.mean(deviations)) if deviations else 0.0
    median_deviation = float(np.median(deviations)) if deviations else 0.0
    
    # 5. Store JSON
    comparison_dir = os.path.join(upload_folder, 'practice', 'comparison')
    os.makedirs(comparison_dir, exist_ok=True)
    
    base_filename = f"comparison_attempt_{attempt.id}"
    data_filename = f"{base_filename}.json"
    plot_filename = f"{base_filename}.png"
    
    data_path = os.path.join(comparison_dir, data_filename)
    plot_path = os.path.join(comparison_dir, plot_filename)
    
    out_data = {
        "method": "Dynamic Time Warping (NumPy)",
        "teacher_lesson_id": lesson.id,
        "practice_attempt_id": attempt.id,
        "teacher_tonic_frequency": teacher_data.get("tonic_frequency"),
        "student_tonic_frequency": student_tonic_freq,
        "mean_pitch_deviation_cents": mean_deviation,
        "median_pitch_deviation_cents": median_deviation,
        "swara_match_percentage": swara_match_percentage,
        "alignment": alignment_data
    }
    
    with open(data_path, 'w') as f:
        json.dump(out_data, f, indent=4)
        
    # 6. Generate Plot
    generate_comparison_plot(alignment_data, plot_path)
    
    return {
        "comparison_status": "Ready",
        "comparison_data_filename": f"comparison/{data_filename}",
        "comparison_plot_filename": f"comparison/{plot_filename}",
        "swara_match_percentage": swara_match_percentage,
        "mean_pitch_deviation_cents": mean_deviation,
        "median_pitch_deviation_cents": median_deviation,
        "comparison_method": "DTW",
        "student_tonic_frequency": student_tonic_freq
    }

def generate_comparison_plot(alignment_data, output_path):
    times = []
    t_cents_plot = []
    s_cents_plot = []
    
    for row in alignment_data:
        times.append(row['teacher_time']) # Plotting against teacher time
        t_c = row['teacher_relative_pitch']
        s_c = row['student_relative_pitch']
        t_cents_plot.append(t_c if t_c is not None else np.nan)
        s_cents_plot.append(s_c if s_c is not None else np.nan)
        
    plt.figure(figsize=(10, 4), facecolor='#2D140F')
    ax = plt.axes()
    ax.set_facecolor('#2D140F')
    
    plt.plot(times, t_cents_plot, color='#FFD700', linewidth=2, alpha=0.9, label="Teacher")
    plt.plot(times, s_cents_plot, color='#00FFFF', linewidth=1.5, alpha=0.8, label="Student")
    
    ax.spines['bottom'].set_color('#8B7355')
    ax.spines['top'].set_color('none') 
    ax.spines['right'].set_color('none')
    ax.spines['left'].set_color('#8B7355')
    ax.tick_params(axis='x', colors='#FDF5E6')
    ax.tick_params(axis='y', colors='#FDF5E6')
    
    plt.xlabel('Aligned Time (s)', color='#FDF5E6', fontsize=10)
    plt.ylabel('Relative Pitch (cents)', color='#FDF5E6', fontsize=10)
    plt.title('Teacher vs Student Normalized Pitch', color='#FFD700', fontsize=12)
    plt.legend(facecolor='#2D140F', edgecolor='#8B7355', labelcolor='#FDF5E6')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='#2D140F', edgecolor='none')
    plt.close()
