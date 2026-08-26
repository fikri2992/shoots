<script>
import { mapActions, mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/**
 * The step that buys the first opinion. Handing over a few Shots from the
 * gallery is the shortest path to something true about the user's own
 * photography — shorter than opening Drive in another app and moving files.
 */
export default {
  name: 'SeedStep',
  computed: {
    ...mapState(useShootsStore, ['seeding']),
  },
  methods: {
    ...mapActions(useShootsStore, ['seed']),
    onPick(event) {
      const files = [...(event.target.files || [])]
      event.target.value = ''
      if (files.length) this.seed(files)
    },
  },
}
</script>

<template>
  <section class="page-shell py-8 md:py-12">
    <template v-if="!seeding">
      <p class="eyebrow">Now · One step left</p>
      <div class="mt-6 grid gap-5 lg:grid-cols-[1fr_360px]">
        <div class="surface-active p-6 sm:p-9">
          <p class="eyebrow text-accent">Start with your work, not a questionnaire</p>
          <h1 class="mt-4 max-w-2xl t-hero lg:text-[48px]">Show it three or four Shots you already made.</h1>
          <p class="mt-5 max-w-2xl text-[16px] leading-7 text-neutral-300">
            Older Shots are useful. Shoots needs enough of your own work to notice a supported Tendency before it offers an Experiment.
          </p>
        </div>
        <div class="surface p-5 sm:p-6">
          <p class="eyebrow">First read</p>
          <p class="mt-3 t-body">Choose stills or video from this device. Unreadable dimensions remain unknown.</p>
          <label class="btn mt-6 w-full cursor-pointer">
            Choose Shots
            <input type="file" accept="image/*,video/*" multiple class="hidden" @change="onPick" />
          </label>
          <p class="mt-3 t-meta">They enter Shoots directly. Drive is optional.</p>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="mx-auto max-w-2xl surface-active p-6 sm:p-9">
        <p class="eyebrow text-accent">Uploading {{ seeding.done + 1 }} of {{ seeding.total }}</p>
        <h1 class="mt-4 t-hero">Building the first memory.</h1>
        <p class="mt-4 t-body">{{ seeding.name }}</p>
        <div class="mt-7 h-1 overflow-hidden rounded bg-edge">
        <div
          class="h-full bg-accent transition-all"
          :style="{ width: `${Math.round((seeding.done / seeding.total) * 100)}%` }"
        />
        </div>
      </div>
    </template>
  </section>
</template>
