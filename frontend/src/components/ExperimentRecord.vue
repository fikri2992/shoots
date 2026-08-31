<script>
import DisclosureRow from '@/components/DisclosureRow.vue'
import VerdictNote from '@/components/VerdictNote.vue'

/** How the three answers read, and how loudly. */
const CHANGE = {
  changed: { label: 'changed', tone: 'text-paper' },
  unchanged: { label: 'unchanged', tone: 'text-neutral-400' },
  'insufficient evidence': { label: 'not enough to say', tone: 'text-muted' },
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
      if (verdicts.some((v) => v.criteria_met)) return 'matched every check'
      if (this.experiment.status === 'skipped') return 'left for another day'
      return this.experiment.status
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
      return this.experiment.result_shot_ids?.at(-1) || this.attempts[0]?.shot_id || ''
    },
    referenceShotId() {
      return this.experiment.reference_shot_id || ''
    },
    resultCount() {
      return this.experiment.result_shot_ids?.length || this.attempts.length
    },
  },
}
</script>

<template>
  <DisclosureRow :label="experiment.title" :count="when">
    <div class="space-y-4 pl-1">
      <p v-if="experiment.criteria_notice" role="note" class="rounded-xl border border-accent/40 p-4 t-body text-paper">
        {{ experiment.criteria_notice }}
      </p>
      <p class="t-meta">
        {{ experiment.type || 'explore' }} · {{ outcome }}
        <template v-if="change">
          · <span :class="change.tone">{{ change.label }}</span>
        </template>
      </p>

      <div v-if="baseline">
        <p class="t-meta text-muted">What Shoots knew before</p>
        <p class="mt-1 t-body text-neutral-300">{{ baseline.citation }}</p>
      </div>

      <div v-if="referenceShotId">
        <p class="t-meta text-muted">The Shot you chose first</p>
        <RouterLink
          :to="{ name: 'shot', params: { shotId: referenceShotId } }"
          class="mt-1 inline-block t-body text-neutral-300 hover:text-paper"
        >
          Open the exact reference Shot ▸
        </RouterLink>
      </div>

      <div v-if="experiment.criteria?.text?.length">
        <p class="t-meta text-muted">The checks you set before shooting</p>
        <ul class="mt-1 space-y-1">
          <li v-for="(c, i) in experiment.criteria.text" :key="i" class="t-body text-neutral-300">
            {{ c }}
          </li>
        </ul>
      </div>

      <div v-if="experiment.type === 'explore' && experiment.variations?.length">
        <p class="t-meta text-muted">Different ways you tried it · no Verdict</p>
        <ul class="mt-2 space-y-2">
          <li v-for="variation in experiment.variations" :key="variation.id" class="t-body text-neutral-300">
            {{ variation.title }}
            <span class="block t-meta">{{ variation.instruction }}</span>
          </li>
        </ul>
        <p v-if="experiment.variation_observations?.length" class="mt-2 t-meta">
          {{ new Set(experiment.variation_observations.map((item) => item.variation_id)).size }} Variations observed across
          {{ experiment.variation_observations.length }} readable result Shots.
        </p>
      </div>

      <div v-if="attempts.length">
        <p class="t-meta text-muted">What came back</p>
        <div class="mt-2 rounded-xl bg-panel-2 p-3"><VerdictNote :verdict="attempts[0]" /></div>
        <p class="mt-2 t-meta">{{ resultCount }} result Shot{{ resultCount === 1 ? '' : 's' }}</p>
      </div>

      <p v-else-if="resultCount" class="t-body text-neutral-300">
        {{ resultCount }} result Shot{{ resultCount === 1 ? '' : 's' }} came back. Shoots could not check {{ resultCount === 1 ? 'it' : 'them' }}.
      </p>

      <div v-if="change">
        <p class="t-meta text-muted">In the Shots since</p>
        <p class="mt-1 t-body" :class="change.tone">{{ change.outcome }}</p>
        <p class="mt-1 t-meta text-muted">
          Shoots compared similar Shots from before and after. That does not prove the Experiment caused the difference.
        </p>
      </div>
      <p v-else-if="baseline" class="t-meta text-muted">Not checked yet.</p>

      <p v-if="sample" class="t-meta text-muted">
        Starting point calculated from {{ sample.sample_size }} Shots with {{ sample.calc_version }}.
        <template v-if="sample.inputs?.length"> Visual reads came from {{ sample.inputs.map((input) => `${input.model}/${input.prompt_version || 'legacy prompt'}`).join(', ') }}.</template>
      </p>

      <RouterLink
        v-if="shotId"
        :to="{ name: 'shot', params: { shotId } }"
        class="inline-block t-meta text-neutral-400 hover:text-neutral-100"
      >
        See the Shot ▸
      </RouterLink>
    </div>
  </DisclosureRow>
</template>
