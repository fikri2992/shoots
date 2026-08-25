<script>
import { mapActions, mapState } from 'pinia'

import DisclosureRow from '@/components/DisclosureRow.vue'
import ShootAction from '@/components/ShootAction.vue'
import VerdictNote from '@/components/VerdictNote.vue'
import { useShootsStore } from '@/stores/shoots'

const EXIF_LABELS = {
  shutter_min_s: (v) => `shutter at least ${shutter(v)}`,
  shutter_max_s: (v) => `shutter no slower than ${shutter(v)}`,
  aperture_max: (v) => `aperture f/${v} or wider`,
  aperture_min: (v) => `aperture f/${v} or narrower`,
  iso_min: (v) => `ISO ${v} or higher`,
  iso_max: (v) => `ISO ${v} or lower`,
  focal_min_mm: (v) => `${v} mm or longer`,
  focal_max_mm: (v) => `${v} mm or shorter`,
  flash: (v) => (v ? 'flash must fire' : 'no flash'),
}

const RENDER_MINUTES = 10

function shutter(seconds) {
  return seconds >= 1 ? `${seconds} s` : `1/${Math.round(1 / seconds)} s`
}

function clock(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/**
 * The one thing to do today. Media first and full width, one title, the
 * criteria in plain sentences, and the shutter pinned in the thumb zone.
 * Everything that explains rather than instructs sits behind a disclosure.
 */
export default {
  name: 'QuestHero',
  components: { DisclosureRow, ShootAction, VerdictNote },
  props: { experiment: { type: Object, required: true } },
  data() {
    return { muted: true }
  },
  computed: {
    ...mapState(useShootsStore, ['busy']),
    clipUrl() {
      return this.experiment.reference_clip ? `/api/blobs/${this.experiment.reference_clip}` : ''
    },
    /** The Director takes about a minute; after that, stop promising a clip. */
    rendering() {
      if (this.clipUrl || this.experiment.status !== 'open') return false
      return (Date.now() - new Date(this.experiment.issued_at)) / 60000 < RENDER_MINUTES
    },
    technique() {
      return this.experiment.technique_id.replace(/_/g, ' ')
    },
    steps() {
      const brief = (this.experiment.brief || '').trim()
      const lines = brief.includes('\n') ? brief.split(/\n+/) : brief.split(/\s+(?=\d{1,2}[.)]\s)/)
      return lines.map((line) => line.replace(/^\s*\d+[.)]\s*/, '').trim()).filter(Boolean)
    },
    criteria() {
      return this.experiment.criteria?.text || []
    },
    cameraRules() {
      return Object.entries(this.experiment.criteria?.exif || {})
        .filter(([, value]) => value !== null && value !== undefined)
        .map(([key, value]) => EXIF_LABELS[key]?.(value) || `${key}: ${value}`)
    },
    /** One line: when it lands, why then, how long is left. */
    when() {
      const q = this.experiment
      const bits = []
      if (q.timing) {
        if (q.deliver_at && new Date(q.deliver_at) > Date.now()) bits.push(`Lands ${clock(q.deliver_at)}`)
        bits.push(q.timing.reason)
        if (q.timing.anchor_at) bits.push(`${q.timing.anchor} ${clock(q.timing.anchor_at)}`)
      }
      if (q.status === 'open' && q.due_at) {
        const days = Math.ceil((new Date(q.due_at) - Date.now()) / 86400000)
        bits.push(days <= 0 ? 'due today' : `${days} day${days === 1 ? '' : 's'} left`)
      }
      return bits.filter(Boolean).join(' · ')
    },
    attempts() {
      return [...(this.experiment.verdicts || [])].reverse()
    },
    host() {
      return (ref) => {
        try {
          const url = new URL(ref.url)
          return url.hostname.startsWith('vertexaisearch') ? ref.title : url.hostname
        } catch {
          return ref.title
        }
      }
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['skipQuest']),
  },
}
</script>

<template>
  <article class="pb-32">
    <div v-if="clipUrl" class="relative bg-black">
      <video :src="clipUrl" class="mx-auto max-h-[46vh] w-full object-contain" autoplay loop playsinline :muted="muted" />
      <p class="absolute bottom-3 left-3 rounded-full bg-black/70 px-3 py-1 t-num text-[11px] text-neutral-400">
        what it looks like · Veo
      </p>
      <button
        type="button"
        class="absolute bottom-3 right-3 rounded-full bg-black/70 px-3 py-1 t-num text-[11px] text-neutral-200"
        @click="muted = !muted"
      >
        {{ muted ? 'sound off' : 'sound on' }}
      </button>
    </div>

    <div class="col gutter">
      <p v-if="rendering" class="pt-5 t-meta text-accent">The Director is rendering a reference clip…</p>

      <p class="pt-6 t-meta">{{ experiment.status === 'open' ? 'Today' : 'Experiment' }} · {{ technique }}</p>
      <h1 class="mt-1 t-hero">{{ experiment.title }}</h1>
      <p v-if="when" class="mt-2 t-meta text-accent">{{ when }}</p>

      <ul class="mt-6 space-y-2">
        <li v-for="(c, i) in criteria" :key="i" class="flex gap-3 t-body">
          <span class="mt-2 h-1 w-1 shrink-0 rounded-full bg-neutral-600" />
          <span>{{ c }}</span>
        </li>
      </ul>
      <p v-if="cameraRules.length" class="mt-3 t-meta">Camera: {{ cameraRules.join(' · ') }}</p>

      <div v-if="attempts.length" class="mt-8 rounded-2xl bg-panel p-4">
        <VerdictNote :verdict="attempts[0]" />
        <p v-if="attempts.length > 1" class="mt-3 t-meta">{{ attempts.length }} attempts so far</p>
      </div>

      <div class="mt-8">
        <DisclosureRow label="How to shoot it" :count="steps.length">
          <ol class="space-y-3">
            <li v-for="(step, i) in steps" :key="i" class="flex gap-3 t-body">
              <span class="w-4 shrink-0 t-num text-[12px] text-neutral-600">{{ i + 1 }}</span>
              <span>{{ step }}</span>
            </li>
          </ol>
        </DisclosureRow>

        <DisclosureRow label="Why the Scout picked this">
          <p class="t-body">{{ experiment.why_now }}</p>
        </DisclosureRow>

        <DisclosureRow v-if="experiment.references.length" label="What it read" :count="experiment.references.length">
          <ul class="space-y-2">
            <li v-for="(ref, i) in experiment.references" :key="i">
              <a :href="ref.url" target="_blank" rel="noopener" class="t-body text-neutral-400 hover:text-neutral-100">
                {{ host(ref) }} ↗
              </a>
            </li>
          </ul>
        </DisclosureRow>
      </div>
    </div>

    <div
      v-if="experiment.status === 'open'"
      class="sticky bottom-16 z-10 mt-10 border-t border-edge bg-ink/95 backdrop-blur md:bottom-0"
      style="padding-bottom: calc(0.75rem + env(safe-area-inset-bottom))"
    >
      <div class="col gutter flex items-center gap-3 pt-3">
        <div class="flex-1"><ShootAction :experiment-id="experiment.id" label="Shoot for this" /></div>
        <button type="button" class="btn-quiet px-4" :disabled="busy === 'skip'" @click="skipQuest(experiment.id)">
          Skip
        </button>
      </div>
    </div>
  </article>
</template>
