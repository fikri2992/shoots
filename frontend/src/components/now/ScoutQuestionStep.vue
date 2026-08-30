<script>
import { mapActions } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

export default {
  name: 'ScoutQuestionStep',
  props: {
    record: { type: Object, required: true },
    members: { type: Array, default: () => [] },
    busy: { type: String, default: '' },
  },
  computed: {
    techniqueChoices() {
      return (this.record.scout.question.options || [])
        .filter((option) => option.technique_id)
        .map((option) => {
          const warrant = (this.record.scout.warrant || []).find(
            (item) => item.technique_id === option.technique_id,
          )
          const evidenceIds = [warrant?.reference_shot_id, ...(warrant?.shot_ids || [])].filter(Boolean)
          const view = evidenceIds
            .map((id) => this.members.find((member) => member.shot.id === id))
            .find((member) => this.thumb(member)) || null
          return {
            option,
            view,
            evidenceCount: new Set(warrant?.shot_ids || []).size,
          }
        })
    },
    openChoice() {
      return (this.record.scout.question.options || []).find((option) => !option.technique_id) || null
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['answerScoutQuestion']),
    choose(optionId) {
      return this.answerScoutQuestion(this.record.shoot_id, this.record.revision, optionId)
    },
    thumb(view) {
      const blobs = view?.shot?.blobs || {}
      const path = blobs.thumb || blobs.original || ''
      return path ? `/api/blobs/${path}` : ''
    },
    shotTarget(choice) {
      return {
        name: 'shot',
        params: { shotId: choice.view.shot.id },
        query: { from: 'now' },
      }
    },
  },
}
</script>

<template>
  <section class="page-shell pt-10 md:pt-14">
    <div class="max-w-5xl rounded-[24px] border border-edge bg-panel p-6 sm:p-8">
      <p class="eyebrow">One thing Shoots cannot know</p>
      <h1 class="mt-4 t-hero lg:text-[46px]">{{ record.scout.question.prompt }}</h1>
      <p class="mt-4 max-w-2xl t-body">
        Shoots saw these choices in the Shots below. Which one were you actually paying attention to?
        Your answer stays with this Shoot. It does not label your style.
      </p>

      <div class="mt-7 grid gap-4 md:grid-cols-3">
        <article
          v-for="choice in techniqueChoices"
          :key="choice.option.id"
          data-scout-evidence
          class="overflow-hidden rounded-[20px] border border-edge bg-panel-2/70"
        >
          <RouterLink
            v-if="choice.view"
            :to="shotTarget(choice)"
            class="group relative block aspect-[4/3] bg-ink"
            :aria-label="`Open evidence Shot for ${choice.option.label}`"
          >
            <img
              :src="thumb(choice.view)"
              :alt="`One Shot where ${choice.option.label} appeared`"
              class="h-full w-full object-contain transition duration-200 group-hover:opacity-90"
            />
            <span class="absolute right-3 bottom-3 rounded-full bg-ink/80 px-3 py-1 text-[11px] text-paper backdrop-blur">
              Open Shot
            </span>
          </RouterLink>
          <div v-else class="flex aspect-[4/3] items-center justify-center bg-ink px-5 text-center t-meta">
            Evidence Shot unavailable
          </div>

          <div class="p-4">
            <h2 class="text-[17px] font-medium text-paper">{{ choice.option.label }}</h2>
            <p class="mt-1 t-meta">
              One example · clear in {{ choice.evidenceCount }}
              {{ choice.evidenceCount === 1 ? 'Shot' : 'Shots' }}
            </p>
            <button
              type="button"
              class="btn-quiet mt-4 w-full justify-center"
              :data-option-id="choice.option.id"
              :disabled="busy === 'scout-answer'"
              @click="choose(choice.option.id)"
            >
              That was what I noticed
            </button>
          </div>
        </article>
      </div>

      <div v-if="openChoice" class="mt-5 border-t border-edge pt-5">
        <p class="t-meta">None of those fit?</p>
        <button
          type="button"
          class="btn-quiet mt-3 w-full justify-center sm:w-auto"
          :data-option-id="openChoice.id"
          :disabled="busy === 'scout-answer'"
          @click="choose(openChoice.id)"
        >
          {{ openChoice.label }}
        </button>
      </div>
    </div>
  </section>
</template>
