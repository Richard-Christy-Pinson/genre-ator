import os
from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio

# Constants for folder paths
INPUT_FOLDER = "splitter_input"
OUTPUT_FOLDER = "splitter_output"

# Separation functions (pass model to avoid reloading)
def separate_vocals(input_path, output_dir, model):
    separate_audio_for_source(input_path, output_dir, "vocals", model)

def separate_drums(input_path, output_dir, model):
    separate_audio_for_source(input_path, output_dir, "drums", model)

def separate_bass(input_path, output_dir, model):
    separate_audio_for_source(input_path, output_dir, "bass", model)

def separate_other(input_path, output_dir, model):
    separate_audio_for_source(input_path, output_dir, "other", model)

# Core audio separation logic
def separate_audio_for_source(input_path, output_dir, source_name, model):
    if not os.path.exists(input_path):
        print("❌ File not found:", input_path)
        return

    # Load and preprocess audio
    wav = AudioFile(input_path).read(streams=0, samplerate=model.samplerate)
    ref = wav[0]

    if ref.dim() == 1:
        ref = ref.unsqueeze(0).repeat(2, 1)  # mono to stereo
    elif ref.shape[0] == 1:
        ref = ref.repeat(2, 1)  # 1-channel to 2-channel

    wav = ref.unsqueeze(0)  # shape: [1, channels, length]

    print(f"🎧 Separating {source_name}...")
    sources = apply_model(model, wav, shifts=0, split=True, overlap=0.1)[0]

    source_index = model.sources.index(source_name)
    source = sources[source_index]

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    out_path = os.path.join(output_dir, f"{base_name}_{source_name}.wav")
    os.makedirs(output_dir, exist_ok=True)
    save_audio(source, out_path, samplerate=model.samplerate)

    print(f"✅ {source_name.capitalize()} saved to {out_path}")

# Main entry point used after file upload and dropdown selection
def handle_uploaded_file(uploaded_filename, user_choice):
    input_path = os.path.join(INPUT_FOLDER, uploaded_filename)
    output_path = OUTPUT_FOLDER

    # Load model once
    model = get_model(name="htdemucs").cuda()  # Use GPU


    # Use dropdown value to select separation
    if user_choice == "vocals":
        separate_vocals(input_path, output_path, model)
    elif user_choice == "drums":
        separate_drums(input_path, output_path, model)
    elif user_choice == "bass":
        separate_bass(input_path, output_path, model)
    elif user_choice == "other":
        separate_other(input_path, output_path, model)
    else:
        print("❌ Invalid source selected.")
