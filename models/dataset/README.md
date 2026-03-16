# Dataset

Shared audio dataset used for both KWS and SLU model training.

KWS uses binary labels (command vs noise).
SLU uses the same command audio labeled across 8 intent categories.

---

## KWS Dataset

**Total samples (after preprocessing):** ~2500
**Class balance:** capped at 1500 per class

| Class              | Contents                                                                             | Count |
| ------------------ | ------------------------------------------------------------------------------------ | ----- |
| Positive (command) | All medicine-related utterances across all 7 SLU intent categories except irrelevant | ~1500 |
| Negative (noise)   | Ambient noise, silence, unrelated speech, ESC-50 clips                               | ~1500 |

Note: the positive class for KWS contains the same audio used 
to train SLU intent classes — the difference is label granularity. 
KWS collapses all intent categories into one positive class. 
SLU differentiates between them.

---

## SLU Dataset

**Total classes:** 8  
**Samples per class:** approximately 180-190  
**Total samples:** approximately 1440-1520

| Intent Class | Approx Samples |
|-------------|----------------|
| confirm_taken | ~180-190 |
| deny_taken | ~180-190 |
| remind_later | ~180-190 |
| ask_med_details | ~180-190 |
| ask_schedule | ~180-190 |
| ask_time | ~180-190 |
| notify_sos | ~180-190 |
| irrelevant | ~180-190 |

---

## Recording Conditions

- Format: 16kHz, 16-bit mono .wav
- Duration per sample: 1 second (enforced by preprocessing)
- Primary speaker: single speaker (author)
- Language: English
- Environment: indoor, not formally characterised
- Collection period: approximately 2023

Negative samples supplemented with:
- Google Speech Commands dataset (background/noise clips)
- ESC-50 environmental noise clips
- Manually recorded silence and ambient samples

---

## Preprocessing Pipeline

**Step 1 — data_preprocessing.py**

Normalises raw collected audio into uniform 1-second clips 
before augmentation or training.

For positive samples:
- Loads each .wav at 16kHz
- Trims to 1 second if longer, pads with zeros if shorter
- Caps at 1500 samples for class balance

For negative samples:
- Loads long-form noise recordings
- Chunks into 1-second clips using stride equal to chunk length
  (no overlap)
- Pools all chunks, shuffles randomly
- Caps at 1500 samples for class balance

Result: balanced dataset of 1500 positive + 1500 negative 
1-second clips, ready for augmentation.

**Step 2 — data_augmentation.py**

Applies augmentation to expand the preprocessed dataset.
See data_augmentation.py for full implementation.

Techniques:
- Additive noise (SNR 5dB and 10dB)
- Time stretching (0.9× and 1.1×)
- Pitch shifting (±1 semitone)

Result: approximately 6× increase in total samples.

---

## Dataset Split

- Training: 80%
- Test: 20%
- Stratified to maintain class balance

---

## Known Limitations

- **Single speaker** — entire dataset recorded by one person.
  Primary cause of accuracy degradation on unseen speakers.
- **Exact original counts not recorded** — preprocessing caps
  at 1500/class so final counts are known, but original raw
  collection sizes were not formally logged.
- **No accent or voice diversity** — generalisation to different
  voices, accents, and languages is an open problem.
  See LIMITATIONS_AND_FUTURE_WORK.md.
- **English only** — excludes the majority of the target 
  deployment population in India.
