<script>
import { mapActions, mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/**
 * The step that buys the first opinion. Handing over a few frames from the
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
  <section class="col gutter pt-12">
    <template v-if="!seeding">
      <p class="t-meta text-accent">One step left</p>
      <h1 class="mt-2 t-hero">Show it three or four photos you have already taken.</h1>
      <p class="mt-4 t-body text-neutral-300">
        It reads them the way a print judge would — what you did well, what you have not tried — and that read is
        what the first quest is built from. Old photos are fine. Anything on this phone is fine.
      </p>

      <label class="btn mt-8 w-full cursor-pointer">
        <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
          <path d="M4 5h16v14H4zM4 15l4-4 4 4 3-3 5 5" />
        </svg>
        Choose photos
        <input type="file" accept="image/*,video/*" multiple class="hidden" @change="onPick" />
      </label>
      <p class="mt-3 t-meta">They go into your own Drive folder, and stay yours.</p>
    </template>

    <template v-else>
      <p class="t-meta text-accent">Uploading {{ seeding.done + 1 }} of {{ seeding.total }}</p>
      <h1 class="mt-2 t-hero">Handing them over…</h1>
      <p class="mt-4 t-body text-neutral-400">{{ seeding.name }}</p>
      <div class="mt-6 h-1 overflow-hidden rounded bg-edge">
        <div
          class="h-full bg-accent transition-all"
          :style="{ width: `${Math.round((seeding.done / seeding.total) * 100)}%` }"
        />
      </div>
    </template>
  </section>
</template>
