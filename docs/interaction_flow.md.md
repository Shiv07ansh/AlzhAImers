
![System Architecture](methodology_block.jpg)
## System Output by Event

| Event               | OLED Output        | Audio (Speaker) | Buzzer      |
| ------------------- | ------------------ | --------------- | ----------- |
| Idle                | Clock + Next Alarm | —               | —           |
| Reminder Active     | Take [Med] now     | It's time       | Long Beep   |
| Wake Word Detected  | Listening...       | —               | —           |
| Intent Detected     | You said: [intent] | Snoozing        | —           |
| Confirmed Dose      | Medicine Taken     | Confirmed       | Single Beep |
| Error / Missed Dose | Error              | —               | 3 Beeps     |
![System Architecture](system_architecture.png)