import { acceptHMRUpdate, defineStore } from 'pinia'

import api from '@/api'
import { openMic, Player } from '@/live/audio'

/**
 * One conversation at a time, about one Shot. The socket carries PCM both
 * ways and JSON for transcripts; this store turns that into lines the sheet
 * renders. Options syntax (AGENTS.md).
 *
 * Text first: the session opens without the microphone, because a photographer
 * on a street, in a gallery, or on a laptop without a mic still deserves an
 * answer. The mic is one tap away and never a precondition.
 */
export const useCoachStore = defineStore('coach', {
  state: () => ({
    shotId: '',
    open: false, // is the sheet showing
    status: 'idle', // idle | connecting | live | ended | error
    lines: [], // [{ role: 'user' | 'model' | 'tool', text }]
    error: '',
    notice: '', // non-fatal, e.g. the mic was refused
    pending: '', // a question to send the moment the socket opens
    listening: false, // is the mic on
    retried: false, // one silent reconnect per conversation
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
    /**
     * Open the sheet for a Shot, optionally with the question the user just
     * clicked — "why did this not pass" should not need retyping.
     * Must be called from a tap: audio playback needs a gesture.
     */
    async openFor(shotId, { opener = '' } = {}) {
      this.open = true
      if (this.shotId === shotId && this.active) {
        if (opener) this.ask(opener)
        return
      }
      this.pending = opener
      this.retried = false
      await this.start(shotId)
    },

    close() {
      this.open = false
      if (this.active) this.stop()
    },

    async start(shotId, { keepNotice = false } = {}) {
      if (this.active) this.stop()
      this.shotId = shotId
      this.status = 'connecting'
      this.lines = []
      this.error = ''
      if (!keepNotice) this.notice = ''
      try {
        this.player = new Player()
        await this.player.resume()
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
          else if (event.code === 4409) this.fail('There is no Shot to talk about yet')
          else this.finish()
        }
        this.ticker = setInterval(() => {
          this.speaking = Boolean(this.player?.speaking)
        }, 200)
      } catch (error) {
        this.fail(error.message)
      }
    },

    /** Hand over the microphone, once the user asks for it. */
    async useMic() {
      if (this.mic || !this.active) return
      try {
        this.mic = await openMic((chunk) => {
          if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(chunk)
        })
        this.muted = false
        this.mic.setMuted(false)
        this.listening = true
        this.notice = ''
      } catch (error) {
        this.notice =
          error.name === 'NotAllowedError'
            ? 'No microphone permission — typing still works.'
            : 'No microphone here — typing still works.'
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
      if (data.type === 'turn_complete') this.flushPending()
      else if (data.type === 'transcript') this.append(data.role, data.text)
      else if (data.type === 'tool') this.lines.push({ role: 'tool', text: data.text })
      else if (data.type === 'interrupted') this.player?.flush()
      else if (data.type === 'timeout') this.finish()
      else if (data.type === 'error') this.fail(data.text)
    },

    /** The question the user clicked, sent once the model has finished greeting. */
    flushPending() {
      if (!this.pending) return
      const text = this.pending
      this.pending = ''
      this.ask(text)
    },

    append(role, text) {
      const last = this.lines[this.lines.length - 1]
      if (last && last.role === role) last.text += text
      else this.lines.push({ role, text })
    },

    ask(text) {
      const question = (text || '').trim()
      if (!question) return
      if (this.socket?.readyState !== WebSocket.OPEN) {
        this.pending = question
        return
      }
      this.lines.push({ role: 'user', text: '' })
      this.socket.send(JSON.stringify({ type: 'text', text: question }))
    },

    toggleMute() {
      this.muted = !this.muted
      this.mic?.setMuted(this.muted)
      this.listening = Boolean(this.mic) && !this.muted
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
      const retryable = /1006|abnormal|Connection failed/i.test(message)
      this.teardown()
      if (retryable && !this.retried && this.open && this.shotId) {
        this.retried = true
        const asked = this.lines.filter((l) => l.role === 'user' && l.text).pop()
        this.pending = asked?.text || this.pending
        this.start(this.shotId, { keepNotice: true })
        this.notice = 'The session dropped; picking it up again…'
        return
      }
      this.error = message
      this.status = 'error'
    },

    teardown() {
      clearInterval(this.ticker)
      this.ticker = null
      this.mic?.close()
      this.mic = null
      this.listening = false
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
