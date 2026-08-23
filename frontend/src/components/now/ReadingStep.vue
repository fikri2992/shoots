<script>
import { mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/** The pipeline, in the order the user's frame goes through it. */
const STAGES = [
  { key: 'ingest.queued', label: 'landed in your Drive folder' },
  { key: 'ingest.ingested', label: 'file read: camera settings, grid, thumbnail' },
  { key: 'analyst.analyzed', label: 'three lenses reading the frame' },
]

/**
 * The wait is the only moment the user can see the agents work, so it narrates
 * instead of spinning. Stages come from the same events the audit trail uses.
 */
export default {
  name: 'ReadingStep',
  props: { shots: { type: Array, required: true } },
  data() {
    return { now: Date.now(), ticker: null }
  },
  computed: {
    ...mapState(useShootsStore, ['events']),
    current() {
      return this.shots[0]
    },
    thumb() {
      const blobs = this.current?.shot.blobs || {}
      const key = blobs.thumb ? 'thumb' : blobs.original ? 'original' : ''
      return key ? `/api/blobs/${blobs[key]}` : ''
    },
    /** Which stages this frame has already cleared. */
    done() {
      const mine = this.events.filter((e) => e.shot_id === this.current?.shot.id)
      return new Set(mine.map((e) => `${e.agent}.${e.stage}`))
    },
    rows() {
      const done = this.done
      let running = true
      return STAGES.map((stage) => {
        const complete = done.has(stage.key)
        const active = running && !complete
        if (active) running = false
        return { ...stage, complete, active }
      })
    },
    elapsed() {
      const started = this.current?.shot.ingested_at
      if (!started) return 0
      return Math.max(0, Math.round((this.now - new Date(started)) / 1000))
    },
  },
  created() {
    this.ticker = setInterval(() => {
      this.now = Date.now()
    }, 1000)
  },
  beforeUnmount() {
    clearInterval(this.ticker)
  },
}
</script>

<template>
  <section class="col gutter pt-10">
    <p class="t-meta text-accent">Reading it now · {{ elapsed }}s</p>
    <h1 class="mt-2 t-hero">
      {{ shots.length > 1 ? `${shots.length} frames are being read.` : 'Your frame is being read.' }}
    </h1>

    <div class="mt-6 flex gap-4">
      <img v-if="thumb" :src="thumb" alt="" class="h-28 w-28 shrink-0 rounded-xl object-cover" />
      <ul class="min-w-0 flex-1 space-y-3">
        <li v-for="row in rows" :key="row.key" class="flex items-start gap-3">
          <span
            class="mt-1.5 h-2 w-2 shrink-0 rounded-full"
            :class="row.complete ? 'bg-good' : row.active ? 'animate-pulse bg-accent' : 'bg-edge-strong'"
          />
          <span class="t-body" :class="row.complete ? 'text-neutral-500' : row.active ? 'text-neutral-100' : 'text-neutral-600'">
            {{ row.label }}
          </span>
        </li>
      </ul>
    </div>

    <p class="mt-8 t-body text-neutral-400">
      A technician, a composer and a storyteller each read the frame on their own, then have to agree before
      anything is called a technique you used. It takes about a minute.
    </p>
    <p class="mt-4 t-meta">You can close this. The review lands in your Drive either way.</p>
  </section>
</template>
