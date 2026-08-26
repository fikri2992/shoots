<script>
import { mapActions } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

export default {
  name: 'ScoutQuestionStep',
  props: {
    record: { type: Object, required: true },
    busy: { type: String, default: '' },
  },
  methods: {
    ...mapActions(useShootsStore, ['answerScoutQuestion']),
    choose(optionId) {
      return this.answerScoutQuestion(this.record.shoot_id, this.record.revision, optionId)
    },
  },
}
</script>

<template>
  <section class="page-shell pt-10 md:pt-14">
    <div class="max-w-2xl rounded-[24px] border border-edge bg-panel p-6 sm:p-8">
      <p class="eyebrow">One thing Shoots cannot know</p>
      <h1 class="mt-4 t-hero lg:text-[46px]">{{ record.scout.question.prompt }}</h1>
      <p class="mt-4 t-body">These choices came from corroborated Technique Evidence in this Shoot. Your answer becomes Shoot-scoped Intent, not a permanent style label.</p>
      <div class="mt-6 grid gap-3 sm:grid-cols-2">
        <button
          v-for="option in record.scout.question.options"
          :key="option.id"
          type="button"
          class="btn-quiet justify-start text-left"
          :disabled="busy === 'scout-answer'"
          @click="choose(option.id)"
        >
          {{ option.label }}
        </button>
      </div>
    </div>
  </section>
</template>
