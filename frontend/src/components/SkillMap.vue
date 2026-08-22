<script>
import { mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

const FAMILIES = ['composition', 'light', 'exposure', 'lens', 'color', 'video']
const DOT = {
  unexplored: 'bg-neutral-700',
  attempted: 'bg-sky-400',
  practiced: 'bg-violet-400',
  solid: 'bg-emerald-400',
  rusty: 'bg-amber-400',
}

/**
 * The skill graph as six family rows of technique chips. Level is the chip's
 * position (L1 first); locked chips (prerequisites not met) are dimmed.
 * Tapping a chip shows its state and what it needs.
 */
export default {
  name: 'SkillMap',
  props: { summary: { type: Boolean, default: false } },
  data() {
    return { selected: null, legend: { attempted: DOT.attempted, practiced: DOT.practiced, solid: DOT.solid, rusty: DOT.rusty } }
  },
  computed: {
    ...mapState(useShootsStore, ['skills', 'skillsByFamily']),
    families() {
      return FAMILIES.filter((f) => this.skillsByFamily[f]?.length)
    },
    counts() {
      const out = {}
      for (const f of this.families) {
        const nodes = this.skillsByFamily[f]
        out[f] = { done: nodes.filter((n) => n.status !== 'unexplored').length, total: nodes.length }
      }
      return out
    },
    total() {
      const done = this.skills.filter((n) => n.status !== 'unexplored').length
      return { done, total: this.skills.length }
    },
    byId() {
      return Object.fromEntries(this.skills.map((n) => [n.technique_id, n]))
    },
    dot() {
      return (status) => DOT[status] || DOT.unexplored
    },
  },
  methods: {
    sorted(nodes) {
      return [...nodes].sort((a, b) => a.level - b.level)
    },
    pick(node) {
      this.selected = this.selected?.technique_id === node.technique_id ? null : node
    },
    name(id) {
      return this.byId[id]?.name || id
    },
  },
}
</script>

<template>
  <section class="rounded-xl border border-edge bg-panel p-4">
    <header class="flex items-baseline justify-between">
      <h2 class="text-sm font-semibold">Skill map</h2>
      <span class="text-xs text-neutral-500">{{ total.done }} / {{ total.total }} techniques</span>
    </header>

    <div class="mt-3 space-y-3">
      <div v-for="f in families" :key="f">
        <div class="mb-1 flex items-baseline justify-between">
          <span class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">{{ f }}</span>
          <span class="text-[11px] text-neutral-600">{{ counts[f].done }}/{{ counts[f].total }}</span>
        </div>
        <div v-if="summary" class="flex h-1.5 overflow-hidden rounded bg-neutral-800">
          <div
            v-for="n in sorted(skillsByFamily[f])"
            :key="n.technique_id"
            class="flex-1 border-r border-ink last:border-r-0"
            :class="dot(n.status)"
            :title="n.name"
          />
        </div>
        <div v-else class="flex flex-wrap gap-1.5">
          <button
            v-for="n in sorted(skillsByFamily[f])"
            :key="n.technique_id"
            type="button"
            class="flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs transition"
            :class="[
              selected?.technique_id === n.technique_id ? 'border-neutral-300 text-neutral-100' : 'border-edge text-neutral-300',
              n.unlocked || n.status !== 'unexplored' ? '' : 'opacity-40',
            ]"
            @click="pick(n)"
          >
            <span class="h-2 w-2 rounded-full" :class="dot(n.status)" />
            {{ n.name }}
            <span class="font-mono text-[10px] text-neutral-500">L{{ n.level }}</span>
          </button>
        </div>
      </div>
    </div>

    <div v-if="selected && !summary" class="mt-4 rounded-lg border border-edge bg-panel-2 p-3 text-sm">
      <div class="flex items-center justify-between">
        <span class="font-medium">{{ selected.name }}</span>
        <span class="text-xs text-neutral-400">{{ selected.status }}</span>
      </div>
      <p class="mt-1 text-xs text-neutral-400">
        {{ selected.attempts }} attempt{{ selected.attempts === 1 ? '' : 's' }}
        <template v-if="selected.best_score"> · best {{ selected.best_score }}/10</template>
        <template v-if="selected.last_practiced"> · last {{ new Date(selected.last_practiced).toLocaleDateString() }}</template>
      </p>
      <p v-if="selected.requires.length" class="mt-1 text-xs text-neutral-500">
        Needs: {{ selected.requires.map(name).join(', ') }}
      </p>
    </div>

    <div class="mt-3 flex flex-wrap gap-3 text-[11px] text-neutral-500">
      <span v-for="(cls, s) in legend" :key="s" class="flex items-center gap-1">
        <span class="h-2 w-2 rounded-full" :class="cls" />{{ s }}
      </span>
    </div>
  </section>
</template>
