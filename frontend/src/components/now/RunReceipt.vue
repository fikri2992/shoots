<script>
import { mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

const SETTLED = new Set(['completed', 'skipped', 'terminal'])

export default {
  name: 'RunReceipt',
  computed: {
    ...mapState(useShootsStore, ['experiments', 'orderedShots', 'runs']),
    run() {
      return this.runs[0] || null
    },
    view() {
      return this.orderedShots.find((item) => item.shot.id === this.run?.shot_id) || null
    },
    shot() {
      return this.view?.shot || null
    },
    source() {
      if (this.run?.source === 'android') return 'Phone Source'
      if (this.run?.source === 'drive') return 'Google Drive'
      return 'Direct import'
    },
    experiment() {
      return this.experiments.find((item) => item.id === this.run?.experiment_id) || null
    },
    rows() {
      const step = (name) => this.run?.steps?.[name] || { state: 'pending', outcome: '' }
      const row = (name, waiting) => {
        const current = step(name)
        return {
          name,
          label: current.outcome || waiting,
          state: current.state,
          done: SETTLED.has(current.state),
          bad: current.state === 'terminal',
          retrying: current.state === 'retrying',
        }
      }
      return [
        row('ingest', `${this.source} is preparing the Shot`),
        row('analyst', 'Analyst is reading the Shot'),
        row('cartographer', 'Cartographer is checking the longitudinal record'),
        row('judge', this.experiment ? 'Judge is checking the result contract' : 'No Experiment judgment needed'),
        row('scribe', 'Scribe is accounting for the external write'),
        row('scout', 'Scout is deciding whether the record supports another Experiment'),
      ]
    },
    complete() {
      return ['completed', 'terminal'].includes(this.run?.status)
    },
    statusLabel() {
      if (this.run?.status === 'completed') return 'ACCOUNTED FOR'
      if (this.run?.status === 'terminal') return 'STOPPED'
      if (this.run?.status === 'retrying') return 'RETRYING'
      return 'WORKING'
    },
    statusTone() {
      if (this.run?.status === 'terminal') return 'text-bad'
      if (this.complete) return 'text-neutral-400'
      return 'text-accent'
    },
    scoutOutcome() {
      return this.run?.steps?.scout?.outcome || ''
    },
  },
}
</script>

<template>
  <section v-if="run && shot" class="page-shell mt-6">
    <div class="surface overflow-hidden">
      <div class="flex items-center gap-3 border-b border-edge px-5 py-4 sm:px-6">
        <span
          class="h-2.5 w-2.5 rounded-full"
          :class="complete ? 'bg-neutral-400' : 'animate-pulse bg-accent'"
        />
        <div class="min-w-0">
          <p class="eyebrow">Latest autonomous run</p>
          <p class="mt-1 truncate t-body text-paper">{{ shot.filename }}</p>
        </div>
        <span class="ml-auto t-num text-[11px]" :class="statusTone">{{ statusLabel }}</span>
      </div>

      <div class="grid gap-6 p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <ol class="space-y-4">
          <li v-for="item in rows" :key="item.name" class="flex items-start gap-3">
            <span
              class="mt-1.5 h-2 w-2 shrink-0 rounded-full"
              :class="item.bad ? 'bg-bad' : item.retrying ? 'animate-pulse bg-accent' : item.done ? 'bg-neutral-400' : 'bg-edge-strong'"
            />
            <span class="t-body" :class="item.done ? 'text-neutral-300' : 'text-neutral-600'">
              {{ item.label }}
            </span>
          </li>
        </ol>

        <div class="rounded-2xl border border-edge bg-panel-2/50 p-4">
          <p class="eyebrow">What it left</p>
          <p v-if="scoutOutcome" class="mt-3 t-body text-neutral-300">{{ scoutOutcome }}</p>
          <p v-else class="mt-3 t-body text-muted">
            The Shot, Evidence, and stage outcomes stay in one checkable Run.
          </p>
          <RouterLink
            :to="{ name: 'shot', params: { shotId: shot.id } }"
            class="mt-4 inline-block t-meta text-accent hover:text-paper"
          >
            Inspect the Evidence →
          </RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>
