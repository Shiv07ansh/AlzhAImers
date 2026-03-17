# MedReminder — Setup & Integration Guide

---

## Prerequisites

### Hardware Required
- ESP32-S3 development board
- I2S MEMS microphone (e.g. INMP441)
- SSD1306 OLED display (128×64, I2C)
- DS3231 RTC module
- HC-SR04 ultrasonic sensor
- Hall effect sensor (e.g. A3144 or similar)
- Passive buzzer
- LED + resistor
- SD card module (SPI)
- MicroSD card

### Software Required
- Arduino IDE **1.8.19** (not 2.x — TFLite Micro libraries have known compatibility issues with Arduino 2.x on ESP32)
- ESP32 board support package via Boards Manager: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
- Select board: **ESP32S3 Dev Module**

### Required Libraries (install via Library Manager unless noted)
- `Adafruit SSD1306`
- `Adafruit GFX Library`
- `DS3231` (by Makuna)
- `SD` (built-in)
- `arduinoFFT` by Enrique Condes
- `tflm_esp32` (install manually from GitHub)
- Your Edge Impulse KWS library (exported from Edge Impulse, installed manually — see KWS section below)

---

## Pin Configuration

Before uploading, verify all pins in the code match your physical wiring. The defaults are set in `sensors.h` and `kws.h`.

**`sensors.h` — change these to match your wiring:**

```cpp
#define PIN_I2C_SDA   21    // OLED + RTC shared I2C bus
#define PIN_I2C_SCL   22
#define PIN_BUZZER    15
#define PIN_LED       2
#define PIN_TRIG      25    // HC-SR04 trigger
#define PIN_ECHO      26    // HC-SR04 echo
#define PIN_HALL      34    // hall sensor (INPUT_PULLUP, active LOW = lid closed)
```

**`kws.h` — I2S microphone pins:**

```cpp
#define KWS_I2S_BCK_PIN   27
#define KWS_I2S_WS_PIN    33
#define KWS_I2S_DATA_PIN  32
```

**SD card** is wired directly in `MedReminder.ino`:

```cpp
#define SD_CS   5
#define SD_SCK  18
#define SD_MISO 19
#define SD_MOSI 23
```

---

## Credentials Setup

Open `credentials.h` and fill in all values before uploading. This file is never uploaded to any repository — add it to `.gitignore` immediately.

```cpp
#define WIFI_SSID       "your_network_name"
#define WIFI_PASS       "your_network_password"

#define SMTP_SERVER     "smtp.gmail.com"
#define SMTP_PORT       465
#define EMAIL_FROM      "your_device_email@gmail.com"
#define EMAIL_TO        "caregiver@example.com"
#define EMAIL_USER_B64  "base64_encoded_email"
#define EMAIL_PASS_B64  "base64_encoded_app_password"

#define DASHBOARD_URL   "https://your-server.example.com/api/log"
```

**Encoding your email credentials:**

Gmail requires an App Password, not your main password. Go to Google Account → Security → 2-Step Verification → App Passwords, generate one, then encode both your email address and the app password in base64.

On Linux/Mac:
```bash
echo -n "your@email.com" | base64
echo -n "your_app_password" | base64
```

On Windows:
```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your@email.com"))
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your_app_password"))
```

Paste the output strings into `EMAIL_USER_B64` and `EMAIL_PASS_B64`.

---

## Calibrating the Ultrasonic Sensor

The ultrasonic sensor determines whether a hand is inside the medicine box. It compares the measured distance against a baseline — the distance to the bottom of the empty box.

In `sensors.h`:

```cpp
constexpr float D_EMPTY_MM       = 150.0f;   // TODO: measure your box
constexpr float HAND_THRESHOLD_MM = D_EMPTY_MM - 10.0f;
```

To calibrate, place the sensor above your empty medicine box, run the sketch, and read the distance printed to Serial during `STATE_AWAIT_HAND`. Update `D_EMPTY_MM` to that value. The threshold is set 10mm closer — any reading shorter than that is considered a hand present. Adjust the margin if you get false positives or missed detections.

---

## Preparing Your Model Files

This section covers everything that needs to happen between training a model and including it in this sketch. These are the steps most commonly responsible for crashes, OOM failures, and silent inference errors on ESP32.

