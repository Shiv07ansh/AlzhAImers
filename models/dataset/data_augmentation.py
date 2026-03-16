"""
MP3 Audio Augmentation Script
==============================
Applies the following augmentations to every .mp3 in a target folder:
  1. White noise addition       (SNR 5 dB  → _white_noise_5db)
  2. White noise addition       (SNR 10 dB → _white_noise_10db)
  3. Background noise addition  (SNR 5 dB  → _bg_noise_5db)
  4. Background noise addition  (SNR 10 dB → _bg_noise_10db)
  5. Time stretch – slow        (0.9×      → _time_stretch_0_9)
  6. Time stretch – fast        (1.1×      → _time_stretch_1_1)
  7. Pitch shift up             (+1 semi   → _pitch_up_1)
  8. Pitch shift down           (−1 semi   → _pitch_down_1)
  9. Dynamic range scaling               → _dynamic_range_scaled

Requirements:
    pip install librosa soundfile numpy

Usage:
    python augment_mp3.py <folder_path>
    python augment_mp3.py .           # current directory
"""

import os
import sys
import numpy as np
import librosa
import soundfile as sf


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _snr_noise(signal: np.ndarray, snr_db: float, noise: np.ndarray | None = None) -> np.ndarray:
    """
    Mix `signal` with noise at a given SNR (dB).
    If `noise` is None, white Gaussian noise is generated.
    If `noise` is provided (background) it is looped / trimmed to match signal length.
    """
    signal_power = np.mean(signal ** 2)

    if noise is None:
        # White noise
        raw_noise = np.random.randn(len(signal))
    else:
        # Loop background noise to match signal length
        reps = int(np.ceil(len(signal) / len(noise)))
        raw_noise = np.tile(noise, reps)[: len(signal)]

    noise_power = np.mean(raw_noise ** 2)
    if noise_power == 0:
        return signal.copy()

    # Scale noise so that signal_power / scaled_noise_power == 10^(snr_db/10)
    desired_noise_power = signal_power / (10 ** (snr_db / 10))
    scale = np.sqrt(desired_noise_power / noise_power)
    return signal + scale * raw_noise


def _background_noise(length: int, sr: int) -> np.ndarray:
    """
    Synthesise a simple background noise texture:
    pink-ish noise (white noise passed through a crude 1/f filter).
    """
    white = np.random.randn(length)
    # Simple pink approximation: low-pass IIR cascade
    b = np.array([0.049922035, -0.095993537, 0.050612699, -0.004408786])
    a = np.array([1, -2.494956002, 2.017265875, -0.522189400])
    from scipy.signal import lfilter  # optional, falls back gracefully
    try:
        pink = lfilter(b, a, white)
    except Exception:
        pink = white  # fallback to white if scipy missing
    return pink.astype(np.float32)


def _dynamic_range_scale(signal: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    """
    Scale the signal so its RMS matches `target_db` dBFS,
    then apply soft-knee compression (ratio 4:1 above threshold).
    """
    rms = np.sqrt(np.mean(signal ** 2))
    if rms == 0:
        return signal.copy()
    # Normalise to target RMS
    target_rms = 10 ** (target_db / 20.0)
    scaled = signal * (target_rms / rms)
    # Soft compression: squash peaks beyond threshold
    threshold = 0.5
    ratio = 4.0
    out = scaled.copy()
    mask = np.abs(out) > threshold
    excess = np.abs(out[mask]) - threshold
    compressed_excess = excess / ratio
    out[mask] = np.sign(out[mask]) * (threshold + compressed_excess)
    return out


# ──────────────────────────────────────────────
# Core augmentation dispatcher
# ──────────────────────────────────────────────

AUGMENTATIONS = [
    ("white_noise_5db",       lambda y, sr: _snr_noise(y, snr_db=5)),
    ("white_noise_10db",      lambda y, sr: _snr_noise(y, snr_db=10)),
    ("bg_noise_5db",          lambda y, sr: _snr_noise(y, snr_db=5,  noise=_background_noise(len(y), sr))),
    ("bg_noise_10db",         lambda y, sr: _snr_noise(y, snr_db=10, noise=_background_noise(len(y), sr))),
    ("time_stretch_0_9",      lambda y, sr: librosa.effects.time_stretch(y, rate=0.9)),
    ("time_stretch_1_1",      lambda y, sr: librosa.effects.time_stretch(y, rate=1.1)),
    ("pitch_up_1",            lambda y, sr: librosa.effects.pitch_shift(y, sr=sr, n_steps=1)),
    ("pitch_down_1",          lambda y, sr: librosa.effects.pitch_shift(y, sr=sr, n_steps=-1)),
    ("dynamic_range_scaled",  lambda y, sr: _dynamic_range_scale(y)),
]


def augment_file(input_path: str, output_dir: str) -> None:
    """Load one MP3, apply every augmentation, save each result."""
    basename   = os.path.splitext(os.path.basename(input_path))[0]
    print(f"\n{'─'*60}")
    print(f" Source : {input_path}")

    try:
        y, sr = librosa.load(input_path, sr=None, mono=True)
    except Exception as exc:
        print(f"  ✗  LOAD FAILED  → {exc}")
        return

    print(f"     Loaded  | sr={sr} Hz | samples={len(y)} | duration={len(y)/sr:.2f}s")

    for tag, fn in AUGMENTATIONS:
        out_name = f"{basename}_{tag}.wav"          # Save as WAV (lossless)
        out_path = os.path.join(output_dir, out_name)
        try:
            augmented = fn(y, sr)
            # Clip to [-1, 1] to prevent clipping artefacts on export
            augmented = np.clip(augmented, -1.0, 1.0)
            sf.write(out_path, augmented, sr)
            print(f"  ✔  {tag:<28} → {out_name}")
        except Exception as exc:
            print(f"  ✗  {tag:<28} → FAILED: {exc}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python augment_mp3.py <folder_path>")
        sys.exit(1)

    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print(f"Error: '{folder}' is not a valid directory.")
        sys.exit(1)

    mp3_files = sorted(
        f for f in os.listdir(folder) if f.lower().endswith(".mp3")
    )

    if not mp3_files:
        print(f"No .mp3 files found in '{folder}'.")
        sys.exit(0)

    # Output goes into a sub-folder called 'augmented'
    output_dir = os.path.join(folder, "augmented")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Found {len(mp3_files)} MP3 file(s) in '{folder}'")
    print(f"Output directory: {output_dir}")
    print(f"Augmentations per file: {len(AUGMENTATIONS)}")

    for fname in mp3_files:
        augment_file(os.path.join(folder, fname), output_dir)

    print(f"\n{'═'*60}")
    print(f"Done — augmented files saved to: {output_dir}")


if __name__ == "__main__":
    main()

