<script>
import { mapActions, mapState } from 'pinia'

import { useCoachStore } from '@/stores/coach'

/** Talk with the Coach about this frame. One tap to start, one to hang up. */
export default {
  name: 'CoachPanel',
  props: { shotId: { type: String, required: true } },
  data() {
    return { typed: '' }
  },
  computed: {
    ...mapState(useCoachStore, ['status', 'lines', 'error', 'muted', 'speaking', 'active']),
    ...mapState(useCoachStore, { coachShotId: 'shotId' }),
    mine() {
      return this.coachShotId === this.shotId
    },
    supported() {
      return typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia) && 'AudioWorklet' in window
    },
    stateLabel() {
      if (!this.mine) return ''
      if (this.status === 'connecting') return 'Connecting…'
      if (this.status === 'live') return this.speaking ? 'Coach is talking' : this.muted ? 'Muted' : 'Listening'
      if (this.status === 'ended') return 'Session ended'
      return ''
    },
  },
  methods: {
    ...mapActions(useCoachStore, ['start', 'stop', 'ask', 'toggleMute']),
    send() {
      this.ask(this.typed)
      this.typed = ''
    },
  },
  beforeUnmount() {
    if (this.mine && this.active) this.stop()
  },
}
</script>

<template>
  <section class="rounded-xl border border-edge bg-panel p-4">
    <div class="flex items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold">Talk it through</h2>
        <p class="text-xs text-neutral-500">
          {{ mine && active ? stateLabel : 'Voice review with the Coach. It sees the frame and the read above.' }}
        </p>
      </div>
      <button
        v-if="!(mine && active)"
        type="button"
        class="rounded-lg bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-900 hover:bg-white disabled:opacity-50"
        :disabled="!supported"
        @click="start(shotId)"
      >
        Talk about this shot
      </button>
      <div v-else class="flex items-center gap-2">
        <span class="h-2.5 w-2.5 rounded-full" :class="speaking ? 'animate-pulse bg-sky-400' : muted ? 'bg-neutral-600' : 'bg-emerald-400'" />
        <button type="button" class="rounded-lg border border-edge-strong px-2.5 py-1.5 text-xs text-neutral-300 hover:text-neutral-100" @click="toggleMute">
          {{ muted ? 'Unmute' : 'Mute' }}
        </button>
        <button type="button" class="rounded-lg border border-red-900 px-2.5 py-1.5 text-xs text-red-200 hover:bg-red-950/40" @click="stop">
          End
        </button>
      </div>
    </div>

    <p v-if="!supported" class="mt-2 text-xs text-neutral-600">This browser cannot capture audio for a live session.</p>
    <p v-if="mine && error" class="mt-3 rounded-lg border border-red-900 bg-red-950/40 px-3 py-2 text-xs text-red-200">{{ error }}</p>

    <div v-if="mine && lines.length" class="mt-3 max-h-64 space-y-2 overflow-y-auto text-sm">
      <p v-for="(line, i) in lines" :key="i" :class="line.role === 'model' ? 'text-neutral-100' : 'text-neutral-500'">
        <span class="mr-1 font-mono text-[10px] uppercase text-neutral-600">{{ line.role === 'model' ? 'coach' : 'you' }}</span>{{ line.text }}
      </p>
    </div>

    <form v-if="mine && status === 'live'" class="mt-3 flex gap-2" @submit.prevent="send">
      <input
        v-model="typed"
        type="text"
        placeholder="Or type a question"
        class="min-w-0 flex-1 rounded-lg border border-edge bg-panel-2 px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-600"
      />
      <button type="submit" class="rounded-lg border border-edge-strong px-3 py-2 text-sm text-neutral-300 hover:text-neutral-100">Ask</button>
    </form>
  </section>
</template>
