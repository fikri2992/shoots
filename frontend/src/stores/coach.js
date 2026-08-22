import { acceptHMRUpdate, defineStore } from 'pinia'

import api from '@/api'
import { openMic, Player } from '@/live/audio'

/**
 * One voice session at a time, about one shot. The socket carries PCM both
 * ways and JSON for transcripts; this store turns that into lines the panel
 * renders. Options syntax (AGENTS.md).
 */
export const useCoachStore = defineStore('coach', {
  state: () => ({
    shotId: '',
    status: 'idle', // idle | connecting | live | ended | error
    lines: [], // [{ role: 'user' | 'model', text }]
    error: '',
    muted: false,
    speaking: false,
    socket: null,
    mic: null,
    player: null,
    ticker: null,
  }),

  getters: {
    active: (state) => state.status === 'connecting' || state.status === 'live',
  },

  actions: {
    /** Must be called from a tap: mic permission and AudioContext need a gesture. */
    async start(shotId) {
      if (this.active) this.stop()
      this.shotId = shotId
      this.status = 'connecting'
      this.lines = []
      this.error = ''
      try {
        this.player = new Player()
        await this.player.resume()
        this.mic = await openMic((chunk) => {
          if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(chunk)
        })
        this.mic.setMuted(this.muted)
        this.socket = api.socket(`/api/live/${shotId}`)
        this.socket.onopen = () => {
          this.status = 'live'
        }
        this.socket.onmessage = (event) => this.onMessage(event)
        this.socket.onerror = () => this.fail('Connection failed')
        this.socket.onclose = (event) => {
          if (this.status === 'error') return
          if (event.code === 4401) this.fail('Sign in again')
          else if (event.code === 4404) this.fail('Shot not found')
          else if (event.code === 4409) this.fail('This shot has no frame to talk about yet')
          else this.finish()
        }
        this.ticker = setInterval(() => {
          this.speaking = Boolean(this.player?.speaking)
        }, 200)
      } catch (error) {
        this.fail(error.name === 'NotAllowedError' ? 'Microphone permission denied' : error.message)
      }
    },

    onMessage(event) {
      if (event.data instanceof ArrayBuffer) {
        this.player?.play(event.data)
        return
      }
      let data
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }
      if (data.type === 'transcript') this.append(data.role, data.text)
      else if (data.type === 'interrupted') this.player?.flush()
      else if (data.type === 'timeout') this.finish()
      else if (data.type === 'error') this.fail(data.text)
    },

    append(role, text) {
      const last = this.lines[this.lines.length - 1]
      if (last && last.role === role) last.text += text
      else this.lines.push({ role, text })
    },

    /** Typed fallback when speaking is awkward. */
    ask(text) {
      if (!text.trim() || this.socket?.readyState !== WebSocket.OPEN) return
      this.socket.send(JSON.stringify({ type: 'text', text }))
    },

    toggleMute() {
      this.muted = !this.muted
      this.mic?.setMuted(this.muted)
    },

    stop() {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'end' }))
      }
      this.finish()
    },

    finish() {
      this.teardown()
      if (this.status !== 'error') this.status = 'ended'
    },

    fail(message) {
      this.teardown()
      this.error = message
      this.status = 'error'
    },

    teardown() {
      clearInterval(this.ticker)
      this.ticker = null
      this.mic?.close()
      this.mic = null
      this.player?.close()
      this.player = null
      if (this.socket) {
        this.socket.onclose = null
        this.socket.onerror = null
        this.socket.onmessage = null
        if (this.socket.readyState <= WebSocket.OPEN) this.socket.close()
        this.socket = null
      }
      this.speaking = false
    },
  },
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useCoachStore, import.meta.hot))
}
