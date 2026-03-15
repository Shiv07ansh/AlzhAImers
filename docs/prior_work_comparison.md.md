# How This System Differs From Prior Work

Prior systems surveyed fall into four categories and their limitations:

**Button-based confirmation** [9][10][22] — require patient to 
press button, unsuitable for cognitive impairment

**Cloud-dependent systems** [11][30][31] — require stable internet, 
no local fallback

**Heavy hardware** [14][32] — Raspberry Pi based, high cost and 
power, not battery-operable

**No intelligent interaction** [13][23][27] — basic scheduling 
only, no voice, no behavioral modeling

This system is the first to combine:
- On-device conversational AI (KWS + SLU) on MCU-class hardware
- Physical multi-sensor adherence verification
- Offline-first operation with opportunistic cloud sync
- Sub-$15 BOM

For the full systematic literature review comparing 14 prior systems
across methodology, results, and limitations → docs/paper.md
