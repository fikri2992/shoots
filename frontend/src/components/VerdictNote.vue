<script>
import { mapActions, mapState } from 'pinia'

import DisclosureRow from '@/components/DisclosureRow.vue'
import { plain } from '@/domain/cells'
import { useCoachStore } from '@/stores/coach'
import { useShootsStore } from '@/stores/shoots'

/**
 * One attempt, read the way a photographer needs it: the verdict, then the one
 * thing to change. The Judge's full reasoning is a tap away — it is evidence
 * for the instruction, not the instruction.
 */
export default {
  name: 'VerdictNote',
  components: { DisclosureRow },
  props: {
    verdict: { type: Object, required: true },
    title: { type: String, default: '' },
  },
  computed: {
    ...mapState(useShootsStore, ['shotById']),
    /** The Judge writes a paragraph and closes with a "Next:" line. */
    parts() {
      const grid = this.shotById(this.verdict.shot_id)?.shot?.grid
      const text = plain((this.verdict.feedback || '').trim(), grid)
      const at = text.lastIndexOf('Next:')
      if (at < 0) {
        const stop = text.indexOf('. ')
        return { lead: stop > 0 ? text.slice(0, stop + 1) : text, body: stop > 0 ? text.slice(stop + 2) : '' }
      }
      return { lead: text.slice(at + 5).trim(), body: text.slice(0, at).trim() }
    },
  },
  methods: {
    ...mapActions(useCoachStore, ['openFor']),
    askWhy() {
      this.openFor(this.verdict.shot_id, {
        opener: this.verdict.passed
          ? 'What made this one work, and what would take it further?'
          : 'Why did this not pass the quest? Point at the frame.',
      })
    },
  },
}
</script>

<template>
  <div>
    <p class="t-meta">
      <span :class="verdict.passed ? 'text-good' : 'text-accent'">{{ verdict.passed ? 'Passed' : 'Not yet' }}</span>
      <span v-if="title"> · {{ title }}</span>
    </p>
    <p class="mt-2 t-body text-neutral-100">{{ parts.lead }}</p>

    <div class="mt-3 flex flex-wrap items-center gap-4 t-meta">
      <button type="button" class="text-neutral-400 hover:text-neutral-100" @click="askWhy">Ask the Coach ▸</button>
      <RouterLink :to="{ name: 'frame', params: { shotId: verdict.shot_id } }" class="hover:text-neutral-200">
        See the frame ▸
      </RouterLink>
      <RouterLink
        v-if="verdict.compared_with"
        :to="{ name: 'frame', params: { shotId: verdict.compared_with } }"
        class="hover:text-neutral-200"
      >
        Against your best ▸
      </RouterLink>
    </div>

    <div v-if="parts.body" class="mt-2">
      <DisclosureRow label="What it looked at">
        <p class="t-body text-neutral-400">{{ parts.body }}</p>
      </DisclosureRow>
    </div>
  </div>
</template>