### Converting a `.tflite` file to a C header

The standard tool is `xxd`:

```bash
xxd -i slu_model_int8.tflite > slu_model_int8.h
```

On Windows, `xxd` is not available by default. Use `certutil` instead:

```powershell
certutil -encodehex -f slu_model_int8.tflite slu_model_int8.h 4
```

Note: `xxd` outputs a `.cc`-style C array. Some guides tell you to name the output `.cc` — rename it to `.h` and include it normally. The file extension does not affect compilation, but `.h` is consistent with Arduino project conventions and avoids confusion.

The raw output from `xxd` looks like this:

```cpp
unsigned char slu_model_int8_tflite[] = {
  0x1c, 0x00, 0x00, 0x00, 0x54, 0x46, 0x4c, 0x33, ...
};
unsigned int slu_model_int8_tflite_len = 764321;
```

Do not use this directly. Apply every modification below before including it in the sketch.

---

### Modification 1 — Add `const` to both declarations

```cpp
// Before
unsigned char slu_model_int8_tflite[] = { ... };
unsigned int  slu_model_int8_tflite_len = 764321;

// After
const unsigned char slu_model_int8_tflite[] = { ... };
const unsigned int  slu_model_int8_tflite_len = 764321;
```

Without `const`, the compiler treats both as mutable data and copies the entire model array into SRAM at runtime. A typical SLU model is several hundred kilobytes. The ESP32-S3 has approximately 512KB of SRAM. The copy will exhaust it before `setup()` finishes and the board will crash silently or fail to boot entirely.

With `const`, the compiler knows the data never changes and leaves it mapped in Flash (up to 16MB on most ESP32-S3 modules). SRAM is preserved for the tensor arena, ring buffer, FFT buffers, and stack.

This is the single most common reason TFLite sketches crash on first boot with no useful error message.

---

### Modification 2 — Add `alignas(8)` for alignment safety

```cpp
// Before
const unsigned char slu_model_int8_tflite[] = { ... };

// After
alignas(8) const unsigned char slu_model_int8_tflite[] = { ... };
```

TFLite Micro reads the model array with 4-byte and 8-byte aligned memory accesses internally. If the array starts at a misaligned Flash address, the ESP32 throws a hardware load/store alignment exception and the sketch crashes inside `tflite::GetModel()` or `AllocateTensors()` — usually with a `LoadStoreAlignment` or `IllegalInstruction` panic in the Serial output.

`alignas(8)` guarantees the array starts on an 8-byte boundary. If you still see alignment faults after adding `alignas(8)`, try `alignas(16)` — some model architectures require stricter alignment.

---

### Modification 3 — Rename the array variable

`xxd` generates the variable name from the input filename by replacing all non-alphanumeric characters with underscores. If your file is named `slu_model_int8.tflite`, the array will be called `slu_model_int8_tflite`. If the path had directories, the name gets longer and uglier.

Rename it to something clean that matches what `slu.h` expects:

```cpp
// xxd generated
alignas(8) const unsigned char slu_model_int8_tflite[] = { ... };

// rename to match slu.h
alignas(8) const unsigned char slu_model_int8[] = { ... };
```

The name you use here must exactly match the name passed to `tflite::GetModel()` in `slu.h`:

```cpp
slu_model_ptr = tflite::GetModel(slu_model_int8);  // must match array name
```

---

### Modification 4 — Add `#pragma once`

`xxd` does not add include guards. Without one, including the header more than once causes a duplicate symbol error. Add `#pragma once` as the very first line:

```cpp
#pragma once

alignas(8) const unsigned char slu_model_int8[] = {
  0x1c, 0x00, 0x00, 0x00, ...
};
const unsigned int slu_model_int8_len = 764321;
```

---

### Note on `PROGMEM`

You may see older ESP32 examples using:

```cpp
const unsigned char model_tflite[] PROGMEM = { ... };
```

`PROGMEM` is an AVR-specific directive for forcing data into program memory on chips where data and program memory are physically separate (e.g. Arduino Uno). On ESP32, `const` alone is sufficient — the compiler already keeps const data in Flash. Adding `PROGMEM` on ESP32 either has no effect or causes a warning. Do not use it here.

---

### Final form of `slu_model_int8.h`

