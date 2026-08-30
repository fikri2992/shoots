<script>
import { mapState } from 'pinia'

import { repeatabilitySummary } from '@/domain/copy'
import { useShootsStore } from '@/stores/shoots'

const FAMILIES = ['composition', 'light', 'exposure', 'lens', 'color', 'video']
const TONE = {
  observed: 'bg-neutral-500',
  recurring: 'bg-paper',
}

/**
 * The Technique Map as evidence grouped by family. The chips reveal the
 * Technique behind a count without implying a curriculum or completion bar.
 */
export default {
  name: 'TechniqueMap',
  data() {
    return { open: '', selected: null }
  },
  computed: {
    ...mapState(useShootsStore, ['techniques', 'techniquesByFamily']),
    families() {
      return FAMILIES.filter((family) => this.techniquesByFamily[family]?.length).map((family) => {
        const nodes = [...this.techniquesByFamily[family]].sort((a, b) => a.name.localeCompare(b.name))
        return {
          key: family,
          nodes,
          observed: nodes.filter((node) => node.status !== 'unobserved').length,
          recurring: nodes.filter((node) => node.status === 'recurring').length,
        }
      })
    },
    tone() {
      return (status) => TONE[status] || 'bg-edge'
    },
  },
  methods: {
    toggle(key) {
      this.open = this.open === key ? '' : key
      this.selected = null
    },
    pick(node) {
      this.selected = this.selected?.technique_id === node.technique_id ? null : node
    },
    repeatabilityEvidence(node) {
      return repeatabilitySummary(node)
    },
    statusLabel(status) {
      return status === 'recurring' ? 'keeps returning' : status === 'observed' ? 'seen' : 'not seen yet'
    },
  },
}
</script>

<template>
  <section>
    <div class="flex items-baseline justify-between">
      <h2 class="t-title">Techniques in your Shots</h2>
      <span class="t-meta">what Shoots keeps seeing</span>
    </div>

    <div class="mt-4 space-y-4">
      <div v-for="f in families" :key="f.key">
        <button type="button" class="w-full text-left" @click="toggle(f.key)">
          <div class="flex items-baseline justify-between t-meta">
            <span :class="open === f.key ? 'text-neutral-200' : ''">{{ f.key }}</span>
            <span class="t-num">{{ f.observed }} seen · {{ f.recurring }} keep returning</span>
          </div>
          <div class="mt-1.5 flex h-1.5 gap-px overflow-hidden rounded">
            <span v-for="n in f.nodes" :key="n.technique_id" class="flex-1" :class="tone(n.status)" :title="n.name" />
          </div>
        </button>

        <div v-if="open === f.key" class="mt-3 flex flex-wrap gap-1.5">
          <button
            v-for="n in f.nodes"
            :key="n.technique_id"
            type="button"
            class="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12px] transition"
            :class="[
              selected?.technique_id === n.technique_id ? 'border-accent text-accent' : 'border-edge text-neutral-400',
            ]"
            @click="pick(n)"
          >
            <span class="h-1.5 w-1.5 rounded-full" :class="tone(n.status)" />
            {{ n.name }}
          </button>
        </div>

        <div v-if="open === f.key && selected" class="mt-3 rounded-xl bg-panel-2 p-3">
          <p class="t-body text-neutral-100">{{ selected.name }} · {{ statusLabel(selected.status) }}</p>
          <p class="mt-1 t-meta">
            Seen in {{ selected.sightings }} Shot{{ selected.sightings === 1 ? '' : 's' }}
            <template v-if="selected.corroborated_shots"> · clear in {{ selected.corroborated_shots }}</template>
            <template v-if="selected.distinct_shoots"> · {{ selected.distinct_shoots }} Shoot{{ selected.distinct_shoots === 1 ? '' : 's' }}</template>
            <template v-if="selected.last_observed"> · last {{ new Date(selected.last_observed).toLocaleDateString() }}</template>
          </p>
          <p class="mt-2 t-meta text-neutral-300">{{ repeatabilityEvidence(selected) }}</p>
        </div>
      </div>
    </div>

    <p v-if="!families.length" class="mt-4 t-meta text-muted">No clear Technique pattern yet.</p>

    <!-- Unobserved catalogue entries are omitted: this is Evidence memory,
         not a completion denominator. -->
    <p class="mt-5 t-meta">
      <span class="mr-3"><span class="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-neutral-500" />seen</span>
      <span><span class="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-paper" />keeps returning</span>
    </p>
  </section>
</template>
