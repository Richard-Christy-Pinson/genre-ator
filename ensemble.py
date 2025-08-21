# 32 Hz (Sub-bass), 64 Hz (Bass), 125 Hz (Lower midrange), 250 Hz (Midrange), 500 Hz (Upper midrange),
# 1 kHz (Low treble), 2 kHz (Treble), 4 kHz (Presence), 8 kHz (Brilliance), 16 kHz (Air)

# 0: [4, 3, 2, 1, 0, -1, -2, -3, -4, -5],  # Electronic
# 1: [3, 2, 1, 0, -1, -2, -3, -4, -5, -6],  # Rock
# 2: [2, 3, 2, 1, 0, -1, -2, -3, -4, -5],  # Punk
# 3: [1, 0, -1, -2, -3, -4, -5, -6, -7, -8],  # Experimental
# 4: [6, 5, 3, 2, 1, 0, -1, -2, -3, -4],  # Hip-Hop (Boosted bass & presence, reduced mids)
# 5: [0, 1, 2, 3, 4, 3, 2, 1, 0, -1],  # Folk
# 6: [-2, -1, 0, 1, 2, 3, 4, 3, 2, 1],  # Chiptune/Glitch
# 7: [1, 2, 3, 4, 3, 2, 1, 0, -1, -2],  # Instrumental
# 8: [3, 4, 3, 2, 1, 0, -1, -2, -3, -4],  # Pop
# 9: [2, 1, 0, -1, -2, -3, -4, -5, -6, -7],  # International

# Define the 10 frequency bands
FREQ_BANDS = [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000),
              (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000), (16000, 20000)]

import torch
from pydub import AudioSegment
import db_connection
import numpy as np
import librosa

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device for ensemble: {device}")

connection2 = db_connection.get_db_conn()


def analyze_audio_levels(audio_path):
    print("Analyzing the audio levels.")
    y, sr = librosa.load(audio_path, sr=44100)

    y_tensor = torch.tensor(y, device=device)
    window = torch.hann_window(4096, device=device)  # Use Hann window to reduce spectral leakage
    S = torch.abs(torch.stft(
        y_tensor.to(device),  # Ensure input is on GPU
        n_fft=4096,
        return_complex=True,
        window=torch.hann_window(4096, device=device)  # Move window to GPU
    ))

    freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)

    max_amp = torch.max(S) + 1e-6
    eq_levels = []

    for band in FREQ_BANDS:
        idx = np.where((freqs >= band[0]) & (freqs < band[1]))[0]

        if len(idx) > 0:
            magnitude = torch.max(S[idx, :])
            db_level = librosa.amplitude_to_db([magnitude.cpu().numpy()], ref=max_amp.cpu().numpy())[0]
        else:
            db_level = -80  # Default to silence

        eq_levels.append(float(db_level))

    return eq_levels


def compare_eq_levels(audio_path, genre_id):
    print("Compare Eq called.")
    if genre_id not in DEFAULT_EQ_LEVELS:
        raise ValueError("Invalid genre ID")

    current_levels = analyze_audio_levels(audio_path)
    default_levels = DEFAULT_EQ_LEVELS[genre_id]
    differences = [current - default for current, default in zip(current_levels, default_levels)]

    return {
        "current_levels": current_levels,
        "default_levels": default_levels,
        "differences": differences
    }


def apply_equalizer(audio_path, differences, output_path):
    print("Applying Equalizer.")
    audio = AudioSegment.from_file(audio_path)

    for i, (low, high) in enumerate(FREQ_BANDS):
        gain = differences[i]
        filtered_band = audio.low_pass_filter(high).high_pass_filter(low)
        filtered_band = filtered_band.apply_gain(gain)
        audio = audio.overlay(filtered_band)

    print("Gains applied.")
    print("Saving the processed file...")
    audio.export(output_path, format="wav")
    print(f"Processed audio saved to: {output_path}")


def ensemble_eq(audio_path, genre_id, output_path):
    try:
        print("Ensemble Eq called.")
        connection2.reconnect()
        cursor = connection2.cursor(dictionary=True)
        cursor.execute('''SELECT sub_bass, bass, lower_midrange, midrange, upper_midrange, low_treble, treble, 
        presence, brilliance, air FROM eq_levels WHERE genre_id = %s''', (genre_id,))
        eq_preset = cursor.fetchone()

        eq_values = list(eq_preset.values())
        global DEFAULT_EQ_LEVELS
        DEFAULT_EQ_LEVELS = {genre_id: eq_values}

        result = compare_eq_levels(audio_path, genre_id)
        apply_equalizer(audio_path, result["differences"], output_path)
        return 1
    except Exception as e:
        print(f"Error in ensemble_eq: {e}")
        return 0


if __name__ == "__main__":
    # Example usage
    audio_file = 'E:\\Main Project\\FlaskEq\\static\\audios\\original\\50_Cent_In_Da_Club.wav'
    genre_id = 4  # Hip-Hop
    result = compare_eq_levels(audio_file, genre_id)

    print("Current EQ Levels (dB):", result["current_levels"])
    print("Default EQ Levels (dB):", result["default_levels"])
    print("Difference (dB):", result["differences"])

    output_file = "E:\\Main Project\\FlaskEq\\static\\audios\\rendered\\50paisa.wav"
    apply_equalizer(audio_file, result["differences"], output_file)
