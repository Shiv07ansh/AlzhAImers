import os
import random
import librosa
import soundfile as sf
from pathlib import Path
from tqdm import tqdm

# === CONFIG === #
SAMPLE_RATE = 16000
TARGET_DURATION = 1.0  # seconds
SAMPLES_PER_CLIP = int(SAMPLE_RATE * TARGET_DURATION)

from pathlib import Path

# Your base path
BASE_DIR = Path(r"<path>")

POS_DIR = BASE_DIR / "positive"
NEG_DIR = BASE_DIR / "negative"

OUTPUT_BASE = Path(r"<path>")
OUTPUT_POS_DIR = OUTPUT_BASE / "positive"
OUTPUT_NEG_DIR = OUTPUT_BASE / "negative"

MAX_SAMPLES_PER_CLASS = 1500           # Cap for balance

# === Ensure Output Dirs Exist === #
Path(OUTPUT_POS_DIR).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_NEG_DIR).mkdir(parents=True, exist_ok=True)


def extract_chunks(y, sr, chunk_len, stride):
    """
    Extract fixed-length chunks (1s) from a long waveform.
    """
    chunks = []
    for start in range(0, len(y) - chunk_len + 1, stride):
        chunks.append(y[start:start + chunk_len])
    return chunks


def process_positive_files():
    print(f"🔹 Processing positive class from: {POS_DIR}")
    count = 0
    for filename in tqdm(os.listdir(POS_DIR)):
        if not filename.endswith(".wav"):
            continue

        path = os.path.join(POS_DIR, filename)
        y, sr = librosa.load(path, sr=SAMPLE_RATE)

        if len(y) < SAMPLES_PER_CLIP:
            y = librosa.util.fix_length(y, SAMPLES_PER_CLIP)
        elif len(y) > SAMPLES_PER_CLIP:
            y = y[:SAMPLES_PER_CLIP]

        outname = f"pos_{count:04d}.wav"
        sf.write(os.path.join(OUTPUT_POS_DIR, outname), y, sr)
        count += 1

        if count >= MAX_SAMPLES_PER_CLASS:
            break


def process_negative_files():
    print(f"🔸 Processing negative class from: {NEG_DIR}")
    chunk_pool = []

    for filename in tqdm(os.listdir(NEG_DIR)):
        if not filename.endswith(".wav"):
            continue

        path = os.path.join(NEG_DIR, filename)
        y, sr = librosa.load(path, sr=SAMPLE_RATE)

        chunks = extract_chunks(y, sr, SAMPLES_PER_CLIP, stride=SAMPLES_PER_CLIP)
        chunk_pool.extend(chunks)

    print(f"🔸 Total negative chunks extracted: {len(chunk_pool)}")

    random.shuffle(chunk_pool)
    chunk_pool = chunk_pool[:MAX_SAMPLES_PER_CLASS]

    for i, chunk in enumerate(chunk_pool):
        outname = f"neg_{i:04d}.wav"
        sf.write(os.path.join(OUTPUT_NEG_DIR, outname), chunk, SAMPLE_RATE)


if __name__ == "__main__":
    print(" Starting dataset balancing and trimming...")
    process_positive_files()
    process_negative_files()
    print(" Dataset prepared successfully.")