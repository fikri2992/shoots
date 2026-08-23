<script>
import { mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/**
 * The audit trail, condensed. The store keeps every write; a human does not
 * need to read "remembered: no tripod" four times, so identical lines fold
 * into one row with a count.
 */
export default {
  name: 'AgentLog',
  props: { limit: { type: Number, default: 40 } },
  computed: {
    ...mapState(useShootsStore, ['events']),
    rows() {
      const out = []
      for (const event of this.events) {
        const line = this.describe(event)
        if (!line) continue
        const last = out[out.length - 1]
        if (last && last.agent === event.agent && last.line === line) {
          last.repeats += 1
          continue
        }
        out.push({
          id: event.id,
          agent: event.agent,
          line,
          repeats: 1,
          shot_id: event.shot_id,
          when: new Date(event.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          day: new Date(event.at).toLocaleDateString(),
        })
        if (out.length >= this.limit) break
      }
      return out
    },
  },
  methods: {
    describe(e) {
      const d = e.detail || {}
      switch (`${e.agent}.${e.stage}`) {
        case 'ingest.queued':
          return `took in ${d.filename || 'a file'}`
        case 'ingest.ingested':
          return `read the file · grid ${d.grid || ''}`
        case 'ingest.failed':
          return `could not read it: ${d.error}`
        case 'analyst.analyzed': {
          const seen = (d.techniques || [])
            .filter((t) => t.agreement >= 2)
            .map((t) => t.id.replace(/_/g, ' '))
            .join(', ')
          return `scored it ${d.score}/10${seen ? ` · agreed on ${seen}` : ''}`
        }
        case 'cartographer.mapped':
          return (d.changes || [])
            .map((c) => `${c.technique_id.replace(/_/g, ' ')}: ${c.from} → ${c.to}`)
            .join(' · ')
        case 'judge.passed':
          return `passed ${d.technique_id?.replace(/_/g, ' ')}`
        case 'judge.not_passed':
          return `not yet: ${d.technique_id?.replace(/_/g, ' ')}`
        case 'judge.preflight':
          return d.ready ? `pre-flight cleared it · ${d.say}` : `pre-flight said shoot again · ${d.say}`
        case 'scout.issued':
          return `issued “${d.title}” · ${d.why || ''}`
        case 'scout.delivered':
          return `sent it to your phone · ${d.timing || ''}`
        case 'scout.nothing_to_issue':
          return 'found nothing it could ask for within your constraints'
        case 'director.storyboard':
          return 'storyboarded the reference clip'
        case 'director.clip_ready':
          return `rendered the reference clip, ${d.seconds}s`
        case 'scribe.reviewed':
        case 'scribe.updated':
          return `wrote the review into Drive · ${d.name}`
        case 'coach.session':
          return `talked it through, ${d.turns} turn${d.turns === 1 ? '' : 's'} in ${d.seconds}s`
        case 'coach.issued_by_voice':
          return `issued “${d.title}” because you asked out loud`
        case 'coach.noted':
          return `remembered: ${[d.missing_gear?.length ? `no ${d.missing_gear.join(', ')}` : '', ...(d.notes || [])]
            .filter(Boolean)
            .join(' · ')}`
        case 'scheduler.daily':
          return `daily round: ${d.synced} synced, ${d.issued} issued`
        case 'scheduler.expired':
          return `${d.technique_id?.replace(/_/g, ' ')} is going rusty`
        case 'drive.connected':
          return 'connected your Drive folder'
        case 'user.skipped':
          return `you skipped ${d.technique_id?.replace(/_/g, ' ')}`
        default:
          return ''
      }
    },
  },
}
</script>

<template>
  <ol class="space-y-3">
    <li v-for="r in rows" :key="r.id" class="flex gap-3">
      <span class="w-10 shrink-0 t-num text-[11px] leading-5 text-neutral-600">{{ r.when }}</span>
      <span class="min-w-0 flex-1">
        <span class="t-body text-neutral-300">
          <span class="text-neutral-500">{{ r.agent }}</span>
          <RouterLink v-if="r.shot_id" :to="{ name: 'frame', params: { shotId: r.shot_id } }" class="hover:text-neutral-100">
            {{ r.line }}
          </RouterLink>
          <template v-else>{{ r.line }}</template>
          <span v-if="r.repeats > 1" class="t-num text-[11px] text-neutral-600"> ×{{ r.repeats }}</span>
        </span>
      </span>
    </li>
    <li v-if="!rows.length" class="t-meta">Nothing yet.</li>
  </ol>
</template>
