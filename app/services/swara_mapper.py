import os
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 12-semitone relative mapping to approximate Carnatic Swaras
# Tolerance is applied per frame later.
SWARA_MAPPING = {
    0: "S",
    1: "R1",
    2: "R2", # Can also be G1
    3: "G2", # Can also be R3
    4: "G3",
    5: "M1",
    6: "M2",
    7: "P",
    8: "D1",
    9: "D2", # Can also be N1
    10: "N2", # Can also be D3
    11: "N3"
}

# Base frequencies for octave 3
# C3 is ~130.81 Hz
BASE_FREQUENCIES = {
    "C": 130.81,
    "C#": 138.59,
    "D": 146.83,
    "D#": 155.56,
    "E": 164.81,
    "F": 174.61,
    "F#": 185.00,
    "G": 196.00,
    "G#": 207.65,
    "A": 220.00,
    "A#": 233.08,
    "B": 246.94
}

def get_tonic_frequency(shruti: str) -> float:
    """Returns the base frequency (octave 3) for the given shruti."""
    shruti_upper = shruti.upper()
    return BASE_FREQUENCIES.get(shruti_upper, BASE_FREQUENCIES["C"])

def frequency_to_cents(f0: float, tonic_frequency: float) -> float:
    """Calculate cents distance from tonic."""
    if f0 <= 0 or tonic_frequency <= 0:
        return 0.0
    return 1200.0 * math.log2(f0 / tonic_frequency)

