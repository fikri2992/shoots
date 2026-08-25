<script>
import DisclosureRow from '@/components/DisclosureRow.vue'
import VerdictNote from '@/components/VerdictNote.vue'

/** How the three answers read, and how loudly. */
const CHANGE = {
  changed: { label: 'changed', tone: 'text-good' },
  unchanged: { label: 'unchanged', tone: 'text-neutral-400' },
  'insufficient evidence': { label: 'not enough to say', tone: 'text-neutral-500' },
}

/**
 * One finished Experiment as its durable record.
 *
 * This is the artifact the loop leaves behind: why it was set, what it was
 * measured against before anything happened, what counted as done, what came
 * back, and whether comparable behaviour differs now. Advice text on its own
 * leaves nothing to check, and a coach whose recommendations cannot be audited
 * is a critique queue with a friendlier tone.
 *
 * The Change is shown as one of three answers, never two. "Not enough to say"
 * is the honest state for a photographer who has not been out since, and
 * collapsing it into "unchanged" would read as advice that failed.
 */
export default {
  name: 'ExperimentRecord',
  components: { DisclosureRow, VerdictNote },
  props: { experiment: { type: Object, required: true } },
  computed: {
    when() {
      return new Date(this.experiment.issued_at).toLocaleDateString()
    },
    outcome() {
      const verdicts = this.experiment.verdicts || []
      if (verdicts.some((v) => v.criteria_met)) return 'criteria met'
      return this.experiment.status === 'skipped' ? 'skipped' : this.experiment.status
    },
    change() {
      const change = this.experiment.change
      return change ? { ...CHANGE[change.state], outcome: change.outcome } : null
    },
    baseline() {
      return this.experiment.baseline
    },
    /** Only shown once there is a sample to name. */
    sample() {
      const p = this.baseline?.provenance
      return p?.sample_size ? p : null
    },
    attempts() {
      return [...(this.experiment.verdicts || [])].reverse()
    },
    shotId() {
      return this.attempts[0]?.shot_id || ''
    },
  },
}
</script>

<template>
  <DisclosureRow :label="experiment.title" :count="when">
    <div class="space-y-4 pl-1">
      <p class="t-meta">
        {{ experiment.type || 'explore' }} · {{ outcome }}
        <template v-if="change">
          · <span :class="change.tone">{{ change.label }}</span>
        </template>
      </p>

      <div v-if="baseline">
        <p class="t-meta text-neutral-500">Measured before it was set</p>
        <p class="mt-1 t-body text-neutral-300">{{ baseline.citation }}</p>
      </div>

      <div v-if="experiment.criteria?.text?.length">
        <p class="t-meta text-neutral-500">What counted as done</p>
        <ul class="mt-1 space-y-1">
          <li v-for="(c, i) in experiment.criteria.text" :key="i" class="t-body text-neutral-300">
            {{ c }}
          </li>
        </ul>
      </div>

      <div v-if="attempts.length">
        <p class="t-meta text-neutral-500">What came back</p>
        <div class="mt-2 rounded-xl bg-panel-2 p-3"><VerdictNote :verdict="attempts[0]" /></div>
        <p v-if="attempts.length > 1" class="mt-2 t-meta">{{ attempts.length }} attempts</p>
      </div>

      <div v-if="change">
        <p class="t-meta text-neutral-500">In the shots since</p>
        <p class="mt-1 t-body" :class="change.tone">{{ change.outcome }}</p>
        <p class="mt-1 t-meta text-neutral-600">
          Counts either side, compared by code. It does not show that the experiment caused this.
        </p>
      </div>
      <p v-else-if="baseline" class="t-meta text-neutral-600">Not checked yet.</p>

      <p v-if="sample" class="t-meta text-neutral-600">
        Baseline computed from {{ sample.sample_size }} frames by {{ sample.calc_version }}.
      </p>

      <RouterLink
        v-if="shotId"
        :to="{ name: 'frame', params: { shotId } }"
        class="inline-block t-meta text-neutral-400 hover:text-neutral-100"
      >
        See the frame ▸
      </RouterLink>
    </div>
  </DisclosureRow>
</template>
