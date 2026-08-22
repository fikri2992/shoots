<script>
import { mapActions, mapState } from 'pinia'

import ShootButton from '@/components/ShootButton.vue'
import StatusChip from '@/components/StatusChip.vue'
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

function shutter(seconds) {
  return seconds >= 1 ? `${seconds} s` : `1/${Math.round(1 / seconds)} s`
}

/** Today's quest: the thing the user acts on. Everything else is context. */
export default {
  name: 'QuestCard',
  components: { ShootButton, StatusChip },
  props: {
    quest: { type: Object, required: true },
    compact: { type: Boolean, default: false },
  },
  data() {
    return { open: !this.compact, muted: true }
  },
  computed: {
    ...mapState(useShootsStore, ['busy']),
    clipUrl() {
      return this.quest.reference_clip ? `/api/blobs/${this.quest.reference_clip}` : ''
    },
    steps() {
      const brief = this.quest.brief.trim()
      // Older quests may carry "1. … 2. …" on one line; split on the numbering.
      const lines = brief.includes('\n') ? brief.split(/\n+/) : brief.split(/\s+(?=\d{1,2}[.)]\s)/)
      return lines.map((line) => line.replace(/^\s*\d+[.)]\s*/, '').trim()).filter(Boolean)
    },
    hardCriteria() {
      return Object.entries(this.quest.criteria.exif)
        .filter(([, value]) => value !== null && value !== undefined)
        .map(([key, value]) => EXIF_LABELS[key]?.(value) || `${key}: ${value}`)
    },
    technique() {
      return this.quest.technique_id.replace(/_/g, ' ')
    },
    verdicts() {
      return [...this.quest.verdicts].reverse()
    },
    due() {
      if (!this.quest.due_at) return ''
      const days = Math.ceil((new Date(this.quest.due_at) - Date.now()) / 86400000)
      return days <= 0 ? 'due today' : `${days} day${days === 1 ? '' : 's'} left`
    },
    isOpen() {
      return this.quest.status === 'open'
    },
    /** "Lands at 17:10 · fifty minutes before sunset where you last shot." */
    timingLine() {
      const q = this.quest
      if (!q.timing) return ''
      const time = (iso) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      const anchor = q.timing.anchor_at ? ` (${q.timing.anchor} ${time(q.timing.anchor_at)})` : ''
      if (q.delivered_at) return `Sent ${time(q.delivered_at)} · ${q.timing.reason}${anchor}`
      if (q.deliver_at && new Date(q.deliver_at) > Date.now()) {
        return `Lands on your phone at ${time(q.deliver_at)} · ${q.timing.reason}${anchor}`
      }
      return `${q.timing.reason}${anchor}`
    },
    reference() {
      return (ref) => {
        try {
          return new URL(ref.url).hostname.startsWith('vertexaisearch') ? ref.title : new URL(ref.url).hostname
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
  <section class="rounded-xl border border-edge bg-panel">
    <header class="flex items-start justify-between gap-3 p-4">
      <div>
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">
          {{ isOpen ? "Today's quest" : 'Quest' }} · {{ technique }}
        </p>
        <h2 class="mt-1 text-xl font-semibold leading-tight">{{ quest.title }}</h2>
        <p class="mt-2 text-sm text-neutral-400">{{ quest.why_now }}</p>
        <p v-if="timingLine" class="mt-1.5 text-xs text-amber-200/80">{{ timingLine }}</p>
      </div>
      <div class="flex shrink-0 flex-col items-end gap-1">
        <StatusChip :status="quest.status" />
        <span v-if="isOpen" class="text-[11px] text-neutral-500">{{ due }}</span>
      </div>
    </header>

    <button
      v-if="compact"
      type="button"
      class="w-full border-t border-edge px-4 py-2 text-left text-xs text-neutral-400 hover:text-neutral-200"
      @click="open = !open"
    >
      {{ open ? 'Hide details' : 'Show brief and criteria' }}
    </button>

    <div v-if="open" class="space-y-4 border-t border-edge p-4">
      <div v-if="clipUrl" class="flex gap-4">
        <button
          type="button"
          class="relative w-36 shrink-0 overflow-hidden rounded-lg bg-black"
          :title="muted ? 'Tap for sound' : 'Tap to mute'"
          @click="muted = !muted"
        >
          <video :src="clipUrl" class="aspect-[9/16] w-full object-cover" autoplay loop playsinline :muted="muted" />
          <span class="absolute bottom-1.5 right-1.5 rounded bg-black/60 px-1.5 py-0.5 font-mono text-[10px] text-neutral-200">
            {{ muted ? 'sound off' : 'sound on' }}
          </span>
        </button>
        <div class="text-xs text-neutral-400">
          <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Reference</p>
          <p class="mt-1">What the finished technique looks like, rendered by the Director for this quest.</p>
          <p class="mt-2 font-mono text-[10px] text-neutral-600">Veo 3.1</p>
        </div>
      </div>
      <p v-else-if="isOpen" class="text-[11px] text-neutral-600">Reference clip rendering…</p>

      <ol class="space-y-2 text-sm text-neutral-200">
        <li v-for="(step, i) in steps" :key="i" class="flex gap-3">
          <span class="w-5 shrink-0 text-right font-mono text-neutral-500">{{ i + 1 }}</span>
          <span>{{ step }}</span>
        </li>
      </ol>

      <div>
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">What counts as done</p>
        <ul class="mt-1 space-y-1 text-sm">
          <li v-for="(c, i) in hardCriteria" :key="'h' + i" class="flex gap-2 text-amber-200">
            <span class="font-mono text-[11px] leading-5 text-amber-400">EXIF</span><span>{{ c }}</span>
          </li>
          <li v-for="(c, i) in quest.criteria.text" :key="'t' + i" class="flex gap-2 text-neutral-300">
            <span class="font-mono text-[11px] leading-5 text-sky-400">SEEN</span><span>{{ c }}</span>
          </li>
        </ul>
      </div>

      <div v-if="quest.references.length" class="flex flex-wrap gap-2">
        <a
          v-for="(ref, i) in quest.references"
          :key="i"
          :href="ref.url"
          target="_blank"
          rel="noopener"
          class="rounded-full border border-edge-strong px-2.5 py-0.5 text-[11px] text-neutral-400 hover:text-neutral-100"
        >
          {{ reference(ref) }}
        </a>
      </div>

      <div v-if="verdicts.length" class="space-y-2">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Attempts</p>
        <div
          v-for="v in verdicts"
          :key="v.shot_id"
          class="rounded-lg border p-3 text-sm"
          :class="v.passed ? 'border-emerald-800/60 bg-emerald-950/30' : 'border-edge bg-panel-2'"
        >
          <div class="mb-1 flex items-center gap-2 text-xs">
            <span :class="v.passed ? 'text-emerald-400' : 'text-amber-400'">
              {{ v.passed ? 'Passed' : 'Not yet' }}
            </span>
            <RouterLink :to="{ name: 'shot', params: { shotId: v.shot_id } }" class="text-neutral-500 hover:text-neutral-200">
              view shot
            </RouterLink>
            <RouterLink
              v-if="!v.passed"
              :to="{ name: 'shot', params: { shotId: v.shot_id }, hash: '#coach' }"
              class="ml-auto rounded-full border border-teal-900 px-2 py-0.5 text-teal-300 hover:border-teal-600"
            >
              Ask the Coach why
            </RouterLink>
          </div>
          <p class="whitespace-pre-line text-neutral-200">{{ v.feedback }}</p>
        </div>
      </div>

      <div v-if="isOpen" class="flex items-center gap-2 pt-1">
        <ShootButton :quest-id="quest.id" label="Shoot for this quest" />
        <button
          type="button"
          class="rounded-lg border border-edge-strong px-3 py-2 text-sm text-neutral-400 hover:text-neutral-100 disabled:opacity-40"
          :disabled="busy === 'skip'"
          @click="skipQuest(quest.id)"
        >
          Skip
        </button>
      </div>
    </div>
  </section>
</template>
