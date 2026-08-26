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
    resultId() {
      return this.experiment.result_shot_ids?.at(-1) || ''
    },
    result() {
      return this.shots.find((item) => item.shot.id === this.resultId) || null
    },
    verdict() {
      return this.experiment.verdicts?.find((item) => item.shot_id === this.resultId) || null
    },
    statement() {
      if (!this.verdict) return 'The result is recorded. Judge abstained, so Shoots makes no repeatability claim.'
      if (this.verdict.criteria_met) return 'The same decision appeared again, and the declared Reproduce Criteria were met.'
      return 'You tried the decision again. The declared Reproduce Criteria were not met yet.'
    },
    technique() {
      return this.experiment.technique_id.replace(/_/g, ' ')
    },
  },
  methods: {
    thumb(view) {
      const path = view?.shot?.blobs?.thumb
      return path ? `/api/blobs/${path}` : ''
    },
  },
}
</script>

<template>
  <section v-if="reference && result" class="surface-active overflow-hidden">
    <div class="h-1 bg-accent" />
    <div class="p-5 sm:p-7">
      <p class="eyebrow text-accent">Can you repeat what you keep?</p>
      <h2 class="mt-3 t-title">{{ technique }}</h2>
      <p class="mt-3 max-w-2xl text-[16px] leading-7 text-neutral-200">{{ statement }}</p>

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
        <RouterLink
          :to="{ name: 'shot', params: { shotId: result.shot.id } }"
          class="overflow-hidden rounded-2xl border border-edge bg-panel"
        >
          <img v-if="thumb(result)" :src="thumb(result)" alt="" class="aspect-[4/3] w-full object-cover" />
          <span class="block p-4">
            <span class="eyebrow">Explicit result</span>
            <span class="mt-2 block truncate t-body text-paper">{{ result.shot.filename }}</span>
          </span>
        </RouterLink>
      </div>

      <p class="mt-4 t-meta">
        This compares one declared decision. It does not claim the result Shot is better.
      </p>
    </div>
  </section>
</template>
