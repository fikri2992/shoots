# Phone Camera Companion — Conversation Export

> Historical research only. Its Gemini Live and continuous Scene guidance is parked outside the hackathon submission and current roadmap. Do not treat this document as current implementation direction unless the user explicitly reopens that scope.

**Date:** 2026-08-26
**Topic:** Real-time multimodal camera companion, on-device perception, Google technologies, product design

---

## User

say i make an agent to understand surrounding with live chat like gpt-live. i need it to understand surrounding. problem is LLM multi modal takes 5 second to analyze its too long for live/realtime processes. can u find me better, faster, cheaper way to do this preferably using google tech that can achieve this under 1 sec including network overhead or on device (but midrange android device xiaomi 14T base model not pro)

---

## Assistant

# Yes—but do not run a multimodal LLM on every frame

The practical way to reach **under one second** is to split the job into two parts:

1. **A fast local perception loop** reads objects, people, movement, distance, text, and sounds.
2. **Gemini Live** handles conversation, uncertain cases, and questions that need deeper reasoning.

The phone should continuously maintain a small structured **scene state**, rather than continuously sending full camera frames to Gemini.

This matters because Gemini Live receives video as separate images at up to roughly **1 frame per second**. It is useful for conversation, but it is not fast enough to track a person, vehicle, or obstacle moving in real time. ([firebase.google.com](https://firebase.google.com/docs/ai-logic/live-api/capabilities))

---

## The system I would use

```text
Camera + microphone
        │
        ▼
Local fast models
────────────────────────────
Object detector
Object tracker
ARCore depth
OCR
Sound classifier
Optional pose detection
────────────────────────────
        │
        ▼
Compact SceneState
        │
        ├── Local rules → instant warning / answer / vibration
        │
        ├── Gemini Live → natural conversation
        │
        └── Gemini Flash-Lite → rare unknown-object checks
```

The important change is this:

```text
Bad:
camera frame → multimodal LLM → answer
every time something happens

Better:
camera frame → small local models → structured update
                                      ↓
                           LLM sees only changes
```

---

# 1. Fast local perception loop

## Object detection

Start with either:

- **MediaPipe Object Detector with EfficientDet-Lite0**
- A custom small INT8 detector through **LiteRT**
- ML Kit Object Detection for an easy first test

Google recommends EfficientDet-Lite0 as a balanced mobile detector. It uses a 320 × 320 input and recognizes the common COCO object classes. Google’s reference Pixel 6 measurements put small object detectors around 24–30 ms per run, depending on model and hardware path. Those are not Xiaomi 14T measurements, but they show that a small detector does not need several seconds. ([developers.google.com](https://developers.google.com/edge/mediapipe/solutions/vision/object_detector))

You do not need to run detection at 30 frames per second. A good starting point is:

- Camera: 30 FPS
- Object detection: 5–10 times per second
- Tracking between detections: 30 FPS

That gives you frequent new labels while keeping motion smooth.

For a simple first version, ML Kit can assign tracking IDs to detected objects. Its standard detector tracks up to five objects, which may be enough for a prototype but can be limiting in a crowded scene. ([developers.google.com](https://developers.google.com/ml-kit/vision/object-detection/android))

For a stronger version, use a LiteRT detector plus a simple IoU/Kalman tracker.

---

## Distance and position

Use **ARCore Raw Depth** for distance.

The Xiaomi 14T is listed as supporting ARCore’s Depth API. Raw Depth uses less computation than full depth processing and includes a confidence map, which helps reject poor measurements. It does not require a dedicated time-of-flight sensor. ([developers.google.com](https://developers.google.com/ar/devices))

For every tracked object:

1. Take the center region of its bounding box.
2. Read several depth pixels.
3. Remove low-confidence pixels.
4. Use the median valid distance.
5. Smooth it over the last few frames.

This gives state such as:

```json
{
  "id": 7,
  "label": "person",
  "distance_m": 1.8,
  "bearing_deg": -12,
  "motion": "approaching",
  "confidence": 0.91
}
```

You do not need an LLM to conclude that a person is approaching. Compare the current distance with recent distances.

---

## Text in the environment

Use **ML Kit Text Recognition**, but do not run it over the whole frame continuously.

Run OCR when:

- The camera becomes stable.
- A likely sign or document region appears.
- The user asks, “What does that sign say?”
- An image region has changed and remained visible for several frames.

Google notes that smaller or cropped OCR inputs can reduce processing time. ([developers.google.com](https://developers.google.com/ml-kit/vision/text-recognition/v2/android))

Store the result in the scene state:

```json
{
  "text": "EXIT",
  "object_id": 12,
  "distance_m": 3.2,
  "bearing_deg": -25
}
```

---

## Sound awareness

Use **MediaPipe Audio Classifier with YAMNet**.

It can detect sounds such as:

- Horns
- Alarms
- Knocks
- Sirens
- Dogs
- Vehicle sounds
- Glass breaking

Google’s Pixel 6 reference measurement for YAMNet is around 12 ms on CPU. It also supports asynchronous audio streaming. ([developers.google.com](https://developers.google.com/edge/mediapipe/solutions/audio/audio_classifier))

Sound should be fused with camera data:

```text
Sound: car horn, high confidence
Visual: vehicle at 8 metres, moving closer
Result: urgent local alert
```

Again, no large model needs to be involved in that immediate response.

---

## Optional person understanding

Only activate these when a person is present:

- MediaPipe Pose Landmarker
- MediaPipe Hand Landmarker
- Face detection without identity recognition
- A small action model for a limited action set

Do not run all of them continuously. Use the object detector as a gate:

```text
No person found:
    pose model off

Person found:
    run pose at 10–15 FPS on person crop
```

This cuts power use substantially.

---

# 2. Maintain a compact scene state

Instead of sending images repeatedly, keep a live internal record:

```json
{
  "timestamp_ms": 12420,
  "objects": [
    {
      "id": 7,
      "label": "person",
      "distance_m": 1.8,
      "bearing_deg": -12,
      "motion": "approaching",
      "confidence": 0.91,
      "last_seen_ms": 12420
    },
    {
      "id": 3,
      "label": "chair",
      "distance_m": 0.7,
      "bearing_deg": 24,
      "motion": "stationary",
      "confidence": 0.88,
      "last_seen_ms": 12410
    }
  ],
  "visible_text": [
    {
      "value": "EXIT",
      "bearing_deg": -25,
      "distance_m": 3.2
    }
  ],
  "sounds": [
    {
      "label": "car horn",
      "confidence": 0.83
    }
  ]
}
```

Then calculate only what changed:

```text
+ person #7 appeared 1.8 m ahead-left
~ person #7 is moving closer
+ text "EXIT" appeared on the left
- chair #3 is no longer visible
```

Send these small updates to Gemini Live. That is much faster and cheaper than sending full images at a steady rate.

It also gives the model continuity. Object `#7` remains the same person across several seconds, rather than becoming a new unnamed person in each image.

---

# 3. Use three response levels

## Level A: fully local, immediate

Use local rules for common requests and urgent events.

Examples:

- “What is directly ahead?”
- “How far is the nearest chair?”
- “Is someone approaching?”
- “Where is the exit sign?”
- “Warn me about objects closer than one metre.”
- “Did something enter the scene?”

These can be answered from the scene state without an LLM.

```text
Nearest object:
chair, 0.7 metres, slightly right

Local response:
“Chair less than one metre to your right.”
```

Use Android text-to-speech, vibration, or a short sound.

This is the only route that can reliably stay below one second even with a bad internet connection.

---

## Level B: Gemini Live receives structured state

Use the current **Gemini 3.1 Flash Live Preview** for the conversation layer. Google describes it as a low-latency live model with audio, image, video, and text input, plus streaming text or audio output. Its default thinking setting is kept low for faster responses. ([ai.google.dev](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-live-preview))

Rather than asking Gemini to inspect every frame, send:

```text
SCENE UPDATE 12.42s
person #7: 1.8m, 12 degrees left, approaching
chair #3: 0.7m, 24 degrees right, stationary
visible text: EXIT, left
sound: car horn, confidence 0.83
```

Then Gemini can answer:

> “There is a chair close to your right, and a person is approaching from ahead-left.”

The reasoning is still handled by Gemini, but the expensive image reading has already been done locally.

---

## Level C: send a cropped image only when needed

Send an image when:

- The local detector finds an unknown object.
- The user asks a broad visual question.
- Several objects overlap.
- The scene relation is unclear.
- OCR fails.
- The user asks about appearance, colour, condition, or context.

Do not send the whole camera image by default. Send the relevant crop:

```text
Unknown tracked object #14
Bounding crop: 256 × 256
Distance: 1.2m
Position: centre-left
```

While the cloud call runs, the local system can still say:

> “There is an unknown object about one metre to your left.”

When the cloud result arrives:

> “It appears to be a folded stroller.”

Bind that label to object `#14` and reuse it while the tracker keeps the same object ID.

---

# 4. Best Google stack for the Xiaomi 14T base model

The Xiaomi 14T base uses the **MediaTek Dimensity 8300-Ultra**, with MediaTek NPU 780 and 12 GB RAM. ([mi.com](https://www.mi.com/global/product/xiaomi-14t/specs/))

Google’s current LiteRT NPU support includes MediaTek Dimensity 8300 devices, including support for ahead-of-time compilation and compilation on the device. LiteRT can also fall back from NPU to GPU or CPU when needed. ([ai.google.dev](https://ai.google.dev/edge/litert/next/mediatek))

So the most useful Google tools for this phone are:

| Need | Google technology | Where it runs |
|---|---|---|
| Camera frame flow | CameraX | Device |
| Small object detector | LiteRT or MediaPipe | Device |
| Object tracking | ML Kit or custom tracker | Device |
| Distance | ARCore Raw Depth | Device |
| Text | ML Kit Text Recognition | Device |
| Sound events | MediaPipe YAMNet | Device |
| Pose and hands | MediaPipe | Device |
| Live conversation | Gemini 3.1 Flash Live | Cloud |
| Rare image checks | Gemini 2.5 Flash-Lite | Cloud |
| Spoken output | Android TTS or Gemini audio | Device/cloud |

## Do not depend on Gemini Nano for this phone

Google’s current supported-device page lists the **Xiaomi 14T Pro**, but not the base Xiaomi 14T, for its on-device Gemini Nano and ML Kit GenAI features. Therefore, I would not base this project on AICore or Gemini Nano support. ([developers.google.com](https://developers.google.com/ml-kit/genai))

LiteRT is the more dependable route because you ship and control the local models yourself.

---

# 5. LiteRT setup details that matter

## Use NPU with fallback

The LiteRT NPU API allows an accelerator order such as:

```kotlin
CompiledModel.Options(
    Accelerator.NPU,
    Accelerator.GPU,
    Accelerator.CPU
)
```

That lets a supported model use the NPU while still working when an operation cannot be placed there. Google also provides a MediaTek compatibility check for supported devices. ([ai.google.dev](https://ai.google.dev/edge/litert/next/npu))

## Avoid slow first-run compilation

On-device NPU compilation can take much longer on the first run. Google’s examples show that cached or ahead-of-time compiled models can start far faster than uncached models. ([ai.google.dev](https://ai.google.dev/edge/litert/next/npu))

Therefore:

- Load models when the app starts.
- Run one dummy inference before the live session begins.
- Cache NPU compilation output.
- Keep the model resident while the camera session is active.
- Do not unload and reload it after every interaction.

Your under-one-second goal should be measured on the **warm path**, after startup preparation.

## Reduce memory copies

LiteRT supports Android hardware buffers, allowing camera and model data to stay closer to GPU or NPU memory. Google notes that this can reduce total latency by cutting buffer copies. ([ai.google.dev](https://ai.google.dev/edge/litert/next/npu))

The intended path is:

```text
CameraX image
    ↓
hardware-backed buffer
    ↓
resize/crop
    ↓
LiteRT model
```

Avoid this path:

```text
Camera image
    ↓
Bitmap
    ↓
JPEG
    ↓
byte array
    ↓
Bitmap again
    ↓
model
```

That second path wastes time and power.

---

# 6. Realistic latency targets

These are engineering targets, not Google guarantees.

## Local visual update

| Step | Warm target |
|---|---:|
| Waiting for latest camera frame | 0–33 ms |
| Crop and resize | 2–10 ms |
| Small object detector | 25–70 ms |
| Tracking and depth fusion | 10–35 ms |
| Local rule | 1–5 ms |
| UI, sound, or vibration start | 5–30 ms |
| **Total** | **roughly 50–180 ms** |

A sensible target for the Xiaomi 14T is:

- Typical local update: **under 200 ms**
- Slow local update: **under 300 ms**
- Local spoken response start: **roughly 200–650 ms**

You will need to measure the real phone because model operator support, thermal state, camera format, and Android power policy affect the result.

---

## Cloud response from an already-known event

For a precomputed scene update:

| Step | Target |
|---|---:|
| Local scene update | 50–180 ms |
| Encode and send small text update | 5–20 ms |
| Network round trip | 40–200+ ms |
| Gemini first response chunk | about 150–500+ ms |
| **Possible total** | **roughly 300–900+ ms** |

This can stay under one second on a good connection, but there is no hard guarantee. Gemini 3.1 Flash Live is currently a preview model, and Google does not give a firm sub-second end-to-end latency promise for a mobile connection. ([ai.google.dev](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-live-preview))

For a spoken question, speech endpoint detection also adds delay.

Google’s Live API documentation suggests about 500–800 ms of silence for automatic end-of-speech detection. A hybrid setup can detect speech ending locally and immediately send `audio_stream_end`, while keeping server-side detection as a fallback. ([ai.google.dev](https://ai.google.dev/gemini-api/docs/live-api/capabilities))

So a complete spoken request may often be:

```text
speech-end detection: approximately 500 ms
network + model: approximately 250–800 ms
first spoken result: approximately 750–1,300 ms
```

Sometimes it will be below one second. It should not be treated as guaranteed.

The best user experience is a two-stage reply:

```text
0–300 ms:
local vibration or brief warning

300–1,200 ms:
natural spoken detail from Gemini
```

---

# 7. Gemini Live connection setup

For the lowest cloud delay:

1. Keep one persistent WebSocket open.
2. Use a small backend only to issue an ephemeral token.
3. Connect the Android app directly to the Gemini Live API.
4. Do not route camera and microphone data through your own application server.
5. Keep the session warm.
6. Send state changes as realtime text.
7. Send images only after a meaningful scene change or visual question.
8. Use low media resolution.
9. Keep initial answers brief.
10. Use local speech-end detection.

Google supports ephemeral tokens for direct client-to-server Live API sessions. ([ai.google.dev](https://ai.google.dev/gemini-api/docs/live-api/capabilities))

Firebase AI Logic has an Android Live API sample and may be easier for a first test. However, its current Live API layer does not expose all controls, including VAD settings, media resolution, and thinking settings. For strict latency work, direct WebSocket access gives you more control. ([firebase.google.com](https://firebase.google.com/docs/ai-logic/live-api/capabilities))

Also plan around current session limits. Google states that a session with audio and video has a shorter base limit than audio-only, although session resumption and context compression can extend ongoing use. ([ai.google.dev](https://ai.google.dev/gemini-api/docs/live-api/session-management))

Since your local system already knows the scene, you may not need to keep video input active at all. Use audio plus structured scene text most of the time.

---

# 8. Local speech recognition

Android provides an on-device speech recognizer API when the phone and installed language model support it. The app should test `isOnDeviceRecognitionAvailable()` at runtime. ([developer.android.com](https://developer.android.com/reference/android/speech/SpeechRecognizer?utm_source=chatgpt.com))

However, Google’s current ML Kit basic on-device speech language list does not include Indonesian, while its more advanced Indonesian support is limited to certain Pixel devices. For an Indonesian-language product, test the Xiaomi firmware’s own on-device speech service, but keep Gemini Live audio as the main compatible route. ([developers.google.com](https://developers.google.com/ml-kit/genai/speech-recognition/android))

A useful mixed setup is:

```text
Common fixed commands:
local command grammar or installed Android recognizer

Open conversation:
Gemini Live audio
```

Fixed commands can include:

- “What is ahead?”
- “Nearest object.”
- “Read text.”
- “Repeat.”
- “Stop.”
- “Describe the room.”
- “Is anyone nearby?”

The local command system does not need to transcribe every word perfectly. It only needs to choose among a small set of common intents.

---

# 9. Model frequency plan

| Component | Suggested rate |
|---|---:|
| Camera capture | 30 FPS |
| Basic tracking | 30 FPS |
| ARCore pose/depth | 15–30 Hz |
| Object detector | 5–10 Hz |
| Image embedding | 2–5 Hz |
| Pose model | 10–15 Hz when a person is present |
| OCR | 0.5–2 Hz or on request |
| Sound classifier | Continuous asynchronous stream |
| Scene-state updates | 4–10 Hz, only when changed |
| Images sent to Gemini | 0–1 Hz, event-based |

Do not queue old frames. CameraX supports `STRATEGY_KEEP_ONLY_LATEST`, which is appropriate here: when inference is busy, process the newest frame and discard stale ones. Google gives the same general advice for real-time ML Kit object processing. ([developers.google.com](https://developers.google.com/ml-kit/vision/object-detection/android))

For an agent understanding the present environment, a newer dropped frame is better than an older frame waiting in a queue.

---

# 10. Event routing logic

```kotlin
fun onFrame(frame: CameraFrame, timeMs: Long) {
    tracker.predict(timeMs)

    val depthFrame = arCoreDepth.latest()

    if (detectorDue(timeMs) || sceneChanged(frame)) {
        val input = frame.cropAndResize(320, 320)
        val detections = detector.run(input)
        val tracks = tracker.update(detections, timeMs)

        sceneState.updateObjects(
            tracks = tracks,
            depth = depthFrame,
            timestampMs = timeMs
        )
    }

    if (stableTextRegionAvailable(frame)) {
        sceneState.updateText(
            textRecognizer.process(selectTextCrop(frame))
        )
    }

    val changes = sceneState.changesSinceLastUpdate()

    when {
        changes.hasImmediateRisk -> {
            localAlert.speak(changes.briefWarning)
            haptics.signal(changes.riskLevel)
        }

        changes.hasUnknownObject -> {
            localAlert.speak(changes.unknownObjectWarning)
            cloudLabeler.classifyAsync(changes.unknownObjectCrop)
        }

        changes.hasMeaningfulChange -> {
            geminiLive.sendRealtimeText(changes.compactText)
        }
    }

    if (conversation.needsImageCheck()) {
        geminiLive.sendLowResolutionImage(
            selectRelevantCrop(frame)
        )
    }
}
```

The cloud call never blocks camera processing.

---

# 11. Cost

For the current Gemini 3.1 Flash Live paid tier, Google lists approximately:

- Audio input: **$0.005 per minute**
- Image/video input: **$0.002 per minute**
- Audio output: **$0.018 per minute**
- Text input: **$0.75 per million tokens**
- Text output: **$4.50 per million tokens** ([ai.google.dev](https://ai.google.dev/gemini-api/docs/pricing?hl=en))

Example for one hour:

```text
60 minutes audio input:       $0.30
60 minutes visual input:      $0.12
10 minutes spoken output:     $0.18
-----------------------------------
Approximate total:            $0.60 per active hour
```

With local event gating:

```text
10 minutes active audio:      $0.05
10 minutes visual input:      $0.02
5 minutes spoken output:      $0.09
-----------------------------------
Approximate total:            $0.16 per clock hour
```

These are list-price examples and exclude extra tool calls and large text output.

You can cut visual cost almost entirely by sending structured scene updates and only rare image crops.

For occasional unknown-object image checks, **Gemini 2.5 Flash-Lite** is Google’s lower-cost stable option, priced at about $0.10 per million image/text/video input tokens and $0.40 per million output tokens. It should be treated as an optional background check, not part of the hard real-time loop. ([ai.google.dev](https://ai.google.dev/gemini-api/docs/pricing?hl=en))

---

# 12. What about running a full VLM locally?

Google’s Gemma 3n supports text, images, and audio and is meant for mobile use. The E2B variant is around 3 GB. LiteRT-LM supports mobile CPU, GPU, and NPU execution. ([ai.google.dev](https://ai.google.dev/gemma/docs/gemma-3n))

But I would not place Gemma 3n in the continuous camera loop on the Xiaomi 14T:

- It will use far more memory and power than a small detector.
- Visual prompt processing is heavier than ordinary text generation.
- Heat will reduce performance during long camera sessions.
- Google’s published phone measurements are on higher-end Samsung devices, not the Xiaomi 14T.
- A full visual response under one second is not something I would promise on this phone.

It can still be useful as:

- An offline fallback
- A slow room-description model
- A private document reader
- A model called only after the phone becomes stationary
- A second-stage check when there is no internet

For the real-time path, several small models plus simple rules are much safer.

---

# My exact choice

For the base Xiaomi 14T, I would use:

```text
CameraX
  + LiteRT INT8 object detector
  + simple IoU/Kalman object tracker
  + ARCore Raw Depth
  + ML Kit OCR
  + MediaPipe YAMNet
  + optional MediaPipe Pose

        ↓

persistent SceneState
  + local rule engine
  + Android TTS and vibration

        ↓

direct Gemini 3.1 Flash Live WebSocket
  receiving scene changes as text
  and occasional low-resolution crops
```

Expected outcome:

- **Known object and hazard updates:** about 50–200 ms
- **Local spoken alert:** generally below one second
- **Gemini reply from existing scene state:** sometimes below one second on a good connection
- **Arbitrary cloud image reasoning:** commonly around one second or more, with no firm guarantee
- **Continuous cost:** much lower than streaming full visual understanding through a large model

The core rule is simple: **the LLM should be the agent’s reasoning and conversation layer, not its frame-by-frame visual sensor.**

---

## User

what about light, or depth or something like that for example its for phone camera companion

---

## Assistant

# Yes—light and depth should be core signals

For a **phone camera companion**, object labels are only one small part. The more useful live state is:

```text
What is the subject?
Where is it?
How far away is it?
Where is the light coming from?
Is the subject darker than the background?
Will the shot blur?
Is focus stable?
Is the camera level?
Is the background separated from the subject?
```

Almost all of that can be calculated **locally, without an LLM and without network delay**.

I would represent the scene as a live **photographic state**, not merely a list of objects:

```text
Camera
├── Exposure and light
├── Depth and geometry
├── Subject and background
├── Focus
├── Phone movement
├── Framing
└── Visual meaning
```

Gemini should receive this structured state and explain it naturally.

---

## 1. Light can be understood very quickly

There are three useful light sources:

1. Camera exposure metadata
2. Pixels from the preview
3. ARCore light estimation

### Camera metadata

Android Camera2 can report values such as:

- Exposure time
- Sensor sensitivity or ISO
- Aperture
- Focal length
- Focus distance
- Auto-exposure state
- Auto-focus state
- Auto-white-balance state
- Rolling-shutter time
- Low-light-boost state

These values come with each camera result, so reading them requires almost no extra image processing. Some fields are optional, so the app must check what the selected lens reports. ([developer.android.com](https://developer.android.com/reference/android/hardware/camera2/CaptureRequest?utm_source=chatgpt.com))

From these values, the companion can say things such as:

```text
Light level: low
Current shutter: 1/25 second
ISO: 3200
Camera movement: medium
Expected blur risk: high
Suggested action: use the main lens and hold the phone steady
```

A useful exposure estimate is:

```text
EV100 ≈ log2(aperture² / exposure_seconds) - log2(ISO / 100)
```

This is not enough by itself because the phone may apply HDR, tone mapping, and digital brightening. It should be combined with the actual preview pixels.

---

## 2. Analyze luminance, not the full-resolution frame

You do not need a vision model to understand basic exposure.

Read the Y plane from the CameraX or Camera2 YUV frame, downscale it to something like:

```text
160 × 120
```

Then calculate:

- Median brightness
- Darkest 1% and 5%
- Brightest 95% and 99%
- Percentage of clipped highlights
- Percentage of crushed shadows
- Brightness by screen region
- Subject brightness
- Background brightness
- Brightness changes over time

This should take only a few milliseconds when written efficiently.

Example state:

```json
{
  "median_luma": 0.39,
  "highlight_clip_ratio": 0.12,
  "shadow_clip_ratio": 0.03,
  "subject_luma": 0.24,
  "background_luma": 0.63
}
```

The system can immediately conclude:

```text
The subject is much darker than the background.
The window is losing highlight detail.
This is a backlit scene.
```

An approximate backlight difference can be calculated as:

```text
backlight_stops =
    log2(background_linear_luma / subject_linear_luma)
```

The brightness values should first be converted from gamma-encoded values into approximate linear values.

A rule could be:

```text
If background is more than 1.5 stops brighter than the subject:
    mark scene as backlit

If highlight clipping exceeds 8%:
    warn about lost highlight detail

If the subject is dark but highlights are safe:
    suggest positive exposure compensation

If the subject is dark and highlights are already clipped:
    suggest changing position instead of raising exposure
```

This is more useful than simply telling the user that the image is “too dark.”

---

## 3. ARCore can estimate the main light direction

ARCore has a useful feature called **Environmental HDR light estimation**.

It can return:

- Main light direction
- Main light RGB intensity
- Average scene intensity
- Ambient light represented as spherical harmonics
- RGB color correction
- An environmental HDR cube map

The estimate is available through `Frame.getLightEstimate()`. Environmental HDR works with the rear camera, not the selfie camera. ([developers.google.com](https://developers.google.com/ar/reference/java/com/google/ar/core/LightEstimate?utm_source=chatgpt.com))

This is very useful for a camera companion.

You can combine:

```text
ARCore main light direction
        +
face or body orientation
        =
how the light reaches the subject
```

For example:

```text
Main light: 58° to the subject’s right
Face direction: 12° to the camera’s left
Light-to-face angle: 70°
```

Then the companion can say:

> “The light is coming strongly from the right. Ask the person to turn slightly toward it.”

Or:

> “The strongest light is behind the subject. Move about one step left or rotate the subject.”

### Important limit

ARCore light estimation was mainly made to light virtual objects so they match the real environment. I would use it for:

- Direction
- Relative intensity
- Relative color

I would **not** treat it as a calibrated photographic light meter. Exposure advice should still come from Camera2 metadata and preview luminance.

---

## 4. Estimate light quality

You can also estimate whether the light is:

- Flat
- Directional
- Hard
- Soft
- Backlit
- Mixed
- Uneven

This does not need a large model.

### For a face

Use MediaPipe Face Landmarker or ML Kit face detection to obtain the face region and landmarks. Then compare several regions:

```text
Left cheek
Right cheek
Forehead
Nose
Eye sockets
Chin
```

Examples:

```text
Left cheek much brighter than right:
    side lighting

Forehead bright but eyes very dark:
    overhead lighting

Edges bright but face centre dark:
    backlight or rim light

Small bright region with strong local contrast:
    hard light

Slow brightness transition across the face:
    softer light
```

For a non-human subject, use subject segmentation and divide the subject mask into a grid.

ML Kit’s subject segmentation can return a foreground mask and separate subject masks. It runs through Google Play services and requires its model to be installed before first use. ([developers.google.com](https://developers.google.com/ml-kit/vision/subject-segmentation/android?utm_source=chatgpt.com))

A possible light state:

```json
{
  "direction": "upper-right",
  "direction_vector": [0.52, -0.61, -0.59],
  "contrast_ratio": 3.1,
  "softness": 0.42,
  "backlit": true,
  "mixed_light": false,
  "confidence": 0.81
}
```

The terms “hard” and “soft” will remain estimates because a single phone camera cannot always separate material texture, shadows, and lighting. The companion should expose confidence rather than acting certain.

---

## 5. The ambient light sensor is only a secondary signal

The Xiaomi 14T includes an ambient light sensor and a flicker sensor according to Xiaomi’s specifications. It also has accelerometer and gyroscope sensors. ([mi.com](https://www.mi.com/global/product/xiaomi-14t/specs/?utm_source=chatgpt.com))

Android’s standard light sensor reports illuminance in lux through `Sensor.TYPE_LIGHT`, when the manufacturer exposes it. ([developer.android.com](https://developer.android.com/develop/sensors-and-location/sensors/sensors_environment?utm_source=chatgpt.com))

However, the ambient sensor may not face the same direction as the rear camera. It may also be affected by:

- The user’s hand
- A phone case
- Screen reflections
- Sensor placement
- The user standing between the sensor and light

So use it like this:

```text
Ambient sensor:
    general room brightness prior

Camera metadata:
    actual exposure conditions

Preview luminance:
    what the camera currently sees

ARCore:
    likely light direction and relative intensity
```

Do not use ambient lux alone to decide whether the subject is properly exposed.

### Xiaomi flicker sensor

The Xiaomi specification lists a flicker sensor, but Android does not provide a common public flicker-sensor API similar to `TYPE_LIGHT`. I would enumerate all available sensors with `SensorManager.getSensorList(TYPE_ALL)` and check whether Xiaomi exposes a vendor sensor.

Treat that as an optional bonus, not a core dependency.

---

## 6. Flicker can be detected from the camera feed

Camera2 supports anti-banding modes for:

- Automatic
- 50 Hz
- 60 Hz
- Off

The camera can adjust exposure timing to reduce bands caused by lights that switch at mains frequency. ([android.googlesource.com](https://android.googlesource.com/platform/frameworks/base/%2B/master/core/java/android/hardware/camera2/CameraMetadata.java?utm_source=chatgpt.com))

Your companion can also detect flicker itself.

Use a small central or subject-focused region and record average luminance over time:

```text
L[0], L[1], L[2], ... L[n]
```

Then calculate:

- Frame-to-frame brightness variance
- Periodic brightness changes
- Horizontal rolling bands
- Difference between alternating frames

For fast flicker, 30 FPS may not identify the actual frequency correctly. A 120 FPS analysis mode would be better when supported. For ordinary operation, the system can still detect that unstable lighting exists, even if it cannot determine its exact frequency.

Possible warning:

> “This LED light is causing brightness bands. Try 1/50 or 1/100 second, or enable automatic anti-banding.”

---

# 7. Depth is very useful for a camera companion

The Xiaomi 14T is officially listed as supporting ARCore’s Depth API. ([developers.google.com](https://developers.google.com/ar/devices?utm_source=chatgpt.com))

ARCore can provide a depth image in which pixels contain distance from the camera. It can work from camera motion and does not require a dedicated time-of-flight sensor. ([developers.google.com](https://developers.google.com/ar/develop/java/depth/developer-guide?utm_source=chatgpt.com))

With depth, the companion can understand:

- Subject distance
- Background distance
- Foreground blockage
- Subject-background separation
- Available room behind the subject
- Distance to walls
- Whether a subject is too close to the lens
- Whether moving left or right would improve separation
- Whether portrait blur is likely to work well
- How much the user should move forward or backward

Example:

```json
{
  "subject_distance_m": 1.72,
  "background_distance_m": 3.85,
  "nearest_foreground_m": 0.58,
  "subject_background_gap_m": 2.13
}
```

The companion can say:

> “The subject is 1.7 metres away, but the background is only 60 centimetres behind them. Move the subject forward to get stronger separation.”

---

## 8. Use Raw Depth for measurements

ARCore offers:

- Full depth
- Raw depth
- Raw depth confidence

Raw depth is more suitable for measurements. It is sparse, so some pixels have no valid distance. Google states that Raw Depth uses roughly half the computation of the full Depth API. ([developers.google.com](https://developers.google.com/ar/develop/java/depth/raw-depth?utm_source=chatgpt.com))

For each subject, do not read one depth pixel from the middle of its bounding box. That pixel could land on:

- A hole between arms
- Hair
- The background
- A low-confidence area
- A reflective surface

Instead:

```text
1. Erode the subject mask slightly.
2. Sample perhaps 50–200 points inside it.
3. Reject zero-depth values.
4. Reject low-confidence values.
5. Calculate the median.
6. Smooth it over several updates.
```

For the background, sample a ring around the subject mask.

```text
subjectDepth =
    median(valid depth inside subject)

backgroundDepth =
    median(valid depth in outer ring)

depthSeparation =
    backgroundDepth - subjectDepth
```

This creates much more stable advice.

---

## 9. Depth has limits

ARCore depth is calculated mainly from movement. It may not yet be available when:

- The phone has not moved enough
- The environment has few visible details
- The scene is too dark
- The camera is covered
- Tracking is lost

Google documents these cases through `NotYetAvailableException`. ([developers.google.com](https://developers.google.com/ar/develop/java/depth/developer-guide?utm_source=chatgpt.com))

Depth is also less dependable on:

- Blank walls
- Glass
- Mirrors
- Shiny metal
- Water
- Very dark surfaces
- Fast-moving subjects
- Thin objects
- Long distances

Therefore the state should include confidence:

```json
{
  "distance_m": 1.72,
  "confidence": 0.84,
  "source": "arcore_raw_depth"
}
```

When confidence is poor:

```text
“The subject seems to be around two metres away.”
```

When confidence is strong:

```text
“The subject is about 1.7 metres away.”
```

---

# 10. A major camera integration choice

There are two quite different products you could make.

## Option A: companion preview

The app displays its own camera preview and gives advice, but the final photo can still be taken elsewhere or through a basic capture path.

Use:

```text
ARCore
├── camera pose
├── depth
├── light estimation
└── camera frame

MediaPipe or ML Kit
├── faces
├── subjects
└── objects
```

This is the simplest way to get both light direction and depth.

## Option B: full replacement camera app

The app must control:

- Final high-resolution capture
- RAW or DNG
- Lens switching
- Exposure
- Focus
- HDR
- Night mode
- Video recording

For this, use Camera2 as the main camera layer.

ARCore has a Shared Camera API that can work alongside Camera2. However, when ARCore is active, the app must not replace ARCore’s repeating request, and ARCore cannot use a hardware depth sensor in shared-camera mode. This makes shared-camera integration more complex than a normal Camera2 session. ([developers.google.com](https://developers.google.com/ar/reference/java/com/google/ar/core/SharedCamera?utm_source=chatgpt.com))

For a full camera product, I would use:

```text
Normal operation:
Camera2 + local image analysis

Optional spatial-assist operation:
ARCore depth and light mode

Final capture:
Camera2 exclusive capture path
```

I would not make the whole app dependent on ARCore depth being available during every high-quality capture configuration.

---

# 11. Depth fallback without ARCore

When ARCore depth is unavailable, combine several weaker signals.

### Autofocus distance

Camera2 may report `LENS_FOCUS_DISTANCE`. It is measured in inverse metres on many camera devices, but calibration quality varies and the field may be absent. ([developer.android.com](https://developer.android.com/reference/android/hardware/camera2/CaptureResult?utm_source=chatgpt.com))

Use it as:

```text
rough focus-plane distance
```

Do not treat it as an exact subject measurement.

### Face size

With a normal adult face, bounding-box size plus camera intrinsics can provide a rough distance estimate.

### Known object size

For common objects with approximately known dimensions:

- A4 document
- Credit card
- Human face
- Full human body
- Door
- Laptop screen

Distance can be estimated from:

```text
distance ≈ focal_length_pixels × real_width / observed_width_pixels
```

### Motion parallax

When the phone moves sideways, nearby objects move more across the frame than distant objects. A local feature tracker can estimate relative depth ordering without producing exact metres.

These fallbacks are useful enough for:

```text
near
medium
far

foreground
subject plane
background
```

For many composition suggestions, relative depth is all you need.

---

# 12. Phone movement gives very strong camera advice

Android devices expose accelerometer and gyroscope data. These sensors can report phone rotation, tilt, shake, and movement locally. ([developer.android.com](https://developer.android.com/develop/sensors-and-location/sensors/sensors_motion?utm_source=chatgpt.com))

This lets the companion calculate blur risk before capture.

A useful approximation is:

```text
predicted_blur_pixels
    ≈ focal_length_pixels
    × angular_speed_radians_per_second
    × exposure_seconds
```

Where:

```text
focal_length_pixels
    ≈ focal_length_mm
    / sensor_width_mm
    × frame_width_pixels
```

Example:

```text
Exposure: 1/20 second
Angular movement: 0.025 rad/s
Focal length: 1,600 pixels

Predicted smear:
1600 × 0.025 × 0.05 = 2 pixels
```

Two pixels of smear may be visible.

The companion can respond instantly:

> “Hold the phone steadier.”

Or:

> “There is too much movement for 1/20 second. Use the main lens or increase shutter speed.”

This is much more dependable than asking an LLM whether the preview “looks shaky.”

---

## 13. Horizon and camera angle

The gravity or rotation-vector sensor can calculate:

- Roll
- Pitch
- Whether the camera is level
- Whether the phone is facing upward or downward
- How quickly the framing is changing

A rule can be:

```text
roll under 0.5°:
    level

roll between 0.5° and 2°:
    slightly tilted

roll above 2°:
    show correction guide
```

For intentional Dutch angles, the system should avoid repeated warnings after the user ignores the correction or locks the composition.

---

# 14. Focus can be checked without an LLM

Combine:

- Camera2 AF state
- Focus distance
- Edge sharpness inside the subject
- Face or eye landmarks
- Subject movement
- Camera movement

Useful states:

```text
focus_searching
focus_locked
focus_lost
wrong_subject_focused
subject_moving_out_of_focus_plane
low_light_focus_failure
lens_too_close
```

A simple sharpness score can use variance of Laplacian, Sobel gradients, or high-frequency energy on a downscaled subject crop.

Do not evaluate sharpness across the entire frame. The background may be very detailed while the person’s eyes remain soft.

For portraits:

```text
1. Detect face.
2. Estimate eye regions.
3. Measure edge strength around both eyes.
4. Compare with nearby hair and background.
5. Combine with AF state.
```

Then:

> “Focus is currently on the background, not the face.”

---

# 15. Lens choice can be automatic

The Xiaomi 14T has approximately:

- 15 mm equivalent ultra-wide
- 23 mm equivalent main camera
- 50 mm equivalent telephoto

Its main camera is f/1.7, telephoto f/1.9, and ultra-wide f/2.2. ([mi.com](https://www.mi.com/global/product/xiaomi-14t/specs/?utm_source=chatgpt.com))

A camera companion can select or suggest a lens based on:

```text
subject distance
available light
phone movement
background distance
number of people
space around the subject
desired framing
```

Example deterministic rules:

```text
Low light + moving subject:
    prefer main camera

Portrait + subject 1.5–3 metres away + enough light:
    suggest telephoto

Large group + limited space:
    suggest ultra-wide

Face close to ultra-wide edge:
    warn about perspective distortion

Telephoto + slow shutter + strong phone movement:
    suggest main camera
```

The LLM is not needed to make these choices.

---

# 16. Low-light vision for the companion itself

If the preview becomes too dark for object and face detection, Android offers two real-time low-light options:

1. Low Light Boost AE mode on supported camera hardware
2. Google Low Light Boost through Google Play services

Google Low Light Boost can process a Camera2 stream and brighten it in real time. CameraX can also receive its output surface. Support must be checked at runtime. ([developer.android.com](https://developer.android.com/media/camera/lowlight/low-light-boost-ae?utm_source=chatgpt.com))

For your system:

```text
Original camera frame:
    exposure and clipping analysis

Brightened analysis frame:
    object, face, and text detection
```

Do not calculate scene brightness only from the brightened frame. Otherwise, the system may believe a dark room is well lit because software has raised the preview brightness.

---

# 17. Suggested update rates

| Component | Suggested frequency |
|---|---:|
| Gyroscope and rotation | 100–200 Hz |
| Exposure metadata | Every camera frame |
| Low-resolution luminance | 30 FPS |
| Horizon and blur risk | 30–60 FPS |
| Face or subject tracking | 10–30 FPS |
| ARCore light estimate | Read each ARCore frame; publish only when changed |
| Raw depth | 5–15 FPS |
| Subject segmentation | 2–10 FPS or after scene changes |
| OCR | On request or when stable |
| Gemini scene update | Only after meaningful changes |

CameraX’s `STRATEGY_KEEP_ONLY_LATEST` mode is suitable for this type of work because it replaces stale frames rather than creating a growing analysis queue. ([developer.android.com](https://developer.android.com/media/camera/camerax/analyze?utm_source=chatgpt.com))

A reasonable warm-path target on the Xiaomi 14T would be:

```text
Metadata + sensors:          a few milliseconds
Luminance analysis:          2–10 ms
Tracking or face update:     target 15–50 ms
Depth/light fusion:          frame-linked and asynchronous
Rule calculation:            under 5 ms
Overlay or vibration:        same display frame

Typical local feedback goal:
50–150 ms
```

Those are design targets, not measured Xiaomi 14T results. Actual performance must be tested across heat levels, lens modes, camera resolutions, and HyperOS versions.

---

# 18. The state sent to Gemini

Instead of sending the camera frame, send this:

```json
{
  "subject": {
    "type": "person",
    "count": 1,
    "distance_m": 1.72,
    "facing_camera": true,
    "focus_quality": 0.74
  },
  "light": {
    "level": "dim",
    "direction": "upper-right",
    "subject_background_difference_stops": 2.1,
    "highlight_clip_ratio": 0.12,
    "backlit": true,
    "flicker_detected": false
  },
  "depth": {
    "background_distance_m": 2.31,
    "separation_m": 0.59,
    "confidence": 0.83
  },
  "camera": {
    "lens_equivalent_mm": 50,
    "exposure_seconds": 0.033,
    "iso": 1600,
    "roll_degrees": 2.4,
    "predicted_blur_px": 1.6
  },
  "framing": {
    "face_near_edge": false,
    "headroom": "high",
    "subject_centered": true
  }
}
```

Gemini then receives:

```text
The person is 1.72 m away.
The background is only 0.59 m behind them.
The subject is 2.1 stops darker than the background.
Main light comes from upper-right.
Highlights are clipping in 12% of the frame.
Estimated camera-shake blur is 1.6 px.
The phone is tilted 2.4 degrees clockwise.
```

Gemini’s job is only to phrase the advice:

> “The bright background is overpowering the person. Move slightly left and ask them to turn toward the light. Keep the phone steadier, and lower it a little to reduce the extra space above their head.”

The actual facts were produced locally.

---

# Recommended stack for this exact product

```text
Camera2
├── preview and final capture
├── exposure metadata
├── focus metadata
├── lens data
└── manual controls

CameraX ImageAnalysis, if you prefer easier setup
└── keep-only-latest preview analysis

SensorManager
├── gyroscope
├── gravity or rotation vector
├── accelerometer
└── ambient light

ARCore, optional spatial mode
├── Environmental HDR light direction
├── Raw Depth
├── camera pose
└── plane information

MediaPipe / ML Kit
├── face landmarks
├── person and object detection
├── subject segmentation
└── pose tracking

Local deterministic rules
├── clipping
├── backlight
├── blur risk
├── horizon
├── focus
├── depth separation
└── lens suggestion

Gemini Live
├── conversation
├── explanation
├── preference handling
└── unusual visual questions
```

The main local loop can stay comfortably below one second. In many cases, the overlay, vibration, or short warning should appear in **well under 200 ms**. Only open-ended visual questions need a multimodal cloud call.

The strongest product idea is therefore not “Gemini watches the camera continuously.” It is:

> **A local photographic perception engine continuously measures light, depth, focus, movement, and framing, while Gemini acts as its voice and reasoning layer.**

---

## User

yes yes what else? build full product plan what else needed for product cohesion and best practices

---

## Assistant

# Full product plan: real-time phone camera companion

Yes. The next step is not adding more detectors. It is making every signal serve **one clear shot goal**, giving **one useful action at a time**, and checking whether that action worked.

The product should feel like this:

> Point the phone, state what you are trying to shoot, receive one clear instruction, move or change a setting, get confirmation, and capture.

The local engine measures the scene. Gemini handles conversation, intent, explanation, and rare visual questions.

---

## 1. Product position

Do **not** sell it only as “an AI camera coach.” Google already has Camera Coach on Pixel phones, with step-by-step guidance for lighting, framing, composition, and camera modes. Pixel 11 also has Creator Suite with a teleprompter, audio level display, speech cleanup, project folders, and social-media frame guides. ([store.google.com](https://store.google.com/us/magazine/camera-coach?hl=en-US&srsltid=AfmBOorY3ghb6j8Qz12svegK8gcvTQNzOuXb4f9rXdB_sisk0JCt8EYI))

Your stronger position is:

> **A cross-brand, low-latency camera companion that measures the scene locally, reacts continuously, explains its advice, and confirms whether each change improved the shot.**

The main differences should be:

- Local reaction in roughly 50–200 ms.
- Useful without internet.
- Continuous coaching instead of a one-time scene review.
- Clear evidence behind advice.
- Works on non-Pixel Android phones.
- User-controlled style and shot goal.
- Photo and video support from the same scene state.
- No camera upload by default.
- Advice that changes as the user moves.
- Learns which advice the user likes or ignores.

---

# 2. The first major product choice

## Consumer camera app versus camera intelligence SDK

A separate companion app cannot dependably inspect the Xiaomi stock camera while that camera owns the stream. The practical consumer route is to make your own camera app.

But this creates a serious product risk: the Xiaomi 14T stock camera includes Xiaomi and Leica processing, dedicated portrait modes, 10-bit Rec.2020 HLG capture, Movie mode, and Director mode. A third-party camera path may not receive all the same vendor processing. Xiaomi exposes a strong camera feature set on the 14T, but you must test which parts are available through CameraX, Camera2, and Camera Extensions rather than assuming parity. ([mi.com](https://www.mi.com/global/product/xiaomi-14t/specs/))

CameraX Extensions can give third-party apps access to vendor-provided modes such as Night, HDR, Auto, Bokeh, and Face Retouch, but only when the device maker implements them and the device reports them as available. Google also says apps should move to CameraX 1.6 or later because some Extensions support will be removed for apps using 1.5 or earlier starting November 1, 2026. ([developer.android.com](https://developer.android.com/media/camera/camerax/extensions-api))

### Recommended product structure

Build two layers from the start:

```text
Camera Intelligence Core
├── scene measurements
├── tracking
├── shot state
├── advice policy
├── quality checks
└── Gemini connection

Consumer Camera App
├── viewfinder
├── camera controls
├── voice interface
├── overlays
├── capture
└── gallery review
```

The consumer app proves demand and collects action-result data.

The core should remain reusable as an SDK for:

- Phone makers.
- Camera app companies.
- Creator apps.
- Live-streaming apps.
- Remote camera systems.
- Smart glasses later.

Long term, an OEM or camera-app integration gives you the best mix of coaching and final image quality.

---

# 3. Start with one narrow use case

Do not begin with “understand every scene.”

Start with:

## Rear-camera portrait coach

Initial limits:

- One visible person.
- Waist-up or full-body portrait.
- Main rear camera.
- Vertical 9:16 and 4:5 output.
- Indoor and outdoor.
- Still photo first.
- Xiaomi 14T as the first supported phone.

Portrait is the best first test because almost every signal produces a clear action:

| Signal | Possible action |
|---|---|
| Face too dark | Turn toward the light |
| Strong backlight | Move sideways |
| Background too close | Move subject forward |
| Face near frame edge | Move camera left |
| Wrong lens | Step back and use 2× |
| Focus on background | Tap or relock face |
| Slow shutter | Hold still or use main lens |
| Poor headroom | Lower or raise phone |
| Body cut at joint | Reframe above or below joint |
| Background object behind head | Move slightly sideways |
| Phone tilted | Rotate phone |
| Hard overhead light | Move subject closer to window |

After portrait works, add:

1. Product and food.
2. Self-shooting and tripod.
3. Creator video.
4. Group photos.
5. General scenes.
6. Advanced creative coaching.

---

# 4. Every session needs a shot contract

The companion must know what the user is trying to make. Without this, different modules will give conflicting advice.

For example, centred framing may be right for a formal product photo but wrong for a 9:16 talking-head video with text planned on the left.

Create a small structured contract:

```json
{
  "capture_type": "photo",
  "subject_type": "person",
  "subject_count": 1,
  "framing": "waist_up",
  "output_ratio": "4:5",
  "destination": "instagram_feed",
  "style": "natural",
  "priority": "face_and_outfit",
  "allow_flash": false,
  "coach_mode": "voice_and_overlay",
  "skill_level": "beginner"
}
```

The contract can come from:

- A mode button.
- A short voice request.
- Recent user settings.
- Automatic scene detection.
- A saved shot template.

Example:

> “Take a natural full-body shot for an Instagram story. Keep the building visible.”

The language model turns this into constraints. The local engine handles the measurements.

---

# 5. Do not reduce quality to one score

A single “82/100 composition score” will often feel false because photography mixes technical facts with personal taste.

Split the evaluation into three layers.

## A. Technical condition

Usually measurable:

- Focus.
- Motion blur.
- Highlight clipping.
- Shadow loss.
- Lens blockage.
- Phone tilt.
- Subject distance.
- Audio clipping.
- Flicker.
- Exposure instability.

## B. Match to stated intent

Measured against the shot contract:

- Is the full outfit visible?
- Is there safe space for text?
- Is the chosen aspect ratio respected?
- Is the main subject large enough?
- Is the background still readable?
- Does the lens match the requested look?
- Is the person facing the intended direction?

## C. Creative options

These are not hard errors:

- More or less negative space.
- Stronger symmetry.
- A lower camera angle.
- A more dramatic side light.
- A tighter crop.
- A more graphic background.
- A different balance between subject and environment.

The UI should label them differently:

```text
FIX
Focus is on the wall.

MATCH
The shoes are outside the 9:16 crop.

TRY
Move the person farther right to leave room for text.
```

Never call a creative choice “wrong.”

---

# 6. Full perception map

The system needs more than objects, light, and depth.

| Signal family | What to calculate locally | What the product can do |
|---|---|---|
| Device capability | Available lenses, focal lengths, exposure range, focus range, OIS/EIS, RAW, HDR, extension modes | Choose valid advice for that phone |
| Light level | Median luminance, subject luminance, clipping, shadow loss, exposure metadata | Warn about dark subject, clipped sky, or blur risk |
| Light direction | ARCore light direction, face shading, shadow direction | Tell subject where to turn |
| Light quality | Local contrast, shadow edge width, face-region brightness difference | Estimate hard, soft, flat, side, or overhead light |
| Color | White-balance state, color cast, mixed-light regions, saturation clipping | Suggest moving away from mixed light or locking white balance |
| Depth | Subject distance, background distance, foreground blockage, depth confidence | Improve subject separation and camera position |
| Subject state | Face, eyes, pose, hands, body bounds, orientation, gaze, blink | Improve pose, crop, timing, and focus |
| Framing | Headroom, look room, lead room, body cuts, frame-edge distance, platform safe area | Give direct movement guidance |
| Background | Visual clutter, strong edges, bright spots, object mergers, competing faces | Suggest moving camera or subject |
| Focus | AF state, subject sharpness, eye sharpness, background sharpness | Detect wrong focus plane |
| Motion | Gyroscope, optical flow, subject speed, shutter duration | Estimate camera-shake and subject-blur risk |
| Capture timing | Eye state, expression stability, pose stability, motion phase | Choose a better frame from a short buffer |
| Lens condition | Dirt, fog, flare, finger blockage, case edge, water drops | Ask user to clean or uncover lens |
| Video movement | Horizon drift, pan speed, acceleration, walking bounce | Coach smoother camera movement |
| Video audio | Speech level, peak level, noise level, wind, echo, mic blockage | Warn before recording bad sound |
| Scene meaning | Broad scene category, activity, likely main subject | Select the right shot template |
| Device condition | Thermal state, battery, storage, model availability | Reduce workload or prevent failed capture |

### Most of this does not need a large model

Use ordinary calculations for:

- Histograms.
- Clipping.
- Edge strength.
- Optical flow.
- Horizon and line detection.
- Phone movement.
- Audio levels.
- Flicker.
- Subject-background brightness.
- Frame-safe regions.
- Capture timing.

Use small models for:

- Faces.
- Pose.
- Hands.
- Subjects.
- Segmentation.
- Object categories.
- Monocular depth fallback.
- Scene category.

Use Gemini for:

- Interpreting the requested shot.
- Explaining an issue.
- Offering creative options.
- Handling uncommon scenes.
- Answering follow-up questions.
- Turning measurements into natural speech.

---

# 7. The central data model

Every detector must write to one shared state. Detectors should not talk directly to the UI or Gemini.

```text
Camera and sensors
        ↓
Measurement modules
        ↓
Shared ShotState
        ↓
Advice policy
        ↓
Overlay / haptic / voice / camera control
```

## Basic metric structure

Every measurement needs:

```kotlin
data class Metric<T>(
    val value: T,
    val confidence: Float,
    val source: String,
    val frameId: Long,
    val timestampNs: Long,
    val validUntilNs: Long
)
```

This stops old depth, old pose, and current camera data from being mixed accidentally.

## Main state

```kotlin
data class ShotState(
    val intent: ShotIntent,
    val device: DeviceState,
    val camera: CameraState,
    val lighting: LightingState,
    val depth: DepthState,
    val subjects: List<SubjectState>,
    val composition: CompositionState,
    val focus: FocusState,
    val motion: MotionState,
    val audio: AudioState?,
    val health: RuntimeHealth,
    val activeAdvice: AdviceState?
)
```

## Important state rules

- Use stable subject IDs across frames.
- Use one normalized coordinate system.
- Save the crop and rotation transform for every frame.
- Use the camera capture timestamp as the main time reference.
- Mark stale measurements as invalid.
- Keep confidence separate from severity.
- Record the source of every fact.
- Never let Gemini overwrite sensor facts.
- Keep measured facts separate from inferred facts.

Example:

```json
{
  "fact": "subject_background_gap_m",
  "value": 0.54,
  "confidence": 0.82,
  "source": "arcore_raw_depth",
  "age_ms": 48
}
```

---

# 8. The real product: the advice policy

The detectors are not the main value. The main value is deciding:

- Whether to speak.
- What to say first.
- Whether the issue is fixable.
- Whether it matters for this shot.
- Whether the user already ignored it.
- Whether a previous instruction worked.

## Advice ranking

A simple first policy can use:

```text
priority =
    expected visual impact
    × confidence
    × relevance to shot goal
    × ease of fixing
    × persistence
    − annoyance cost
```

Do not use a learned policy at first. Start with explicit rules and log the results.

## Advice order

Use this order:

1. Capture blockers.
2. Technical faults.
3. Shot-contract conflicts.
4. Large, easy improvements.
5. Creative options.
6. Silence.

Examples of blockers:

- Lens covered.
- No storage.
- Camera not focused.
- Severe motion blur.
- Subject outside planned crop.
- Audio clipping during video.

## Closed-loop state machine

```text
OBSERVE
   ↓
SELECT ONE ISSUE
   ↓
GIVE ONE ACTION
   ↓
WATCH FOR CHANGE
   ↓
CONFIRM OR CORRECT
   ↓
READY
```

Example:

```text
Measured:
Face is 1.9 stops darker than background.

Instruction:
“Ask them to turn toward the window.”

Verification:
Face-background gap falls to 0.8 stops.

Confirmation:
“Good. The face light is balanced now.”
```

Then the engine moves to the next issue.

## Anti-annoyance rules

- Do not speak until an issue persists for about 300–500 ms.
- Do not repeat the same instruction immediately.
- Give one action only.
- Use a cooldown after each spoken instruction.
- Stop after two ignored attempts.
- Do not comment on tiny changes.
- Do not switch advice while the user is already moving.
- Do not speak during the final shutter moment.
- Do not offer creative advice when a technical fault is active.
- Do not speak when the shot is already ready.
- Reduce advice frequency as user skill increases.

Silence is part of the product.

---

# 9. User experience

## Main screen

Keep the viewfinder clean.

```text
┌──────────────────────────────┐
│  PORTRAIT · 4:5       LIGHT  │
│                              │
│          subject guide       │
│                              │
│     ← Move slightly left     │
│                              │
│   mic      shutter     mode  │
└──────────────────────────────┘
```

Only show:

- Current shot goal.
- One active instruction.
- A simple visual guide.
- Mic state.
- Shutter.
- Coach mode.

Advanced values should stay behind a tap.

## Coaching modes

### Quiet

- Overlay only.
- Haptic when ready.
- No speech.

### Coach

- Short voice instructions.
- Visual arrows.
- User can ask “why?”

### Hands-free

- Voice goal setup.
- Pose and framing guidance.
- Countdown when ready.
- Automatic short burst after stable conditions.
- Voice retake check.

A separate Pro mode can come later with histograms, depth values, exposure data, focus peaking, and audio meters.

## Advice format

Spoken advice should follow this pattern:

```text
Action first.
Reason only when needed.
Confirmation after success.
```

Good:

> “Move half a step left.”

Less useful:

> “The composition could be improved because several background elements are competing with the main subject.”

On-screen text can add:

```text
Move half a step left
Reason: bright sign behind the head
```

## Haptic language

Keep it simple:

- One short pulse: ready.
- Two short pulses: hold still.
- One long pulse: capture problem.

Do not make users learn left/right haptic codes at launch.

---

# 10. Example full session

The user says:

> “Natural full-body photo for an Instagram story. Keep the café sign visible.”

The system creates:

```json
{
  "subject": "one_person",
  "framing": "full_body",
  "ratio": "9:16",
  "background_priority": "cafe_sign",
  "style": "natural"
}
```

### Step 1: initial scene

Measured:

- Subject 1.6 m away.
- Wall 0.4 m behind subject.
- Sign visible.
- Face 1.7 stops darker than background.
- Shoes close to bottom safe area.
- Phone tilted 2.2°.
- Main lens active.
- Shutter estimate 1/30 second.
- Moderate phone movement.

First instruction:

> “Ask them to step away from the wall.”

The app checks whether background separation increases.

### Step 2: lighting

After movement:

- Subject-wall gap becomes 1.4 m.
- Face remains dark.

Instruction:

> “Turn their face slightly toward the window.”

The app verifies the light ratio.

### Step 3: framing

- Light now acceptable.
- Shoes remain too close to the crop.
- Phone still tilted.

Instruction:

> “Step back a little.”

After the subject fits:

> “Rotate the phone slightly counter-clockwise.”

### Step 4: readiness

Requirements remain stable for 400 ms:

- Face focus good.
- Eyes open.
- Whole body inside safe crop.
- Café sign visible.
- Motion blur risk low.
- Exposure acceptable.

The phone gives one short pulse:

> “Ready.”

### Step 5: capture review

The app checks:

- Eye sharpness.
- Blink.
- Motion blur.
- Cropping.
- Highlight clipping.
- Expression.
- Best frame in the short buffer.

It says either:

> “Good capture.”

or:

> “The face moved during the shot. One more.”

That is a complete product loop. The LLM is not responsible for the measurements.

---

# 11. System design

```text
CameraX / Camera2              SensorManager
        │                           │
        └─────────┬─────────────────┘
                  ▼
          Timestamped frame router
                  │
       ┌──────────┼───────────┐
       ▼          ▼           ▼
 Fast metrics   ML tasks   Depth/light
       │          │           │
       └──────────┼───────────┘
                  ▼
             ShotState
                  │
          Local advice policy
          ┌───────┼─────────┐
          ▼       ▼         ▼
       Overlay  Haptic   Local speech
                  │
          Sparse state updates
                  ▼
             Gemini Live
                  │
        Explanation / intent / tools
                  ▼
          Camera action gateway

Capture
   ▼
Post-capture quality check
   ▼
Keep / retake / best frame
```

## Suggested Android modules

```text
app-camera
camera-runtime
camera-capabilities
frame-router
sensor-fusion
perception-light
perception-depth
perception-subject
perception-composition
perception-motion
perception-audio
shot-state
shot-policy
coach-ui
coach-audio
gemini-live
capture-review
device-performance
telemetry
```

This separation lets you test the advice policy using recorded states without running the camera.

---

# 12. Google stack for the Xiaomi 14T

## Camera

Use **CameraX 1.6+** for preview, analysis, capture, lifecycle handling, and vendor extensions where available. Use Camera2 interop for exposure metadata, focus metadata, lens properties, advanced controls, and capability checks. Google recommends CameraX as the starting point for new Android camera apps. ([developer.android.com](https://developer.android.com/media/camera/camerax))

Configure image analysis with `STRATEGY_KEEP_ONLY_LATEST`. CameraX specifically supports dropping stale analysis frames when processing cannot keep up. For a live companion, a new frame is more useful than an old frame waiting in a queue. ([developer.android.com](https://developer.android.com/media/camera/camerax/analyze))

## Light and depth

The Xiaomi 14T is listed as supporting ARCore’s Depth API. ARCore Raw Depth also provides confidence data, while Environmental HDR can provide a main light direction, main light intensity, and ambient lighting information. ([developers.google.com](https://developers.google.com/ar/devices))

Do not make ARCore mandatory in the main capture path. ARCore Shared Camera allows Camera2 access alongside ARCore, but it changes camera control rules, requires careful stream testing, and cannot use a hardware depth sensor while shared-camera mode is active. Treat ARCore as an optional spatial-assist path with a fallback. ([developers.google.com](https://developers.google.com/ar/reference/java/com/google/ar/core/SharedCamera))

Fallback depth sources:

- Focus-plane distance.
- Face-size estimate.
- Known object size.
- Motion parallax.
- Small monocular depth model through LiteRT.
- Near, middle, and far classification rather than exact metres.

## Faces, pose, and hands

Use:

- MediaPipe Face Landmarker.
- MediaPipe Pose Landmarker.
- MediaPipe Hand Landmarker when hands matter.
- A lighter face detector when full landmarks are not needed.

MediaPipe supports continuous camera streams, and its pose output includes image and 3D world coordinates. ([ai.google.dev](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/android))

Do not run full pose, face, and hand tracking at all times. Gate them:

```text
No person:
    face, pose, hand models off

Person present:
    face model on

Full body requested:
    pose model on

Hands near product:
    hand model on
```

## Segmentation and OCR

ML Kit can provide text recognition and on-device subject segmentation. Subject Segmentation is still beta and uses a model downloaded through Google Play services, so pre-install it and keep a fallback for the first run or offline use. ([developers.google.com](https://developers.google.com/ml-kit/vision/subject-segmentation/android))

For portrait MVP, a person segmentation mask from MediaPipe Pose or a bundled local model may be safer than making the beta subject segmenter a required dependency.

## Custom models

Use LiteRT’s `CompiledModel` API for custom INT8 models. LiteRT can use CPU, GPU, and NPU paths, and current Google documentation includes MediaTek NeuroPilot support through the CompiledModel API. The Xiaomi 14T uses the Dimensity 8300-Ultra. Do not assume every operation will reach the NPU; benchmark each model and keep GPU/CPU fallbacks. ([ai.google.dev](https://ai.google.dev/edge/litert/android))

## Low light

Use the original frame for exposure measurements, but an optionally brightened frame for face, object, or text detection.

Android provides:

- Low Light Boost AE when supported by the camera.
- Google Low Light Boost through Google Play services for some other devices.

Support must be checked at runtime. ([developer.android.com](https://developer.android.com/media/camera/lowlight/low-light-boost-ae))

---

# 13. Runtime schedule

A good starting schedule is:

| Module | Rate |
|---|---:|
| Camera preview | 30 FPS |
| Luminance and clipping | Every frame |
| Rotation and blur estimate | 30–60 Hz |
| Face tracking | 10–20 FPS |
| General object detector | 5–10 FPS |
| Pose | 8–15 FPS when required |
| Raw depth | 5–10 FPS |
| Segmentation | 2–5 FPS |
| OCR | On request or stable frame |
| Light-direction update | When meaningfully changed |
| Audio level | Continuous |
| Audio classifier | Continuous, low-rate windows |
| Scene-state publication | 5–15 Hz |
| Spoken advice | Event-based |
| Gemini image upload | Rare, event-based, no more than API limit |

### Suggested local latency targets

These are product targets, not guarantees:

```text
P50 measurement-to-overlay:     under 120 ms
P95 measurement-to-overlay:     under 250 ms
Local haptic response:           under 200 ms
Local short speech start:        under 600 ms
Viewfinder frame stalls:         none above 700 ms
```

Use separate latency measurements for:

- Frame acquisition.
- Preprocessing.
- Each model.
- State reduction.
- Advice choice.
- UI rendering.
- Speech start.
- Gemini network response.

---

# 14. Thermal and battery management

A camera, ARCore, several models, screen brightness, audio, and network can heat a midrange phone quickly.

Use four runtime levels:

## Full

- Normal model rates.
- Depth active.
- Segmentation active.
- Gemini available.

## Reduced

- Detector rate lowered.
- Segmentation paused.
- Depth reduced.
- Lower preview-analysis resolution.

## Hot

- Basic face tracking only.
- Light, focus, motion, and framing metrics.
- No continuous depth.
- No cloud images.

## Critical

- Camera and basic overlay only.
- Voice on request.
- Inform user that advanced coaching is paused.

Android provides Thermal APIs, including thermal status and predicted thermal headroom. Google recommends reducing workload before severe throttling occurs rather than waiting until the device is already hot. ([developer.android.com](https://developer.android.com/games/optimize/adpf/thermal))

Additional rules:

- Warm models once per session.
- Never recreate detectors per frame.
- Cancel stale work.
- Avoid bitmap and JPEG conversions in the local path.
- Reuse buffers.
- Keep only the latest frame.
- Lower processing rates while the phone is moving quickly.
- Raise rates when the phone becomes stable.
- Stop depth and segmentation while the app is in settings or gallery.
- Benchmark plugged-in and battery operation separately.

---

# 15. Gemini Live’s exact role

Gemini should not be the frame-by-frame vision engine.

The current Live API accepts video as separate images at a maximum of one frame per second. Audio-plus-video sessions also have a two-minute base limit unless session-management features are used. This confirms that Gemini video is suited to context and uncommon visual questions, not continuous camera measurements. ([ai.google.dev](https://ai.google.dev/gemini-api/docs/live-api/capabilities))

## Use Gemini for

- Converting user speech into a shot contract.
- Asking one necessary question about intent.
- Explaining local advice.
- Offering two creative variants.
- Identifying an unknown object.
- Understanding a complex background.
- Answering “why?”
- Handling natural follow-up conversation.
- Calling safe camera functions.

## Do not use Gemini for

- Horizon correction.
- Blur warning.
- Focus warning.
- Highlight clipping.
- Depth tracking.
- Subject tracking.
- Audio clipping.
- Shutter timing.
- Immediate camera movement instructions.
- Thermal management.

## Important current API detail

Gemini 3.1 Flash Live defaults to minimal thinking for low latency, but it does not currently support proactive audio. Your local advice policy must decide when the assistant should speak and send a short event to Gemini when natural wording is needed. ([ai.google.dev](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-live-preview))

## Connection setup

Use:

- Direct client-to-Gemini WebSocket.
- A small backend for short-lived tokens.
- Ephemeral tokens rather than embedding the API key.
- 20–40 ms audio chunks.
- Immediate playback cancellation when the user interrupts.
- Context compression.
- Session resumption.
- Low media resolution.
- Sparse structured text updates.

Google recommends ephemeral tokens for client-to-server Live API connections, small audio chunks for lower latency, context compression for long sessions, and session resumption for reconnects. ([ai.google.dev](https://ai.google.dev/gemini-api/docs/live-api/ephemeral-tokens))

---

# 16. Gemini tools

Give Gemini a small and strict tool set.

```text
get_current_shot_state()
set_shot_goal(...)
set_coach_mode(...)
explain_active_advice()
switch_lens(...)
set_exposure_compensation(...)
tap_focus(...)
lock_focus(...)
set_output_ratio(...)
start_countdown(...)
take_photo(...)
start_recording(...)
stop_recording(...)
review_last_capture()
mute_advice(...)
```

The model should not send unrestricted camera parameters.

For example:

```text
Bad:
setCameraParameter(name, value)

Better:
setExposureCompensation(evSteps: -2..2)
```

The local app must:

- Check device support.
- Clamp values.
- Reject unsafe or invalid changes.
- Show the change on screen.
- Make changes reversible.
- Avoid switching lenses during recording unless allowed.
- Avoid automatic flash without clear permission.
- Avoid automatic capture outside hands-free mode.

The LLM requests an action. The local policy decides whether it is valid.

---

# 17. Voice system instruction

A compact system instruction is better than a long photography textbook.

Core rules:

```text
You are the spoken layer of a real-time camera companion.

The app provides measured scene facts. Treat these facts as the source of truth.

Give at most one physical action per response.

Keep normal coaching responses under twelve words.

Do not call a creative choice wrong.

Do not invent distances, light directions, camera settings, or subject states.

When confidence is low, say so briefly.

Do not speak unless the app sends an advice event or the user asks a question.

Use camera tools only under their stated conditions.

When an action succeeds, confirm it briefly and stop speaking.
```

Examples should cover:

- Backlight.
- Focus on background.
- Insufficient depth separation.
- User ignoring advice.
- Conflicting signals.
- Low confidence.
- User asking for a creative option.
- User interrupting.
- No internet.

---

# 18. Capture and post-capture quality

The product should continue working after the shutter.

## Before capture

Keep a small rolling buffer of recent low-resolution frames and state values.

Track:

- Eye openness.
- Face orientation.
- Subject motion.
- Camera motion.
- Focus confidence.
- Expression stability.
- Crop validity.

## At capture

Store:

- Shutter timestamp.
- Current shot state.
- Active advice.
- Lens and exposure metadata.
- Subject tracks.
- Sensor motion around capture.

## After capture

Check:

- Subject sharpness.
- Eye sharpness.
- Blink.
- Motion blur.
- Crop.
- Exposure.
- Face obstruction.
- Strong flare.
- Intended subject presence.
- Audio start quality for video.

CameraX has an optional Zero-Shutter Lag mode on supported devices, using a recent-frame buffer, but it is experimental and has device and mode restrictions. Treat it as an optional gain rather than a required feature. ([developer.android.com](https://developer.android.com/media/camera/camerax/take-photo/zsl))

The first version does not need full AI editing. A good retake recommendation is more valuable than a poor automatic edit.

---

# 19. Device capability registry

Android camera support differs heavily across phones. Build a capability probe before loading the normal camera UI.

Record:

```json
{
  "device": "xiaomi_14t",
  "os_build": "...",
  "camera_ids": ["0", "1", "2"],
  "physical_lenses": ["main", "ultrawide", "telephoto"],
  "camera_extensions": ["hdr", "night"],
  "raw_supported": true,
  "zsl_supported": true,
  "manual_focus": true,
  "exposure_compensation_range": [-4, 4],
  "low_light_boost": false,
  "arcore_depth": true,
  "environmental_hdr": true,
  "npu_model_support": {
    "face_model": true,
    "depth_model": false
  },
  "stable_stream_sets": [
    "preview+analysis+capture"
  ]
}
```

Use this profile to choose the pipeline.

Maintain:

- Local cached profile.
- Remote device compatibility table.
- OS-build-specific exceptions.
- Feature flags.
- Safe fallbacks.
- Model placement results.
- Thermal test results.

Do not identify a phone only by marketing name. Include:

- Manufacturer.
- Model.
- Build fingerprint.
- Android version.
- Camera ID and physical camera IDs.
- Supported stream combination.
- Model version.

---

# 20. Failure and fallback plan

| Failure | Fallback |
|---|---|
| No network | Local coach and Android TTS |
| Gemini session closes | Reconnect with session resumption |
| ARCore unavailable | Relative depth or monocular model |
| Depth confidence low | Use near/middle/far wording |
| Segmentation model missing | Face or object box |
| NPU model fails | GPU, then CPU |
| Phone becomes hot | Reduce model rates |
| Dark preview | Low Light Boost or brightened analysis frame |
| Face model loses subject | General object tracker |
| User moves quickly | Pause detailed advice |
| Camera extension unavailable | Standard capture |
| Advice repeatedly ignored | Lower advice frequency |
| Cloud visual review slow | Continue local feedback |
| Unknown scene | Ask one short intent question |
| Storage nearly full | Block capture with a clear warning |
| Mic blocked | On-screen warning before video |

The product must remain useful even when every optional service is missing.

---

# 21. Privacy and trust

The camera and microphone are highly sensitive. Android recommends clear permission explanations and a visible in-app indicator while capturing, in addition to system privacy indicators. ([developer.android.com](https://developer.android.com/training/permissions/explaining-access))

Use these rules:

## Local by default

- Raw frames remain on the phone.
- Raw microphone audio remains local unless live conversation is active.
- Technical scene measurements remain local.
- No facial identity recognition.
- No permanent face embeddings.
- No background camera use.

## Cloud visual use must be visible

Show a clear status:

```text
LOCAL
No camera frames are being sent.

CLOUD REVIEW
One low-resolution frame is being checked.
```

## Send minimum data

Normal cloud update:

```json
{
  "event": "advice_needed",
  "issue": "subject_backlit",
  "face_background_difference_stops": 1.8,
  "main_light_direction": "camera_right",
  "recommended_action": "turn_subject_toward_right"
}
```

Not:

```text
continuous full camera stream
```

## Analytics

Default analytics should contain:

- Device category.
- Feature support.
- Processing latency.
- Advice type.
- Whether state improved after advice.
- Crash and thermal data.
- Session duration.

Do not collect:

- Camera frames.
- Audio.
- Face crops.
- Exact user location.
- Recognized text.
- Full spoken transcripts.

Media collection for model testing should be a separate opt-in program with clear deletion controls.

---

# 22. Product learning without storing photos

The most valuable data is not the final photo. It is the **action-result pair**.

Example:

```json
{
  "initial_state": {
    "face_background_stops": 2.0,
    "background_gap_m": 0.4
  },
  "advice": "turn_toward_window",
  "user_action_detected": true,
  "result_state": {
    "face_background_stops": 0.9,
    "background_gap_m": 0.4
  },
  "capture_followed": true,
  "retake_requested": false
}
```

This tells you:

- Which advice users follow.
- Which advice works.
- Which conditions cause confusion.
- Which instruction wording works fastest.
- Which advice is ignored by skilled users.
- Which device measurements are unreliable.

This can improve the policy without storing identifiable media.

---

# 23. Personalisation

Keep early personalisation simple.

Learn locally:

- Preferred lens.
- Preferred framing tightness.
- Whether user likes centred or offset subjects.
- Advice frequency.
- Voice versus haptic preference.
- Common output ratio.
- Whether user accepts automatic capture.
- Preferred natural or stronger contrast.
- Common photo subjects.
- Skill level.

Example:

```json
{
  "portrait_preferences": {
    "preferred_equivalent_mm": 50,
    "headroom": "tight",
    "subject_scale": "large",
    "advice_frequency": "low",
    "creative_suggestions": true
  }
}
```

Do not silently infer identity, age, ethnicity, attractiveness, or other personal traits.

A user must be able to reset the profile.

---

# 24. Testing plan

## A. Measurement tests

Use controlled setups for:

- Distance with tape measurements.
- Light with known positions.
- Exposure with calibrated charts.
- Horizon with a level.
- Motion with a tripod and controlled movement.
- Flicker with 50 Hz and 60 Hz lights.
- Audio with fixed speaker levels.
- Background distance.
- Face and pose angles.
- Lens dirt and flare.

Metrics:

- Distance error.
- Horizon-angle error.
- Tracking loss rate.
- Face-box stability.
- Light-direction error.
- False clipping warning rate.
- Blur-risk accuracy.
- Advice flip rate.
- State age at decision time.

## B. Photography expert review

Give experts:

- Current frame.
- Shot contract.
- App advice.
- Result after user action.

Ask:

- Was the issue real?
- Was it important?
- Was the action clear?
- Was it the best first action?
- Did it improve the result?
- Should the app have stayed quiet?

## C. Blind comparison

For each test session:

1. User takes a shot without coaching.
2. User takes a shot with coaching.
3. Independent reviewers compare both.
4. Reviewers do not know which one used the app.

Measure:

- Preferred capture rate.
- Technical failure reduction.
- Retake reduction.
- Time to acceptable capture.
- User confidence.
- Advice annoyance.

## D. Performance tests

Track:

- P50, P90, and P95 latency.
- Preview frame rate.
- Frozen frames.
- Memory.
- CPU, GPU, and NPU use.
- Battery.
- Thermal headroom.
- Cloud response time.
- Crash rate.
- ANR rate.

Android provides Microbenchmark, Macrobenchmark, Perfetto, and Android Vitals for measuring code paths, startup, frame delays, crashes, and power-related quality issues. ([developer.android.com](https://developer.android.com/topic/performance/measuring-performance))

---

# 25. Core product metrics

## North-star metric

**Coached capture success rate**

```text
Sessions ending with a kept capture
÷
Sessions where the user attempted a capture
```

## Supporting metrics

- Time to first useful instruction.
- Time from opening camera to capture.
- Percentage of advice followed.
- Percentage of followed advice that improved the measured state.
- Retakes per kept capture.
- Percentage of sessions completed offline.
- Percentage of sessions requiring a cloud frame.
- User mute rate.
- Advice ignored rate.
- Capture-after-ready rate.
- Post-capture failure rate.

## Guardrail metrics

- Spoken instructions per minute.
- Contradictory advice rate.
- Advice flip rate.
- False technical warning rate.
- Cloud frame-upload rate.
- Thermal throttling rate.
- Battery use.
- Preview stalls.
- Camera startup failure.
- Privacy-setting abandonment.

A coaching system can improve photo metrics while still being irritating. Both sides must be measured.

---

# 26. Build phases and exit conditions

## Phase 0: device probe

Build a plain engineering app for the Xiaomi 14T.

It should test:

- Camera IDs and physical lenses.
- Preview-analysis-capture combinations.
- Metadata availability.
- Camera Extensions.
- RAW and HDR.
- ARCore depth.
- ARCore light estimation.
- Shared Camera.
- LiteRT model placement.
- Low Light Boost.
- Long-session thermal behavior.
- Audio input.
- Capture latency.

Exit when you know which path is stable on the real phone.

## Phase 1: local portrait coach

No Gemini required.

Include:

- One-person tracking.
- Face landmarks.
- Horizon.
- Headroom.
- Full-body crop.
- Subject-background brightness.
- Clipping.
- Focus.
- Camera-shake risk.
- Subject distance.
- Background distance.
- One advice at a time.
- Overlay and haptic.
- Normal photo capture.

Exit when experts agree that the advice is correct and correctly ordered in most controlled test scenes.

## Phase 2: closed-loop policy

Add:

- Advice verification.
- Cooldowns.
- Persistence thresholds.
- Ignored-advice handling.
- Ready state.
- Shot contract.
- Quiet and Coach modes.
- State replay tests.

Exit when the system stops producing repetitive and conflicting advice.

## Phase 3: voice and Gemini

Add:

- Voice goal input.
- Gemini Live.
- Short-lived token backend.
- “Why?” explanations.
- Safe tool calls.
- Local TTS fallback.
- Cloud visual review only on demand.
- Session resumption.

Exit when cloud failure never blocks local coaching.

## Phase 4: hands-free and capture review

Add:

- Voice shutter.
- Stable-pose countdown.
- Short frame buffer.
- Blink check.
- Eye sharpness.
- Retake recommendation.
- Best-frame selection.

## Phase 5: product and food

Add:

- Product segmentation.
- Glare.
- Surface angle.
- Perspective.
- Text orientation.
- Background consistency.
- Color-cast checks.
- Table and horizon geometry.

## Phase 6: creator video

Add:

- Audio level.
- Wind warning.
- Speech-to-noise ratio.
- Social safe areas.
- Teleprompter.
- Horizon drift.
- Walking bounce.
- Pan speed.
- Exposure drift.
- Focus breathing warning.
- Shot list and project folders.

## Phase 7: reusable SDK

Expose:

```text
startSession()
setShotIntent()
observeShotState()
observeAdvice()
submitUserAction()
reviewCapture()
```

The app should already be using this same SDK internally.

---

# 27. What the MVP should not include

Do not include these in the first public version:

- A local general-purpose visual language model.
- Support for every Android phone.
- Every photography genre.
- Automatic full editing.
- Beauty scoring.
- Attractiveness scoring.
- Complex style transfer.
- Continuous cloud camera streaming.
- Full social-media publishing.
- Multi-person group direction.
- Wildlife tracking.
- Advanced cinematic shot planning.
- Automatic manual exposure control in every mode.
- A single universal quality score.

These can hide whether the core closed-loop coaching system is actually useful.

---

# 28. Cloud cost

Google currently lists Gemini 3.1 Flash Live at approximately:

- Audio input: $0.005 per minute.
- Image or video input: $0.002 per minute.
- Audio output: $0.018 per minute.
- Text input: $0.75 per million tokens.
- Text output: $4.50 per million tokens. ([ai.google.dev](https://ai.google.dev/gemini-api/docs/pricing))

A sample session with:

- 10 minutes of audio input.
- 2 minutes of spoken output.
- 1 minute of sparse visual input.

would cost about **$0.088** before small text and backend costs.

That supports a model such as:

## Free

- Local photo coaching.
- Basic portrait mode.
- Quiet overlay.
- Limited local templates.

## Pro

- Live voice.
- Hands-free capture.
- Video coaching.
- Saved shot styles.
- Advanced review.
- More cloud visual checks.
- Project support.

## Business

- SDK licence.
- OEM integration.
- Creator-platform integration.
- Custom rule packs.
- Device-specific optimisation.

Cost controls:

- Never keep Gemini connected when the user is only framing silently.
- Use local voice commands for common actions.
- Use local TTS for standard advice.
- Send structured state instead of frames.
- Send crops rather than whole frames.
- Cap cloud visual checks.
- End idle sessions.
- Keep monthly cloud limits visible.

---

# 29. Main risks and responses

| Risk | Response |
|---|---|
| Third-party capture looks worse than Xiaomi stock camera | Keep core as SDK and test Camera Extensions |
| Too many instructions | One-action policy, cooldowns, silence |
| Phone becomes hot | Adaptive processing levels |
| Depth is unstable | Confidence, smoothing, multiple fallbacks |
| Gemini is slow | Local instruction first |
| Gemini contradicts measurements | Structured state is source of truth |
| Android devices differ | Capability registry and per-device testing |
| Users distrust camera upload | Local default and visible cloud state |
| Creative advice feels generic | Use shot contract and saved preference |
| Advice changes too often | Persistence and action-in-progress state |
| App misses the shutter moment | Local ring buffer and optional ZSL |
| Model download fails | Bundle core models and make extras optional |

---

# 30. Exact first public build

The first usable version should contain only:

1. Xiaomi 14T support.
2. Rear main camera.
3. One-person portrait.
4. 4:5 and 9:16 framing.
5. Face and body tracking.
6. Subject-background light difference.
7. Highlight clipping.
8. Horizon and headroom.
9. Subject and background distance.
10. Focus and blur warning.
11. Background-object merger warning.
12. One-action closed loop.
13. Quiet and Coach modes.
14. Local speech fallback.
15. Optional Gemini explanation.
16. Normal capture.
17. Blink and sharpness review.
18. Performance and thermal logging.
19. No raw media analytics.
20. A replay tool for recorded test sessions.

The first product goal is not to make every shot artistic. It is to prove:

> **Can the app find the most important fix, explain it clearly, detect that the user applied it, and improve the captured result without slowing the camera or becoming annoying?**

The core product is not an LLM watching a camera. It is a fast local measurement and control system, with Gemini serving as its conversational layer. That separation is what gives you low delay, lower cost, offline use, clear evidence, and a product that feels like one complete system rather than a collection of camera features.

---

## User

lets make all our conversation into single markdown file zipped so i can download
