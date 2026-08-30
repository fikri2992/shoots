<script>
export default {
  name: 'ReproduceProof',
  props: {
    experiment: { type: Object, required: true },
    shots: { type: Array, required: true },
  },
  computed: {
    reference() {
      return this.shots.find((item) => item.shot.id === this.experiment.reference_shot_id) || null
    },
    resultRows() {
      const views = new Map(this.shots.map((item) => [item.shot.id, item]))
      const verdicts = new Map((this.experiment.verdicts || []).map((item) => [item.shot_id, item]))
      return (this.experiment.result_shot_ids || []).map((id) => ({
        id,
        view: views.get(id) || null,
        verdict: verdicts.get(id) || null,
      }))
    },
    statement() {
      const evaluable = this.resultRows.filter((row) => row.verdict)
      const met = evaluable.filter((row) => row.verdict.criteria_met).length
      const inconclusive = this.resultRows.length - evaluable.length
      if (!evaluable.length) {
        return `Shoots kept ${this.resultRows.length} ${this.resultRows.length === 1 ? 'result' : 'results'}, but could not check ${this.resultRows.length === 1 ? 'it' : 'them'}. It makes no claim about repeatability.`
      }
      const bits = [`${met} of ${evaluable.length} checked ${evaluable.length === 1 ? 'result matched' : 'results matched'} everything you set before shooting`]
      if (inconclusive) bits.push(`${inconclusive} could not be checked`)
      return `${bits.join('. ')}.`
    },
    technique() {
      return this.experiment.technique_id
        ? this.experiment.technique_id.replace(/_/g, ' ')
        : this.experiment.title || 'Reproduce'
    },
    criteria() {
      return this.experiment.criteria?.text || []
    },
  },
  methods: {
    thumb(view) {
      const path = view?.shot?.blobs?.thumb
      return path ? `/api/blobs/${path}` : ''
    },
    verdictLabel(verdict) {
      if (!verdict) return 'Could not check'
      return verdict.criteria_met ? 'Matched' : 'Not yet'
    },
    resultSummary(verdict) {
      if (!verdict) return 'Shoots could not check every part of this result.'
      return verdict.criteria_met
        ? 'This Shot matched everything you set before shooting.'
        : 'This Shot did not match every check yet.'
    },
    nextMove(feedback) {
      const match = String(feedback || '').match(/(?:^|\n)Next:\s*([^\n]+)/i)
      return match?.[1]?.trim() || ''
    },
  },
}
</script>

<template>
  <section v-if="reference && resultRows.length" class="surface-active overflow-hidden">
    <div class="h-1 bg-accent" />
    <div class="p-5 sm:p-7">
      <p class="eyebrow text-accent">Can you repeat what you keep?</p>
      <h2 class="mt-3 t-title">{{ technique }}</h2>
      <p class="mt-3 max-w-2xl text-[16px] leading-7 text-neutral-200">{{ statement }}</p>

      <div v-if="criteria.length" class="mt-6 rounded-2xl border border-edge bg-panel-2/45 p-4">
        <p class="eyebrow">What you were trying to repeat</p>
        <ol class="mt-3 space-y-2">
          <li v-for="(criterion, index) in criteria" :key="index" class="flex gap-3 t-body text-neutral-300">
            <span class="t-num text-[11px] text-accent">0{{ index + 1 }}</span>
            <span>{{ criterion }}</span>
          </li>
        </ol>
      </div>

      <div class="mt-6 grid gap-3 sm:grid-cols-2">
        <RouterLink
          :to="{ name: 'shot', params: { shotId: reference.shot.id } }"
          class="overflow-hidden rounded-2xl border border-edge bg-panel"
        >
          <img v-if="thumb(reference)" :src="thumb(reference)" alt="" class="aspect-[4/3] w-full object-cover" />
          <span class="block p-4">
            <span class="eyebrow">Keeper reference</span>
            <span class="mt-2 block truncate t-body text-paper">{{ reference.shot.filename }}</span>
          </span>
        </RouterLink>
        <article
          v-for="(row, index) in resultRows"
          :key="row.id"
          class="overflow-hidden rounded-2xl border border-edge bg-panel"
        >
          <template v-if="row.view">
            <RouterLink :to="{ name: 'shot', params: { shotId: row.id } }" class="block">
            <img v-if="thumb(row.view)" :src="thumb(row.view)" :alt="`Explicit result Shot ${index + 1}`" class="aspect-[4/3] w-full object-cover" />
            <span class="block p-4">
              <span class="eyebrow">Result {{ index + 1 }} · {{ verdictLabel(row.verdict) }}</span>
              <span class="mt-2 block truncate t-body text-paper">{{ row.view.shot.filename }}</span>
            </span>
            </RouterLink>
            <div class="border-t border-edge px-4 pb-4 pt-3">
              <p class="t-meta text-neutral-300">{{ resultSummary(row.verdict) }}</p>
              <p v-if="nextMove(row.verdict?.feedback)" class="mt-2 t-body text-paper">
                Next: {{ nextMove(row.verdict.feedback) }}
              </p>
              <details v-if="row.verdict?.feedback" class="mt-3">
                <summary class="cursor-pointer t-meta text-muted">Read the full Judge note</summary>
                <p class="mt-2 t-meta text-neutral-300">{{ row.verdict.feedback }}</p>
              </details>
            </div>
          </template>
          <div v-else class="p-4">
            <p class="eyebrow">Result {{ index + 1 }} · {{ verdictLabel(row.verdict) }}</p>
            <p class="mt-2 t-body text-neutral-300">Shoots kept this result, but its preview is unavailable.</p>
          </div>
        </article>
      </div>

      <p class="mt-4 t-meta text-muted">
        This checks one choice you set before shooting. It does not grade the Shot.
      </p>
    </div>
  </section>
</template>
