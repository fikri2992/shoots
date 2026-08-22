<script>
import { mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

const AGENT_STYLE = {
  ingest: 'text-neutral-300',
  analyst: 'text-sky-300',
  cartographer: 'text-violet-300',
  judge: 'text-emerald-300',
  scout: 'text-amber-300',
  director: 'text-rose-300',
  coach: 'text-teal-300',
  scribe: 'text-lime-300',
  scheduler: 'text-neutral-500',
  drive: 'text-neutral-400',
  user: 'text-neutral-400',
}

/** Every agent step, newest first. The audit trail as a timeline. */
export default {
  name: 'ActivityFeed',
  props: { limit: { type: Number, default: 60 } },
  computed: {
    ...mapState(useShootsStore, ['events']),
    rows() {
      return this.events.slice(0, this.limit).map((e) => ({
        ...e,
        style: AGENT_STYLE[e.agent] || 'text-neutral-400',
        when: new Date(e.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        line: this.describe(e),
      }))
    },
  },
  methods: {
    describe(e) {
      const d = e.detail || {}
      switch (`${e.agent}.${e.stage}`) {
        case 'ingest.queued':
          return `queued ${d.filename || ''}${d.via === 'shoot' ? ' from the camera' : ''}`
        case 'ingest.ingested':
          return `ingested ${d.kind || ''}${d.grid ? `, grid ${d.grid}` : ''}${d.exif?.exposure_time_s ? `, ${this.shutter(d.exif.exposure_time_s)} f/${d.exif.f_number}` : ''}`
        case 'ingest.failed':
          return `failed: ${d.error}`
        case 'analyst.analyzed':
          return `score ${d.score}/10 · ${(d.techniques || []).map((t) => `${t.id.replace(/_/g, ' ')} ${Math.round(t.confidence * 100)}%`).join(', ') || 'no technique tagged'}`
        case 'cartographer.mapped':
          return (d.changes || []).map((c) => `${c.technique_id.replace(/_/g, ' ')}: ${c.from} → ${c.to}`).join(' · ')
        case 'judge.passed':
          return `passed ${d.technique_id?.replace(/_/g, ' ')}`
        case 'judge.not_passed':
          return `not passed: ${this.checks(d)}`
        case 'scout.issued':
          return `issued "${d.title}" · ${d.why}`
        case 'director.storyboard':
          return `storyboarded: ${(d.video_prompt || '').slice(0, 90)}…`
        case 'director.clip_ready':
          return `reference clip ready, ${d.seconds}s`
        case 'scribe.reviewed':
          return `wrote the review into Drive: ${d.name}`
        case 'scribe.updated':
          return `updated the review in Drive: ${d.name}`
        case 'scout.delivered':
          return `delivered the quest · ${d.timing || ''}`
        case 'coach.session':
          return `voice session, ${d.turns} turn${d.turns === 1 ? '' : 's'} in ${d.seconds}s`
        case 'coach.noted':
          return `remembered: ${[d.missing_gear?.length ? `no ${d.missing_gear.join(', ')}` : '', ...(d.notes || [])].filter(Boolean).join(' · ')}`
        case 'scout.nothing_to_issue':
          return 'nothing left to issue within your constraints'
        case 'scheduler.daily':
          return `daily tick: ${d.synced} synced, ${d.issued} issued, ${d.expired} expired`
        case 'scheduler.expired':
          return `expired ${d.technique_id?.replace(/_/g, ' ')}`
        case 'drive.connected':
          return d.mode === 'local' ? 'connected local folder' : `connected folder, shared with ${d.shared_with}`
        case 'user.skipped':
          return `skipped ${d.technique_id?.replace(/_/g, ' ')}`
        default:
          return e.stage
      }
    },
    checks(d) {
      const exif = Object.entries(d.exif_checks || {}).map(([k, v]) => `${k.replace(/_/g, ' ')} ${v === null ? '?' : v ? 'ok' : 'no'}`)
      const vision = Object.entries(d.vision_checks || {}).map(([k, v]) => `${k.replace(/_/g, ' ')} ${Math.round(v * 100)}%`)
      return [...exif, ...vision].join(', ')
    },
    shutter(s) {
      return s >= 1 ? `${s}s` : `1/${Math.round(1 / s)}`
    },
  },
}
</script>

<template>
  <section class="rounded-xl border border-edge bg-panel">
    <header class="flex items-baseline justify-between p-4 pb-2">
      <h2 class="text-sm font-semibold">Activity</h2>
      <span class="text-xs text-neutral-500">{{ events.length }} events</span>
    </header>
    <ol class="divide-y divide-edge">
      <li v-for="r in rows" :key="r.id" class="flex gap-3 px-4 py-2 text-sm">
        <span class="w-16 shrink-0 font-mono text-[11px] leading-5 text-neutral-600">{{ r.when }}</span>
        <span class="w-24 shrink-0 text-xs font-medium leading-5" :class="r.style">{{ r.agent }}</span>
        <span class="min-w-0 flex-1 break-words text-neutral-300">
          <RouterLink
            v-if="r.shot_id"
            :to="{ name: 'shot', params: { shotId: r.shot_id } }"
            class="hover:text-neutral-100"
          >
            {{ r.line }}
          </RouterLink>
          <template v-else>{{ r.line }}</template>
        </span>
      </li>
      <li v-if="!rows.length" class="px-4 py-6 text-center text-sm text-neutral-500">
        Nothing yet. Connect a folder and drop a photo in.
      </li>
    </ol>
  </section>
</template>