After all modifications:

```cpp
#pragma once

alignas(8) const unsigned char slu_model_int8[] = {
  0x1c, 0x00, 0x00, 0x00, 0x54, 0x46, 0x4c, 0x33,
  // ... all bytes ...
};
const unsigned int slu_model_int8_len = 764321;
```

---

## Input Quantization — Verify Before Assuming

This is one of the most common sources of silent inference failure. The input tensor type depends entirely on how the model was converted, and it may not be what you expect.

There are two common quantization paths and they produce different input types:

**Dynamic range quantization** (the default in many Colab notebooks):

```python
converter.optimizations = [tf.lite.Optimize.DEFAULT]
# No representative_dataset provided
```

This quantizes weights only. The input tensor remains `float32`. If you write `int8` values into a `float32` input tensor the model runs without error but produces completely wrong outputs — there is no type-checking at runtime.

**Full integer quantization** (what this project requires):

```python
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type  = tf.int8   # or tf.uint8
converter.inference_output_type = tf.int8   # or tf.uint8
```

This quantizes weights and activations including the input and output tensors.

To verify what your model actually expects, uncomment the tensor print block in `initSLU()` and read the Serial output on first boot:

```
[SLU] Input  type:  9   ← 9 = kTfLiteInt8
[SLU] Input  quant: scale=0.003921  zp=-128
[SLU] Output quant: scale=0.003921  zp=-128
```

Type codes: `1` = float32, `9` = int8, `3` = uint8.

If your input type is `1` (float32), either reconvert the model with full integer quantization, or change the input copy in `slu.h` from `data.int8` to `data.f` and skip the quantization step in `_computeMFE()`. The KWS and SLU models may have been converted differently — verify both independently.

---

## Op Resolver — What to Use and What to Avoid

### Never use `AllOpsResolver`

```cpp
// Do NOT do this
tflite::AllOpsResolver resolver;
```

`AllOpsResolver` loads every op in the TFLite Micro library including training and backpropagation ops that are never needed for inference. On ESP32 this causes SRAM overflow during resolver construction, before inference even begins. The sketch will hang or crash in `setup()` with no meaningful output.

### Always use `MicroMutableOpResolver`

```cpp
static tflite::MicroMutableOpResolver<10> resolver;
resolver.AddConv2D();
resolver.AddDepthwiseConv2D();
resolver.AddFullyConnected();
resolver.AddSoftmax();
// etc.
```

The template parameter is the maximum number of ops. Set it to exactly the number of `Add` calls below it — not more, not less.

### Identifying which ops your model needs

The most reliable way is to let the runtime tell you. Run the sketch with a placeholder resolver (zero ops) and read the error output:

```
Didn't find op for builtin opcode 'CONV_2D'
Didn't find op for builtin opcode 'SOFTMAX'
```

Add each reported op to the resolver and rerun until `AllocateTensors()` succeeds. Netron can give you a visual overview of the graph but it does not always reflect the exact internal op names that TFLite Micro uses — the runtime error messages are the authoritative source.

KWS and SLU require separate resolver instances with their own op sets. They are declared as `static` locals inside `initKWS()` and `initSLU()` respectively so they do not interfere with each other.

---

## Bidirectional Layers — Known Incompatibility

TFLite Micro does not include the `ReverseV2` kernel, which is required internally by bidirectional LSTM and GRU layers. If your SLU model contains a `Bidirectional` wrapper, it will fail at runtime with an op-resolution error even if `ReverseV2` is not visible as a named op in Netron.

The fix must be applied before conversion. Replace any bidirectional layers with stacked unidirectional layers in the Keras model definition, retrain, then convert. There is no workaround at the TFLite Micro level — the kernel simply does not exist.

---

## Plugging In the KWS Model

The KWS model is deployed as an Edge Impulse Arduino library, which handles the `.tflite` conversion, C array generation, and op resolution internally. You do not run `xxd` for KWS.

1. In your Edge Impulse project, go to **Deployment → Arduino library → Build**
2. Download the `.zip` file
3. In Arduino IDE: **Sketch → Include Library → Add .ZIP Library**
4. In `kws.h`, uncomment and update the include:
   ```cpp
   #include <KWS-alzhAImers_inferencing.h>
   ```
