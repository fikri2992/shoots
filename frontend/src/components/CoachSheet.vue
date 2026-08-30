<script>
import { mapActions, mapState } from 'pinia'

import { useCoachStore } from '@/stores/coach'

/**
 * The Coach, as a sheet over whatever the user was looking at — it is a
 * conversation about the Shot on screen, not a place you navigate to.
 * Typing works from the first second; the microphone is opt-in.
 */
export default {
  name: 'CoachSheet',
  data() {
    return { typed: '', previousFocus: null, bodyOverflow: '' }
  },
  computed: {
    ...mapState(useCoachStore, ['open', 'status', 'lines', 'error', 'notice', 'listening', 'muted', 'speaking', 'active']),
    state() {
      if (this.status === 'connecting') return 'connecting…'
      if (this.status === 'live') return this.speaking ? 'talking' : this.listening ? 'listening' : 'ready'
      if (this.status === 'ended') return 'ended'
      if (this.status === 'error') return 'failed'
      return ''
    },
    canMic() {
      return typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia) && 'AudioWorklet' in window
    },
  },
  watch: {
    open: {
      immediate: true,
      handler(value) {
        if (value) this.activateDialog()
        else this.deactivateDialog()
      },
    },
    lines: {
      deep: true,
      handler() {
        this.$nextTick(() => {
          const box = this.$refs.scroll
          if (box) box.scrollTop = box.scrollHeight
        })
      },
    },
  },
  methods: {
    ...mapActions(useCoachStore, ['close', 'ask', 'useMic', 'toggleMute']),
    activateDialog() {
      if (typeof document === 'undefined') return
      this.previousFocus = document.activeElement
      this.bodyOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', this.onDialogKeydown)
      this.$nextTick(() => this.$refs.initialFocus?.focus())
    },
    deactivateDialog() {
      if (typeof document === 'undefined') return
      window.removeEventListener('keydown', this.onDialogKeydown)
      document.body.style.overflow = this.bodyOverflow
      if (this.previousFocus?.isConnected) this.previousFocus.focus()
      this.previousFocus = null
    },
    onDialogKeydown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        this.close()
        return
      }
      if (event.key !== 'Tab') return
      const focusable = [
        ...(this.$refs.dialog?.querySelectorAll(
          'button:not([disabled]), input:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
        ) || []),
      ]
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    },
    send() {
      this.ask(this.typed)
      this.typed = ''
    },
  },
  beforeUnmount() {
    this.deactivateDialog()
  },
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-40 flex items-end justify-center md:items-center md:p-6">
      <div class="absolute inset-0 bg-black/76" @click="close" />

      <section
        ref="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="coach-dialog-title"
        class="relative flex max-h-[84vh] w-full max-w-[580px] flex-col rounded-t-[28px] border-t border-edge bg-panel shadow-2xl md:rounded-[28px] md:border"
      >
        <div class="mx-auto mt-3 h-1 w-10 rounded-full bg-edge-strong md:hidden" />
        <header class="flex items-center gap-3 border-b border-edge px-5 py-4">
          <span
            class="h-2 w-2 rounded-full"
            :class="speaking ? 'animate-pulse bg-accent' : status === 'live' ? 'bg-paper' : 'bg-edge-strong'"
          />
          <div>
            <p class="eyebrow">Shot Coach</p>
            <h2 id="coach-dialog-title" class="text-[17px] font-semibold text-paper">Ask about this read</h2>
          </div>
          <span class="t-meta">{{ state }}</span>
          <button type="button" class="tap-target ml-auto px-2 t-meta hover:text-paper" @click="close">Close</button>
        </header>

        <div ref="scroll" class="min-h-24 flex-1 space-y-4 overflow-y-auto px-5 py-4">
          <p v-if="!lines.length" class="rounded-2xl border border-edge bg-panel-2/45 p-4 t-body text-muted">
            The Coach has this Shot, its Analysis, and the active Experiment. Ask one specific question, or state a constraint you want remembered.
          </p>

          <template v-for="(line, i) in lines" :key="i">
            <p v-if="line.role === 'tool'" class="t-meta">→ {{ line.text }}</p>
            <p v-else-if="line.role === 'user' && line.text" class="ml-8 rounded-2xl border border-edge bg-panel-2 px-4 py-3 t-body text-neutral-300">{{ line.text }}</p>
            <p v-else class="mr-8 rounded-2xl border border-edge bg-ink px-4 py-3 t-body text-paper">{{ line.text }}</p>
          </template>

          <p v-if="error" class="t-body text-bad">{{ error }}</p>
          <p v-if="notice" class="t-meta">{{ notice }}</p>
        </div>

        <form
          class="flex items-center gap-2 border-t border-edge px-5 py-4"
          style="padding-bottom: calc(1rem + env(safe-area-inset-bottom))"
          @submit.prevent="send"
        >
          <input
            ref="initialFocus"
            v-model="typed"
            type="text"
            :disabled="!active"
            placeholder="Ask about this Shot"
            class="min-w-0 flex-1 rounded-xl border border-edge bg-panel-2 px-4 py-3 text-[15px] text-paper outline-none placeholder:text-muted focus:border-accent"
          />
          <button
            v-if="canMic && !listening"
            type="button"
            class="min-h-11 min-w-11 rounded-xl border border-edge-strong px-3 py-3 text-neutral-400 hover:text-neutral-100"
            title="Speak instead"
            aria-label="Speak instead"
            :disabled="!active"
            @click="useMic"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
              <path d="M12 4a3 3 0 013 3v5a3 3 0 01-6 0V7a3 3 0 013-3zM5 11a7 7 0 0014 0M12 18v3" />
            </svg>
          </button>
          <button
            v-else-if="listening || muted"
            type="button"
            class="min-h-11 min-w-11 rounded-xl border px-3 py-3"
            :class="muted ? 'border-edge-strong text-muted' : 'border-accent/50 text-accent'"
            :title="muted ? 'Unmute' : 'Mute'"
            :aria-label="muted ? 'Unmute microphone' : 'Mute microphone'"
            @click="toggleMute"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
              <path d="M12 4a3 3 0 013 3v5a3 3 0 01-6 0V7a3 3 0 013-3zM5 11a7 7 0 0014 0M12 18v3" />
              <path v-if="muted" d="M4 4l16 16" />
            </svg>
          </button>
          <button type="submit" class="btn px-4 py-3" :disabled="!active">Ask</button>
        </form>
      </section>
    </div>
  </Teleport>
</template>
