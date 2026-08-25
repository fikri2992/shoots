<script>
import { mapActions, mapState } from 'pinia'

import VerdictNote from '@/components/VerdictNote.vue'
import { useShootsStore } from '@/stores/shoots'

/**
 * Nothing to shoot right now. Show the last thing the agent decided and when
 * the next one is due, so the screen still answers "what happened".
 */
export default {
  name: 'IdleStep',
  components: { VerdictNote },
  computed: {
    ...mapState(useShootsStore, ['busy', 'lastVerdict', 'frames']),
    /**
     * One earlier frame worth looking at again. A keeper first, because that
     * is the photographer's own verdict; failing that the one the panel
     * corroborated hardest, which is a claim about the evidence. Never the
     * score: no number decides what "your best" means here.
     */
    best() {
      const rank = (v) => [
        v.shot.kept_at ? 1 : 0,
        Math.max(0, ...(v.analysis.techniques || []).map((t) => t.agreement || 0)),
      ]
      return (
        this.frames
          .filter((v) => v.analysis)
          .sort((a, b) => {
            const [ak, ac] = rank(a)
            const [bk, bc] = rank(b)
            return bk - ak || bc - ac
          })[0] || null
      )
    },
    bestThumb() {
      const blobs = this.best?.shot.blobs || {}
      return blobs.thumb ? `/api/blobs/${blobs.thumb}` : ''
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['issueExperiment']),
  },
}
</script>

<template>
  <section class="col gutter pb-32 pt-10">
    <p class="t-meta text-accent">No experiment open</p>
    <h1 class="mt-2 t-hero">The Scout issues the next one in the morning.</h1>
    <p class="mt-4 t-body text-neutral-300">
      It picks from what your frames already show it, and holds it until the light suits the technique.
    </p>

    <button type="button" class="btn-quiet mt-6" :disabled="busy === 'issue'" @click="issueExperiment()">
      {{ busy === 'issue' ? 'Scouting…' : 'Ask for one now' }}
    </button>

    <div v-if="lastVerdict" class="mt-10 rounded-2xl bg-panel p-4">
      <VerdictNote :verdict="lastVerdict.verdict" :title="lastVerdict.experiment.title" />
    </div>

    <RouterLink
      v-if="best"
      :to="{ name: 'frame', params: { shotId: best.shot.id } }"
      class="mt-6 flex items-center gap-4 rounded-2xl bg-panel p-4"
    >
      <img v-if="bestThumb" :src="bestThumb" alt="" class="h-16 w-16 rounded-lg object-cover" />
      <span class="min-w-0">
        <span class="block t-meta">{{ best.shot.kept_at ? 'One you kept' : 'One worth another look' }}</span>
        <span class="mt-1 block truncate t-body">{{ best.analysis.critique }}</span>
      </span>
    </RouterLink>
  </section>
</template>
