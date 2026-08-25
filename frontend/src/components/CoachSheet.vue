<script>
import { mapActions, mapState } from 'pinia'

import { useCoachStore } from '@/stores/coach'

/**
 * The Coach, as a sheet over whatever the user was looking at — it is a
 * conversation about the frame on screen, not a place you navigate to.
 * Typing works from the first second; the microphone is opt-in.
 */
export default {
  name: 'CoachSheet',
  data() {
    return { typed: '' }
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
    send() {
      this.ask(this.typed)
      this.typed = ''
    },
  },
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-40 flex items-end justify-center md:items-center md:p-6">
      <div class="absolute inset-0 bg-black/70" @click="close" />

      <section
        class="relative flex max-h-[82vh] w-full max-w-[560px] flex-col rounded-t-3xl border-t border-edge bg-panel md:rounded-3xl md:border"
      >
        <header class="flex items-center gap-3 border-b border-edge px-5 py-4">
          <span
            class="h-2 w-2 rounded-full"
            :class="speaking ? 'animate-pulse bg-accent' : status === 'live' ? 'bg-good' : 'bg-edge-strong'"
          />
          <h2 class="t-title">Coach</h2>
          <span class="t-meta">{{ state }}</span>
          <button type="button" class="ml-auto t-meta hover:text-neutral-200" @click="close">Close</button>
        </header>

        <div ref="scroll" class="min-h-24 flex-1 space-y-4 overflow-y-auto px-5 py-4">
          <p v-if="!lines.length" class="t-body text-neutral-500">
            It has the frame and the panel's read in front of it. Ask anything — or tell it what you do not have with
            you, and it will remember for the next experiment.
          </p>

          <template v-for="(line, i) in lines" :key="i">
            <p v-if="line.role === 'tool'" class="t-meta">→ {{ line.text }}</p>
            <p v-else-if="line.role === 'user' && line.text" class="t-body text-neutral-400">{{ line.text }}</p>
            <p v-else class="t-body text-neutral-100">{{ line.text }}</p>
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
            v-model="typed"
            type="text"
            :disabled="!active"
            placeholder="Ask about this frame"
            class="min-w-0 flex-1 rounded-xl border border-edge bg-panel-2 px-4 py-3 text-[15px] text-neutral-100 placeholder:text-neutral-600"
          />
          <button
            v-if="canMic && !listening"
            type="button"
            class="rounded-xl border border-edge-strong px-3 py-3 text-neutral-400 hover:text-neutral-100"
            title="Speak instead"
            :disabled="!active"
            @click="useMic"
          >
            <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
              <path d="M12 4a3 3 0 013 3v5a3 3 0 01-6 0V7a3 3 0 013-3zM5 11a7 7 0 0014 0M12 18v3" />
            </svg>
          </button>
          <button
            v-else-if="listening || muted"
            type="button"
            class="rounded-xl border px-3 py-3"
            :class="muted ? 'border-edge-strong text-neutral-500' : 'border-good/50 text-good'"
            :title="muted ? 'Unmute' : 'Mute'"
            @click="toggleMute"
          >
            <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
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
