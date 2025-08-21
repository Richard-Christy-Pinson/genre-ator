from flask import Flask, render_template, request, send_file
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor
import librosa
import torch
from pydub import AudioSegment
import os

# Initialize Flask app
app = Flask(__name__)

# Genre mapping and equalizer presets
genre_mapping = {
    0: "Electronic",
    1: "Rock",
    2: "Punk",
    3: "Experimental",
    4: "Hip-Hop",
    5: "Folk",
    6: "Chiptune / Glitch",
    7: "Instrumental",
    8: "Pop",
    9: "International",
}

equalizer_presets = {
    "Electronic": [5, 4, 3, 2, 1, 0, -1, -2, -3, -4],
    "Rock": [3, 2, 1, 0, -1, -2, -3, -4, -5, -6],
    "Punk": [2, 3, 2, 1, 0, -1, -2, -3, -4, -5],
    "Experimental": [1, 0, -1, -2, -3, -4, -5, -6, -7, -8],
    "Hip-Hop": [4, 3, 2, 1, 0, -1, -2, -3, -4, -5],
    "Folk": [0, 1, 2, 3, 4, 3, 2, 1, 0, -1],
    "Chiptune / Glitch": [-2, -1, 0, 1, 2, 3, 4, 3, 2, 1],
    "Instrumental": [1, 2, 3, 4, 3, 2, 1, 0, -1, -2],
    "Pop": [3, 4, 3, 2, 1, 0, -1, -2, -3, -4],
    "International": [2, 1, 0, -1, -2, -3, -4, -5, -6, -7],
}

# Load model and feature extractor
genre_classifying_model = Wav2Vec2ForSequenceClassification.from_pretrained("gastonduault/music-classifier")
feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/wav2vec2-large")

# Function to preprocess audio for prediction
def preprocess_audio(audio_path):
    audio_array, sampling_rate = librosa.load(audio_path, sr=16000)
    return feature_extractor(audio_array, sampling_rate=16000, return_tensors="pt", padding=True)

# Function to apply equalizer preset
def apply_equalizer(audio_path, preset):
    audio = AudioSegment.from_file(audio_path)
    bands = len(preset)
    for i in range(bands):
        audio = audio.apply_gain_stereo(preset[i], preset[i])
    return audio

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    if 'audio_file' not in request.files:
        return "No file uploaded", 400

    # Save uploaded file
    file = request.files['audio_file']
    input_path = os.path.join("uploads", file.filename)
    file.save(input_path)

    # Preprocess audio and predict genre
    inputs = preprocess_audio(input_path)  # Converting the audio into a format the model can process
    with torch.no_grad():
        logits = genre_classifying_model(**inputs).logits
        predicted_class = torch.argmax(logits, dim=-1).item()   # predicted_class will have values like 0,1,2,3,4,5....
    predicted_genre = genre_mapping[predicted_class]

    # Apply equalizer preset
    if predicted_genre in equalizer_presets:
        preset = equalizer_presets[predicted_genre]
        equalized_audio = apply_equalizer(input_path, preset)
        output_path = os.path.join("outputs", "equalized_" + file.filename)
        equalized_audio.export(output_path, format="wav")
        return send_file(output_path, as_attachment=True)
    else:
        return "No preset available for this genre.", 400

if __name__ == '__main__':
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    app.run(debug=True)
