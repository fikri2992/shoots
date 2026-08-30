<script>
import { mapState } from 'pinia'

import DisclosureRow from '@/components/DisclosureRow.vue'
import { plain } from '@/domain/cells'
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
}
</script>

<template>
  <div>
    <!-- A Verdict answers the criteria the photographer declared in advance,
         and nothing else. "Passed" graded them for it. -->
    <p class="t-meta">
      <span :class="verdict.criteria_met ? 'text-paper' : 'text-muted'">
        {{ verdict.criteria_met ? 'Matched every check' : 'Not yet' }}
      </span>
      <span v-if="title"> · {{ title }}</span>
    </p>
    <p class="mt-2 t-body text-neutral-100">{{ parts.lead }}</p>

    <div class="mt-3 flex flex-wrap items-center gap-4 t-meta">
      <RouterLink :to="{ name: 'shot', params: { shotId: verdict.shot_id } }" class="hover:text-neutral-200">
        See the Shot ▸
      </RouterLink>
      <RouterLink
        v-if="verdict.compared_with"
        :to="{ name: 'shot', params: { shotId: verdict.compared_with } }"
        class="hover:text-neutral-200"
      >
        Against your earlier one ▸
      </RouterLink>
    </div>

    <div v-if="parts.body" class="mt-2">
      <DisclosureRow label="Why Shoots said that">
        <p class="t-body text-neutral-400">{{ parts.body }}</p>
      </DisclosureRow>
    </div>
  </div>
</template>