5. Replace the placeholder buffer size:
   ```cpp
   // Before
   static float kws_flat[16000];
   // After
   static float kws_flat[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE];
   ```
6. Update the positive label to match your Edge Impulse project's label name for valid commands:
   ```cpp
   #define KWS_POSITIVE_LABEL    "command"   // confirm this matches your project
   ```
7. In `runKWSInference()`, remove the MVP stub `return false` and uncomment the `signal_t` → `run_classifier()` → result block
8. Tune `KWS_CONFIDENCE_THR` — start at `0.75f` and adjust based on false positive rate in your environment

---

## Plugging In the SLU Model

1. Convert your `.tflite` file to a C header using `xxd` and apply all modifications from the Model Files section above
2. Place `slu_model_int8.h` in the sketch folder alongside `MedReminder.ino`
3. In `slu.h`, uncomment:
   ```cpp
   #include "slu_model_int8.h"
   ```
4. In `initSLU()`, uncomment the model load block:
   ```cpp
   slu_model_ptr = tflite::GetModel(slu_model_int8);
   if (!slu_model_ptr || slu_model_ptr->version() != TFLITE_SCHEMA_VERSION) {
       Serial.println("[SLU] Model invalid");
       return;
   }
   ```
5. Uncomment the interpreter and `AllocateTensors()` block
6. Uncomment the tensor print block, upload, and read the Serial output:
   ```
   [SLU] Input  type:  9
   [SLU] Input  quant: scale=0.003921  zp=-128
   [SLU] Output quant: scale=0.003921  zp=-128
   ```
7. Copy the printed scale and zero_point values into `MODEL PARAMS` in `slu.h`:
   ```cpp
   constexpr float SLU_INP_SCALE      = 0.003921f;
   constexpr int   SLU_INP_ZERO_POINT = -128;
   constexpr float SLU_OUT_SCALE      = 0.003921f;
   constexpr int   SLU_OUT_ZERO_POINT = -128;
   ```
8. Re-comment the tensor print block after capturing the values
9. Remove the MVP stub in `runSLUInference()`:
   ```cpp
   // Remove these lines:
   if (!slu_interpreter) {
       *outIntentIdx = INTENT_IRRELEVANT;
       *outScore = 0.0f;
       return true;
   }
   ```
10. Tune `SLU_CONFIDENCE_THR` — start at `0.60f`

---

## Arena Size Tuning

If `AllocateTensors()` fails, increase `SLU_ARENA_SIZE` in `slu.h` in 8KB increments until it succeeds:

```cpp
constexpr int SLU_ARENA_SIZE = 64 * 1024;   // try 72, 80, 96 if this fails
```

Once it succeeds, read the arena usage from Serial:

```
[SLU] Arena used: 41832 / 65536 bytes
```

You can then reduce `SLU_ARENA_SIZE` to `arena_used` rounded up to the nearest 8KB, plus a small safety margin of 4–8KB. Keeping the arena as small as possible leaves more heap available for WiFi buffers and other runtime allocations.

---

## Things Left To Implement

The following features have stub implementations in the current code and are ready to be built out:

**TTS audio playback** — all trigger functions (`triggerConfirmTaken`, `triggerAskTime`, etc.) contain `TODO: TTS` comments. The I2S bus is currently used exclusively for microphone input. TTS output requires either a second I2S port wired to a DAC/amplifier, or switching the I2S bus between input and output modes between KWS runs.

**GSM SMS** — `triggerNotifySOS()` sends email but not SMS. A GSM modem (e.g. SIM800L) on a UART port would allow SMS to a caregiver number without WiFi dependency, which is more reliable for an emergency alert.

**Medicine config from SD** — `triggerAskMedDetails()` and `triggerAskSchedule()` currently return hardcoded strings. A JSON config file on the SD card would allow the medicine name, dose, and schedule to be updated without reflashing.

**Production TLS** — `connectivity.h` uses `setInsecure()` for HTTPS and SMTP connections, which skips certificate verification. For production, replace with `setCACert()` using the root certificate of your mail provider.

**`D_EMPTY_MM` auto-calibration** — currently a hardcoded constant in `sensors.h`. Could be measured automatically on first boot with the box empty and stored to flash or the SD card.