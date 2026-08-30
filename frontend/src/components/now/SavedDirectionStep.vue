<script>
import { mapActions, mapState } from 'pinia'

import CompanionReceipt from '@/components/CompanionReceipt.vue'
import { useShootsStore } from '@/stores/shoots'

export default {
  name: 'SavedDirectionStep',
  components: { CompanionReceipt },
  props: {
    direction: { type: Object, required: true },
  },
  computed: {
    ...mapState(useShootsStore, ['busy', 'mobile', 'shotById']),
    sourceShot() {
      return (
        this.shotById(this.direction.source_shot_id)?.shot ||
        (this.mobile?.recent_shots || []).find(
          (shot) => shot.id === this.direction.source_shot_id,
        ) ||
        null
      )
    },
    sourceImage() {
      const path = this.sourceShot?.blobs?.thumb || this.sourceShot?.blobs?.original || ''
      return path ? `/api/blobs/${path}` : ''
    },
    evidenceBasis() {
      const shots = `${this.direction.corroborated_shots} ${this.direction.corroborated_shots === 1 ? 'Shot' : 'Shots'}`
      if (!this.direction.distinct_shoots) return shots
      const shoots = `${this.direction.distinct_shoots} ${this.direction.distinct_shoots === 1 ? 'Shoot' : 'Shoots'}`
      return `${shots} across ${shoots}`
    },
    evidenceLine() {
      return `Seen in ${this.evidenceBasis}.`
    },
    receiptItems() {
      return [
        {
          label: 'Shoots handled',
          text: `Saved one question that comes from ${this.evidenceBasis}.`,
          state: 'done',
        },
        {
          label: 'You decided',
          text: 'You kept this question for later.',
          state: 'done',
        },
        {
          label: 'The result',
          text: 'The question is waiting here. Nothing has started.',
          state: 'done',
        },
        {
          label: 'Next',
          text: 'Try it today, or keep shooting freely. Other Shots stay outside the Experiment.',
          state: 'current',
        },
      ]
    },
  },
  methods: {
    ...mapActions(useShootsStore, [
      'chooseExperimentDirection',
      'startExperimentDirection',
    ]),
    async start() {
      const experiment = await this.startExperimentDirection(this.direction.id)
      if (experiment) {
        await this.$router.replace({ name: 'now', query: { focus: 'experiment' } })
      }
    },
    async leave() {
      await this.chooseExperimentDirection(
        this.direction.source_shot_id,
        this.direction.technique_id,
        false,
      )
    },
  },
}
</script>

<template>
  <section class="page-shell pb-28 pt-7 md:pb-12 md:pt-10">
    <header>
      <p class="eyebrow">Now · saved question</p>
      <h1 class="mt-4 max-w-3xl t-hero lg:text-[48px]">Does this question fit today?</h1>
      <p class="mt-4 max-w-2xl t-body">Try it, or keep shooting normally. Neither choice is a failure.</p>
    </header>

    <div class="mt-7 grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-stretch">
      <article class="surface-active flex flex-col overflow-hidden">
        <div class="h-1 bg-accent" />
        <div class="flex flex-1 flex-col p-5 sm:p-7 lg:p-9">
          <p class="eyebrow text-accent">Before opening the camera</p>
          <div class="mt-5 rounded-2xl border border-edge bg-panel-2/55 p-5 sm:p-6">
            <p class="eyebrow">Saved question</p>
            <p class="mt-3 text-[22px] leading-8 font-medium text-paper">{{ direction.question }}</p>
            <p class="mt-3 t-meta">{{ evidenceLine }}</p>
          </div>

          <CompanionReceipt class="mt-5" title="Why this question is here" :items="receiptItems" compact />

          <div class="mt-6 grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              class="btn w-full"
              :disabled="busy === 'direction-start'"
              @click="start"
            >
              {{ busy === 'direction-start' ? 'Starting…' : 'Try it today' }}
            </button>
            <RouterLink :to="{ name: 'shots' }" class="btn-quiet w-full">Shoot freely</RouterLink>
          </div>
          <p class="mt-4 text-center t-meta">
            Starting fixes the checks before the normal Camera opens.
          </p>
          <button
            type="button"
            class="tap-target mx-auto mt-3 justify-center t-meta text-muted hover:text-paper"
            :disabled="busy === 'direction-choice'"
            @click="leave"
          >
            {{ busy === 'direction-choice' ? 'Deleting…' : 'Delete saved question' }}
          </button>
        </div>
      </article>

      <RouterLink
        v-if="sourceShot"
        :to="{ name: 'shot', params: { shotId: sourceShot.id } }"
        class="surface group overflow-hidden"
      >
        <img
          v-if="sourceImage"
          :src="sourceImage"
          alt=""
          class="aspect-[4/3] w-full object-cover lg:aspect-auto lg:h-[310px]"
        />
        <div class="p-5">
          <p class="eyebrow">The Shot that raised it</p>
          <p class="mt-2 truncate t-body text-paper">{{ sourceShot.filename }}</p>
          <p class="mt-2 t-meta group-hover:text-paper">See why Shoots raised the question</p>
        </div>
      </RouterLink>
    </div>
  </section>
</template>
