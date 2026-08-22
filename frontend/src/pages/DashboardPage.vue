<script>
import { mapState } from 'pinia'

import { useAuthStore } from '@/stores/auth'

/**
 * Day-1 placeholder. Day 6 replaces this with the real thing: today's quest on
 * top, the skill graph, the shot timeline with overlays, the activity feed.
 * Phone first: one column at 390px, two at 1024px.
 */
export default {
  name: 'DashboardPage',
  computed: {
    ...mapState(useAuthStore, ['displayName']),
  },
}
</script>

<template>
  <div class="mx-auto flex max-w-5xl flex-col gap-4 p-4">
    <section class="rounded-lg border border-edge bg-panel p-4">
      <p class="text-xs font-medium uppercase tracking-wide text-neutral-500">Today's quest</p>
      <p class="mt-2 text-neutral-300">
        Nothing yet. Connect a Drive folder and the Scout will issue your first quest after the
        first shots are analysed.
      </p>
    </section>

    <section class="grid gap-4 md:grid-cols-2">
      <div class="rounded-lg border border-edge bg-panel p-4">
        <p class="text-xs font-medium uppercase tracking-wide text-neutral-500">Skill graph</p>
        <p class="mt-2 text-sm text-neutral-500">Appears after the first analysis.</p>
      </div>
      <div class="rounded-lg border border-edge bg-panel p-4">
        <p class="text-xs font-medium uppercase tracking-wide text-neutral-500">Activity</p>
        <p class="mt-2 text-sm text-neutral-500">Signed in as {{ displayName }}.</p>
      </div>
    </section>
  </div>
</template>
