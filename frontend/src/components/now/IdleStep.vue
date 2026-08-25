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
    best() {
      return this.frames.filter((v) => v.analysis).sort((a, b) => b.analysis.score - a.analysis.score)[0] || null
    },
    bestThumb() {
      const blobs = this.best?.shot.blobs || {}
      return blobs.thumb ? `/api/blobs/${blobs.thumb}` : ''
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['issueQuest']),
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

    <button type="button" class="btn-quiet mt-6" :disabled="busy === 'issue'" @click="issueQuest()">
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
        <span class="block t-meta">Your best frame so far</span>
        <span class="mt-1 block truncate t-body">{{ best.analysis.critique }}</span>
      </span>
      <span class="t-num ml-auto text-[15px] text-neutral-300">{{ best.analysis.score }}/10</span>
    </RouterLink>
  </section>
</template>
