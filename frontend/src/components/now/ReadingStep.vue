<script>
import { mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/** The pipeline, in the order the user's Shot goes through it. */
const STAGES = [
  { key: 'ingest.queued', label: 'The Shot is safely in Shoots' },
  { key: 'ingest.ingested', label: 'Reading the camera settings and pixels' },
  { key: 'analyst.analyzed', label: 'Three visual reads are looking at the Shot' },
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
    /** Which stages this Shot has already cleared. */
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
  <section class="page-shell py-8 md:py-12">
    <p class="eyebrow">Now · Reading {{ elapsed }}s</p>
    <div class="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
      <div class="surface-active overflow-hidden">
        <img v-if="thumb" :src="thumb" alt="" class="aspect-[4/3] w-full object-cover sm:aspect-[16/9]" />
        <div class="p-6 sm:p-8">
          <p class="eyebrow text-accent">Shoots is working</p>
          <h1 class="mt-4 t-hero">
            {{ shots.length > 1 ? `${shots.length} Shots are being read.` : 'Your Shot is being read.' }}
          </h1>
          <p class="mt-4 t-body">You can leave this screen. Shoots will keep working in the background.</p>
        </div>
      </div>
      <div class="surface p-5 sm:p-6">
        <p class="eyebrow">What is happening</p>
        <ul class="mt-5 min-w-0 space-y-4">
        <li v-for="row in rows" :key="row.key" class="flex items-start gap-3">
          <span
            class="mt-1.5 h-2 w-2 shrink-0 rounded-full"
            :class="row.active ? 'animate-pulse bg-accent' : row.complete ? 'bg-neutral-400' : 'bg-edge-strong'"
          />
          <span class="t-body" :class="row.active ? 'text-paper' : 'text-muted'">
            {{ row.label }}
          </span>
        </li>
        </ul>
        <p class="mt-7 border-t border-edge pt-5 t-meta">
          Three visual reads work separately. Shoots stores their agreement and confidence. One high-confidence responsible read can also retain a Technique.
        </p>
      </div>
    </div>
  </section>
</template>
