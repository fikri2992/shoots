<script>
import { mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

const FAMILIES = ['composition', 'light', 'exposure', 'lens', 'color', 'video']
const TONE = {
  unexplored: 'bg-edge',
  attempted: 'bg-neutral-500',
  practiced: 'bg-neutral-300',
  solid: 'bg-good',
  rusty: 'bg-accent',
}

/**
 * The skill graph as six bars. A bar reads at a glance; the chips behind it
 * are for the one family the user actually wants to inspect.
 */
export default {
  name: 'SkillBars',
  data() {
    return { open: '', selected: null }
  },
  computed: {
    ...mapState(useShootsStore, ['skills', 'skillsByFamily']),
    families() {
      return FAMILIES.filter((f) => this.skillsByFamily[f]?.length).map((f) => {
        const nodes = [...this.skillsByFamily[f]].sort((a, b) => a.level - b.level)
        return {
          key: f,
          nodes,
          done: nodes.filter((n) => n.status !== 'unexplored').length,
          total: nodes.length,
        }
      })
    },
    total() {
      return {
        done: this.skills.filter((n) => n.status !== 'unexplored').length,
        total: this.skills.length,
      }
    },
    tone() {
      return (status) => TONE[status] || TONE.unexplored
    },
    byId() {
      return Object.fromEntries(this.skills.map((n) => [n.technique_id, n]))
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
    name(id) {
      return this.byId[id]?.name || id
    },
  },
}
</script>

<template>
  <section>
    <div class="flex items-baseline justify-between">
      <h2 class="t-title">What you have used</h2>
      <span class="t-meta t-num">{{ total.done }} / {{ total.total }}</span>
    </div>

    <div class="mt-4 space-y-4">
      <div v-for="f in families" :key="f.key">
        <button type="button" class="w-full text-left" @click="toggle(f.key)">
          <div class="flex items-baseline justify-between t-meta">
            <span :class="open === f.key ? 'text-neutral-200' : ''">{{ f.key }}</span>
            <span class="t-num">{{ f.done }}/{{ f.total }}</span>
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
              selected?.technique_id === n.technique_id ? 'border-neutral-400 text-neutral-100' : 'border-edge text-neutral-400',
              n.unlocked || n.status !== 'unexplored' ? '' : 'opacity-40',
            ]"
            @click="pick(n)"
          >
            <span class="h-1.5 w-1.5 rounded-full" :class="tone(n.status)" />
            {{ n.name }}
          </button>
        </div>

        <div v-if="open === f.key && selected" class="mt-3 rounded-xl bg-panel-2 p-3">
          <p class="t-body text-neutral-100">{{ selected.name }} · {{ selected.status }}</p>
          <p class="mt-1 t-meta">
            {{ selected.attempts }} attempt{{ selected.attempts === 1 ? '' : 's' }}
            <template v-if="selected.best_score"> · best {{ selected.best_score }}/10</template>
            <template v-if="selected.last_practiced"> · last {{ new Date(selected.last_practiced).toLocaleDateString() }}</template>
          </p>
          <p v-if="selected.requires.length" class="mt-1 t-meta">Needs {{ selected.requires.map(name).join(', ') }} first.</p>
        </div>
      </div>
    </div>

    <p class="mt-5 t-meta">
      <span class="mr-3"><span class="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-neutral-500" />tried</span>
      <span class="mr-3"><span class="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-neutral-300" />practised</span>
      <span class="mr-3"><span class="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-good" />solid</span>
      <span><span class="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-accent" />going rusty</span>
    </p>
  </section>
</template>
