from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor
import librosa
import torch

# Check if CUDA (GPU) is available, otherwise use CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device for genre identification: {device}")  # Check if GPU is being used

# Load model and feature extractor
model = Wav2Vec2ForSequenceClassification.from_pretrained("gastonduault/music-classifier")
feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/wav2vec2-large")

# Move model to GPU (if available)
model.to(device)


# Function for preprocessing audio for prediction
def preprocess_audio(audio_path):
    audio_array, sampling_rate = librosa.load(audio_path, sr=16000)
    return feature_extractor(audio_array, sampling_rate=16000, return_tensors="pt", padding=True)


def find_genre(audio_path, genre_mapping):
    try:
        # Preprocess the audio
        inputs = preprocess_audio(audio_path)

        if inputs is None:
            raise ValueError("Invalid input after preprocessing")

        print("Processing audio...")

        # Move input tensors to the same device as the model (GPU if available)
        inputs = {key: val.to(device) for key, val in inputs.items()}

        # Predict genre
        with torch.no_grad():
            logits = model(**inputs).logits
            predicted_class = torch.argmax(logits, dim=-1).item()

        predicted_genre = genre_mapping.get(predicted_class, "error")
        return {'genre_id': predicted_class + 1, 'genre': predicted_genre}

    except Exception as e:
        print(f"Error processing audio: {e}")
        return "error"



# equalizer_presets = {
#     "Electronic": [5, 4, 3, 2, 1, 0, -1, -2, -3, -4],
#     "Rock": [3, 2, 1, 0, -1, -2, -3, -4, -5, -6],
#     "Punk": [2, 3, 2, 1, 0, -1, -2, -3, -4, -5],
#     "Experimental": [1, 0, -1, -2, -3, -4, -5, -6, -7, -8],
#     "Hip-Hop": [-10,-10, 2, 1, 0, -1, -2, -3, -4, -5],
#     "Folk": [0, 1, 2, 3, 4, 3, 2, 1, 0, -1],
#     "Chiptune / Glitch": [-2, -1, 0, 1, 2, 3, 4, 3, 2, 1],
#     "Instrumental": [1, 2, 3, 4, 3, 2, 1, 0, -1, -2],
#     "Pop": [3, 4, 3, 2, 1, 0, -1, -2, -3, -4],
#     "International": [2, 1, 0, -1, -2, -3, -4, -5, -6, -7],
# }

equalizer_presets = {
    1: [5, 4, 3, 2, 1, 0, -1, -2, -3, -4],
    2: [3, 2, 1, 0, -1, -2, -3, -4, -5, -6],
    3: [2, 3, 2, 1, 0, -1, -2, -3, -4, -5],
    4: [1, 0, -1, -2, -3, -4, -5, -6, -7, -8],+
    5: [-10,-10, 2, 1, 0, -1, -20, -30, -40, -5],
    6: [0, 1, 2, 3, 4, 3, 2, 1, 0, -1],
    7: [-2, -1, 0, 1, 2, 3, 4, 3, 2, 1],
    8: [1, 2, 3, 4, 3, 2, 1, 0, -1, -2],
    9: [3, 4, 3, 2, 1, 0, -1, -2, -3, -4],
    10:[2, 1, 0, -1, -2, -3, -4, -5, -6, -7],
}
