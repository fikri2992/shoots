/**
 * Microphone in, speech out, as raw PCM. No library: an AudioWorklet taps the
 * mic and posts Float32 frames; we downsample to 16 kHz Int16 for Gemini Live.
 * Playback schedules 24 kHz Int16 chunks back to back so speech never gaps,
 * and can drop everything queued when the model is interrupted.
 */

export const INPUT_RATE = 16000
export const OUTPUT_RATE = 24000

const CAPTURE_WORKLET = `
class PcmCapture extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0]
    if (channel) this.port.postMessage(channel.slice(0))
    return true
  }
}
registerProcessor('pcm-capture', PcmCapture)
`

/** Opens the mic; calls onChunk(ArrayBuffer of Int16 @16 kHz) ~every 128 samples of input. */
export async function openMic(onChunk) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  })
  const context = new AudioContext()
  await context.resume()
  const url = URL.createObjectURL(new Blob([CAPTURE_WORKLET], { type: 'application/javascript' }))
  await context.audioWorklet.addModule(url)
  URL.revokeObjectURL(url)

  const source = context.createMediaStreamSource(stream)
  const node = new AudioWorkletNode(context, 'pcm-capture')
  const resample = new Resampler(context.sampleRate, INPUT_RATE)
  let muted = false
  node.port.onmessage = (event) => {
    if (muted) return
    const pcm = resample.push(event.data)
    if (pcm.length) onChunk(toInt16(pcm).buffer)
  }
  source.connect(node)
  // Not connected to the destination: we do not want to hear ourselves.

  return {
    setMuted(value) {
      muted = value
    },
    close() {
      node.port.onmessage = null
      node.disconnect()
      source.disconnect()
      stream.getTracks().forEach((track) => track.stop())
      context.close()
    },
  }
}

/** Linear resampler with carry-over so chunk boundaries do not click. */
class Resampler {
  constructor(from, to) {
    this.ratio = from / to
    this.buffer = new Float32Array(0)
  }

  push(frame) {
    const joined = new Float32Array(this.buffer.length + frame.length)
    joined.set(this.buffer)
    joined.set(frame, this.buffer.length)
    const count = Math.floor((joined.length - 1) / this.ratio)
    const out = new Float32Array(Math.max(count, 0))
    let i = 0
    for (; i < count; i++) {
      const position = i * this.ratio
      const index = Math.floor(position)
      const frac = position - index
      out[i] = joined[index] * (1 - frac) + joined[index + 1] * frac
    }
    const consumed = Math.floor(i * this.ratio)
    this.buffer = joined.slice(consumed)
    return out
  }
}

function toInt16(float32) {
  const out = new Int16Array(float32.length)
  for (let i = 0; i < float32.length; i++) {
    const v = Math.max(-1, Math.min(1, float32[i]))
    out[i] = v < 0 ? v * 0x8000 : v * 0x7fff
  }
  return out
}

/** Gapless playback of Int16 PCM chunks at OUTPUT_RATE. */
export class Player {
  constructor() {
    this.context = new AudioContext({ sampleRate: OUTPUT_RATE })
    this.nextAt = 0
    this.sources = new Set()
  }

  async resume() {
    await this.context.resume()
  }

  play(arrayBuffer) {
    const int16 = new Int16Array(arrayBuffer)
    if (!int16.length) return
    const floats = new Float32Array(int16.length)
    for (let i = 0; i < int16.length; i++) floats[i] = int16[i] / 0x8000
    const buffer = this.context.createBuffer(1, floats.length, OUTPUT_RATE)
    buffer.copyToChannel(floats, 0)
    const source = this.context.createBufferSource()
    source.buffer = buffer
    source.connect(this.context.destination)
    const at = Math.max(this.context.currentTime + 0.02, this.nextAt)
    source.start(at)
    this.nextAt = at + buffer.duration
    this.sources.add(source)
    source.onended = () => this.sources.delete(source)
  }

  /** The model was interrupted: whatever is queued is stale. */
  flush() {
    for (const source of this.sources) {
      try {
        source.stop()
      } catch {
        // already finished
      }
    }
    this.sources.clear()
    this.nextAt = 0
  }

  get speaking() {
    return this.nextAt > this.context.currentTime
  }

  close() {
    this.flush()
    this.context.close()
  }
}
