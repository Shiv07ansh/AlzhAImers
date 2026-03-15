# Interaction Flow

![interaction](methodology_block.jpg)

This document describes the complete user journey through the 
system — from alarm trigger to outcome — including what the 
user sees, hears, and does at each step, and what the system 
does internally.

---

## System Output by Event

| Event               | OLED Output        | Audio (Speaker) | Buzzer      |
| ------------------- | ------------------ | --------------- | ----------- |
| Idle                | Clock + Next Alarm | —               | —           |
| Reminder Active     | Take [Med] now     | It's time       | Long Beep   |
| Wake Word Detected  | Listening...       | —               | —           |
| Intent Detected     | You said: [intent] | Snoozing        | —           |
| Confirmed Dose      | Medicine Taken     | Confirmed       | Single Beep |
| Error / Missed Dose | Error              | —               | 3 Beeps     |

---

## Primary Flow — Successful Medicine Taken
```
┌─────────────────────────────────────────────────────────────┐
│ 1. ALARM TRIGGER                                            │
│    RTC reaches nextAlarmTime                                │
│    → Buzzer activates                                       │
│    → OLED displays: "Time to take your medicine"            │
│    → Speaker plays pre-recorded TTS prompt                  │
│    → System enters IDLE, KWS listening                      │
└─────────────────────┬───────────────────────────────────────┘
                      │ User approaches device
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. VOICE DETECTION (KWS)                                    │
│    KWS continuously monitors audio stream                   │
│    → User speaks (any medicine-related phrase)              │
│    → KWS confidence exceeds threshold                       │
│    → System transitions to AWAIT_SLU                        │
│    → OLED displays: "Listening..."                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ ~1s audio captured
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. INTENT CLASSIFICATION (SLU)                              │
│    SLU classifies captured audio                            │
│    → Intent: confirm_taken                                  │
│       (user said "yes", "I took it", "good", etc.)          │
│    → OLED displays: "Please open your medicine box"         │
│    → System transitions to AWAIT_LID                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ User opens pillbox
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. LID DETECTION (Hall Effect)                              │
│    A3144 Hall sensor detects magnet distance increase       │
│    → lid_open = true                                        │
│    → OLED displays: "Please take your medicine"             │
│    → System transitions to AWAIT_HAND                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ User reaches into box
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. HAND PRESENCE DETECTION (Ultrasonic)                     │
│    HC-SR04 measures distance < d_threshold                  │
│    → hand_present = true                                    │
│    → All three confirmations received                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ All conditions met
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. CONFIRMATION AND LOGGING                                 │
│    → Dose logged with timestamp to local storage (CSV)      │
│    → Email sent to caregiver: "Medicine taken confirmed"    │
│    → OLED displays: "Medicine taken. Well done!"            │
│    → Speaker plays confirmation TTS                         │
│    → Buzzer deactivates                                     │
│    → System resets to IDLE                                  │
│    → nextAlarmTime updated to next scheduled dose           │
└─────────────────────────────────────────────────────────────┘
```

---

## Alternate Flows

### User Denies Taking Medicine
```
Step 3 → Intent: deny_taken
         ("no", "I didn't", "forgot")
→ OLED: "Reminder rescheduled"
→ TTS: "I'll remind you again shortly"
→ Alarm rescheduled: nextAlarmTime += 5 minutes
→ Reset to IDLE
→ After 3 retries: missed-dose notification to caregiver
```

### User Asks to Snooze
```
Step 3 → Intent: remind_later
         ("snooze", "remind me in 30 minutes", "later")
→ SLU extracts delay parameter from utterance
→ nextAlarmTime += extracted delay
→ OLED: "Reminder postponed"
→ TTS: "I'll remind you in [X] minutes"
→ Reset to IDLE
```

### User Asks Which Medicine
```
Step 3 → Intent: ask_med_details
         ("which medicine do I take?", "what is this for?")
→ System reads from medicineRegistry keyed by alarm time
→ OLED displays: medicine name + dosage
→ TTS reads out: "You need to take [medicine] — [dosage]"
→ Flow continues — alarm still active
→ KWS resumes listening for confirm/deny
```

### User Asks for Schedule
```
Step 3 → Intent: ask_schedule
         ("when is my next dose?", "what time?")
→ System reads reminderQueue head
→ OLED displays next scheduled dose time
→ TTS reads out next dose time
→ Flow continues — alarm still active
```

### User Asks Current Time
```
Step 3 → Intent: ask_time
         ("what time is it?")
→ RTC lookup
→ OLED displays current time
→ TTS reads out current time
→ Flow continues — alarm still active
```

### Emergency SOS
```
Any point → Intent: notify_sos
            ("help", "emergency", "I need a doctor")
→ System requires two successive SOS detections 
  within 2 seconds (prevents accidental trigger)
→ BYPASSES all sensor checks entirely
→ Email sent to emergency contact with:
  - Timestamp
  - Device ID
  - Alert type: SOS
→ Optional: SMS via GSM module (SIM800L)
→ Local audible alarm activates
→ TTS: "Emergency alert sent"
→ Reset to IDLE after confirmation
```

### Irrelevant Input
```
Step 3 → Intent: irrelevant
         (out-of-scope phrases, low confidence)
→ Confidence below threshold
→ System does nothing
→ OLED: "Sorry, I didn't understand"
→ KWS resumes listening
→ Alarm still active
```

---

## Timeout Behaviour

Every state has a 5-second timeout that resets to IDLE:

| State | Timeout Condition | Result |
|-------|------------------|--------|
| AWAIT_SLU | No intent classified in 5s | Reset to IDLE |
| AWAIT_LID | Lid not opened in 5s | Dose not confirmed, IDLE |
| AWAIT_HAND | Hand not detected in 5s | Dose not confirmed, IDLE |

Timeouts in AWAIT_LID and AWAIT_HAND do not log a missed dose — 
they simply reset. A missed dose is only logged after the 
full alarm escalation sequence (3 unacknowledged reminders) 
has completed.

---

## Alarm Escalation Sequence
```
Alarm fires → unacknowledged for 30s
→ Retry 1: nextAlarmTime += 5 minutes
→ Retry 2: nextAlarmTime += 5 minutes  
→ Retry 3: nextAlarmTime += 5 minutes
→ After 3 retries: log missed dose + 
  send missed-dose notification to caregiver
→ Resume normal schedule
```

Maximum 3 retries. Only one active reminder at a time — 
alarmDue, snoozed, and completed flags prevent overlap.

---