# Limitations and Future Work

This document honestly describes what the system does not do well, 
why, and what would need to change to fix it. The open research 
questions here informed the direction of ongoing work.

---

## Current Limitations

### 1. Speaker Generalisation
The KWS and SLU models were trained primarily on a single speaker's 
voice. Performance degrades meaningfully on unseen speakers, 
regional accents, and non-native pronunciations. This is the core 
unresolved problem.

KWS achieves 97.2% on trained voice. Performance on unseen speakers 
has not been formally benchmarked but degrades noticeably in 
informal testing. SLU faces the same issue with linguistic 
variation.

This limits real-world deployment to environments where the device 
can be personalised to a specific user — it is not a 
general-purpose solution yet.

### 2. Acoustic Adaptability
The firmware does not adapt dynamically to changing acoustic 
conditions. Background noise from television, music, or 
conversation temporarily elevates the KWS false positive rate. 
The current mitigation is a software noise gate (RMS threshold) 
but this is a fixed threshold, not adaptive.

### 3. Sensor Alignment Sensitivity
The hall-effect and ultrasonic sensors are sensitive to physical 
placement. Minor misalignment of the neodymium magnet relative to 
the A3144 sensor causes unreliable lid detection. Similarly, 
ultrasonic readings vary with atypical pillbox geometries or if 
the sensor is not flush-mounted.

Workaround used: hardware jig for positioning, median filter over 
5 consecutive ultrasonic readings (hand detected only if 3 of 5 
below threshold). But this is fragile across different box designs.

### 4. Single Language and Accent
The SLU tokenizer and training data are English-only and skew 
toward one accent. This excludes the majority of the target 
population in India and other non-English speaking contexts where 
medication non-adherence is most acute.

### 5. No Real-World Trial Data Yet
The results (97.2% KWS, 95% SLU) are from controlled bench-top 
evaluation. A 7-day continuous multi-user trial is planned but 
not yet completed. Real-world false positive rates, edge case 
failure modes, and user experience data are pending.

### 6. Model Accuracy Ceiling on Constrained Hardware
Fitting more accurate models within the ESP32-S3's SRAM budget 
(320KB usable after firmware) is an unsolved problem. Current 
architecture accepts 1-2% accuracy degradation from quantization 
and from architectural simplification to meet memory constraints. 
Neural architecture search for ultra-constrained inference targets 
is an active research area this work surfaces but does not resolve.

---

## Future Work

### Near Term
- Formal benchmarking of KWS/SLU accuracy across multiple speakers 
  and accents
- 7-day continuous user trial with adherence logging and 
  subjective satisfaction surveys
- Adaptive noise threshold replacing fixed RMS gate

### Medium Term
1. **Accent and language-agnostic training** — multilingual corpora 
   and data augmentation to expand SLU generalisability across 
   Indian regional languages and accents

2. **Adaptive thresholding and noise suppression** — on-device 
   noise estimation or simple beamforming to maintain accuracy 
   in challenging acoustic environments

3. **Sensor fusion enhancements** — weight sensor or camera-based 
   pill-count verification as additional confirmation layer to 
   reduce dependence on physical alignment

### Long Term
4. **Neural architecture search for constrained inference** — 
   systematic search for model architectures that maximise 
   classification accuracy within fixed SRAM and latency budgets 
   on MCU-class hardware. This is the core open research question 
   this work surfaces.

5. **Personalised scheduling via reinforcement learning** — 
   dynamically adjust reminder timing based on individual 
   adherence patterns and daily routines learned over time

6. **Multilingual deployment** — extend to Hindi, Tamil, Bengali 
   and other languages prevalent in the primary target population

7. **Solar-powered and ultra-low-cost variants** — optimise for 
   under-resourced settings where even $15 BOM is a barrier
   
   
## Modular Accessibility Adaptations

The system is designed to be adjusted for different 
user needs without firmware changes beyond config.h:

| User Need            |                Adaptation                             |
|----------------------|-------------------------------------------------------|
| Hearing impairment   | Increase speaker volume, larger display               |
| Visual impairment    | TTS carries full interaction, no display needed       |
| Motor impairment     | Larger pillbox opening, adjusted ultrasonic threshold |
| Cognitive impairment | Simplified OLED messages, slower TTS speed            | 
| No WiFi              | Email disabled, local logging only via HTTP server    |
| No caregiver         | Logging only, no notifications                        |