def map_pitch_to_swara(cents: float, tolerance: float = 40.0) -> dict:
    """
    Map cents relative to tonic to a swara label.
    Returns a dict with swara label, octave relative to tonic, and deviation.
    """
    # Find relative semitone position (0 to 11) within an octave
    cents_in_octave = cents % 1200
    octave = int(cents // 1200)
    
    # Negative octave correction for proper modulo
    if cents < 0 and cents_in_octave != 0:
        cents_in_octave = 1200 + cents_in_octave
        
    semitone_index = round(cents_in_octave / 100.0) % 12
    exact_cents = semitone_index * 100
    
    # Calculate shortest distance (accounting for circular nature of octave)
    deviation = cents_in_octave - exact_cents
    if deviation > 600:
        deviation -= 1200
    elif deviation < -600:
        deviation += 1200
        
    # Check if within tolerance
    if abs(deviation) <= tolerance:
        return {
            "swara": SWARA_MAPPING[semitone_index],
            "octave": octave,
            "deviation_cents": round(deviation, 2)
        }
    else:
        # Falls outside tolerance, return uncertain but keep closest label
        return {
            "swara": f"~{SWARA_MAPPING[semitone_index]}",
            "octave": octave,
            "deviation_cents": round(deviation, 2)
        }

def analyze_swaras_for_lesson(lesson, upload_folder: str) -> dict:
    """
    Reads Phase 6 pitch JSON, normalizes to tonic, calculates swaras,
    saves new Phase 7 JSON, and generates visualization.
    """
    if not lesson.pitch_data_filename:
        raise ValueError("Missing Phase 6 pitch JSON")
        
    pitch_json_path = os.path.join(upload_folder, lesson.pitch_data_filename)
    if not os.path.exists(pitch_json_path):
        raise FileNotFoundError(f"Pitch JSON file not found: {pitch_json_path}")
        
    with open(pitch_json_path, 'r') as f:
        pitch_data = json.load(f)
        
    tonic_freq = get_tonic_frequency(lesson.shruti)
    
    times = pitch_data.get('times', [])
    f0s = pitch_data.get('f0', [])
    voiced_flags = pitch_data.get('voiced_flag', [])
    
    frames = []
    total_frames = len(times)
    voiced_frames = 0
    mapped_frames = 0
    
    for i in range(total_frames):
        t = times[i]
        f0 = f0s[i] if i < len(f0s) else None
        
        if f0 is not None and f0 > 0:
            voiced_frames += 1
            cents = frequency_to_cents(f0, tonic_freq)
            swara_info = map_pitch_to_swara(cents, tolerance=40.0)
            
            if not swara_info["swara"].startswith("~"):
                mapped_frames += 1
                
            frames.append({
                "time": t,
                "frequency": f0,
                "cents_from_tonic": round(cents, 2),
                "swara": swara_info["swara"],
                "octave": swara_info["octave"]
            })
        else:
            frames.append({
                "time": t,
                "frequency": None,
                "cents_from_tonic": None,
                "swara": None,
                "octave": None
            })
            
    if voiced_frames > 0:
        swara_voiced_percentage = (mapped_frames / voiced_frames) * 100.0
    else:
        swara_voiced_percentage = 0.0
        
    if mapped_frames == 0:
        return {
            "swara_analysis_status": "Failed",
            "swara_analysis_method": "12-semitone relative mapping",
            "tonic_frequency": tonic_freq,
            "swara_voiced_percentage": 0.0
        }
    
    # Save Swara JSON
    audio_basename = os.path.splitext(lesson.reference_audio_filename)[0]
    swara_json_filename = f"{audio_basename}_swara.json"
    swara_json_path = os.path.join(upload_folder, swara_json_filename)
    
    swara_json_data = {
        "tonic": lesson.shruti,
        "tonic_frequency": tonic_freq,
        "analysis_sample_rate": pitch_data.get("analysis_sample_rate", 22050),
        "frames": frames
    }
    
    with open(swara_json_path, 'w') as f:
        json.dump(swara_json_data, f, indent=4)
        
    # Generate Plot
    swara_plot_filename = f"{audio_basename}_swara_plot.png"
    swara_plot_path = os.path.join(upload_folder, swara_plot_filename)
    
    generate_swara_plot(frames, swara_plot_path, lesson.shruti)
    
    return {
        "swara_analysis_status": "Ready",
        "swara_data_filename": swara_json_filename,
        "swara_plot_filename": swara_plot_filename,
        "swara_analysis_method": "12-semitone relative mapping",
        "tonic_frequency": tonic_freq,
        "swara_voiced_percentage": swara_voiced_percentage
    }

def generate_swara_plot(frames, output_path, shruti):
    """Generates a visualization of the swara contour."""
    times = []
    cents = []
    
    import numpy as np
    
    for f in frames:
        times.append(f["time"])
        if f["cents_from_tonic"] is not None:
            cents.append(f["cents_from_tonic"])
        else:
            cents.append(np.nan)
            
    plt.figure(figsize=(10, 4), facecolor='#2D140F')
    ax = plt.axes()
    ax.set_facecolor('#2D140F')
    
    # Plot contour
    plt.plot(times, cents, color='#FFD700', linewidth=1.5, alpha=0.8)
    
    # Style axes
    ax.spines['bottom'].set_color('#8B7355')
    ax.spines['top'].set_color('none') 
    ax.spines['right'].set_color('none')
    ax.spines['left'].set_color('#8B7355')
    ax.tick_params(axis='x', colors='#FDF5E6')
    ax.tick_params(axis='y', colors='#FDF5E6')
    
    plt.xlabel('Time (s)', color='#FDF5E6', fontsize=10)
    plt.ylabel(f'Relative Pitch (cents from {shruti})', color='#FDF5E6', fontsize=10)
    plt.title(f'Swara Contour (Tonic: {shruti})', color='#FFD700', fontsize=12)
    
    # Draw horizontal lines for semitones
    valid_cents = [c for c in cents if not np.isnan(c)]
    min_cents = min(valid_cents) if valid_cents else -1200
    max_cents = max(valid_cents) if valid_cents else 1200
    min_oct = int(min_cents // 1200)
    max_oct = int(max_cents // 1200) + 1
    
    for octv in range(min_oct, max_oct):
        for semitone, label in SWARA_MAPPING.items():
            y_val = (octv * 1200) + (semitone * 100)
            if min_cents - 100 <= y_val <= max_cents + 100:
                ax.axhline(y_val, color='#8B7355', linestyle=':', linewidth=0.5, alpha=0.3)
                if semitone == 0 or semitone == 7: # Highlight S and P
                    ax.axhline(y_val, color='#8B7355', linestyle='-', linewidth=0.8, alpha=0.5)
                # Label y-axis at right side
                ax.text(times[-1] if times else 0, y_val, f" {label}", color='#FDF5E6', 
                        verticalalignment='center', fontsize=8, alpha=0.6)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='#2D140F', edgecolor='none')
    plt.close()
