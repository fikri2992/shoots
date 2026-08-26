<script>
import { mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/**
 * What the photographer keeps doing, drawn as counts before claims.
 *
 * Every bar is a number of their own Shots, re-derivable from the file
 * it came from. A dimension with too few readable shots shows its counts and
 * says nothing else; a dimension that could not be read at all says so rather
 * than implying it was explored. Nothing here is a score, and the word is
 * Tendency and not habit on purpose: a repeated centred Shot might be
 * laziness or the beginning of a style, and this page does not decide that.
 */
export default {
  name: 'TendencyProfile',
  computed: {
    ...mapState(useShootsStore, ['profile']),
    dimensions() {
      return (this.profile?.dimensions || []).filter((d) => this.total(d) > 0)
    },
    unread() {
      return (this.profile?.dimensions || []).filter((d) => this.total(d) === 0)
    },
  },
  methods: {
    total(dimension) {
      return dimension.buckets.reduce((sum, b) => sum + b.count, 0)
    },
    share(dimension, bucket) {
      const total = this.total(dimension)
      return total ? Math.round((bucket.count / total) * 100) : 0
    },
  },
}
</script>

<template>
  <section v-if="profile && profile.shots">
    <header class="flex items-baseline justify-between">
      <h2 class="t-title">Full Tendency distributions</h2>
      <span class="t-meta">{{ profile.shots }} Shots read</span>
    </header>

    <p v-if="profile.walks_on" class="mt-3 t-body text-neutral-300">
      {{ profile.scenes }} Scenes, {{ profile.shots_per_scene }} Shots each — you usually take one and move on.
    </p>

    <ul class="mt-6 grid gap-4 md:grid-cols-2">
      <li v-for="d in dimensions" :key="d.id" class="rounded-2xl border border-edge bg-panel-2/45 p-4">
        <div class="flex items-baseline justify-between gap-3">
          <span class="text-sm font-semibold text-paper">{{ d.label }}</span>
          <span class="flex shrink-0 items-baseline gap-2">
            <span v-if="!d.readable" class="t-meta">too few to say yet</span>
            <span v-else-if="d.narrow" class="t-meta text-neutral-300">barely varies</span>
          </span>
        </div>
        <p class="mt-1 t-meta">{{ d.source }}</p>

        <ul class="mt-4 grid grid-cols-2 gap-2">
          <li
            v-for="b in d.buckets"
            :key="b.bucket"
            class="rounded-xl border border-edge px-3 py-2.5"
            :class="b.count ? 'bg-panel' : 'opacity-45'"
          >
            <div class="flex items-baseline justify-between gap-2">
              <span class="truncate text-[12px] text-neutral-300">{{ b.bucket }}</span>
              <span class="t-num text-sm text-paper">{{ b.count || '—' }}</span>
            </div>
            <p class="mt-1 t-meta">{{ share(d, b) }}% of readable</p>
            <p v-if="b.keepers" class="mt-1 text-[11px] text-accent">{{ b.keepers }}/{{ d.readable_keepers }} Keepers</p>
          </li>
        </ul>

        <p v-if="d.unreadable" class="mt-1 t-meta text-neutral-600">
          {{ d.unreadable }} Shots could not be read on this
        </p>
      </li>
    </ul>

    <p v-if="!profile.taste_is_known" class="mt-6 t-meta text-neutral-500">
      Mark a few Shots you like and this can show where your Keepers gather. Leaving a Shot unmarked says nothing about it.
    </p>

    <div v-if="unread.length" class="mt-6">
      <p class="eyebrow">Still cannot see</p>
      <ul class="mt-2 flex flex-wrap gap-2">
        <li v-for="d in unread" :key="d.id" class="rounded-lg border border-dashed border-edge px-2.5 py-1.5 t-meta">{{ d.label }}</li>
      </ul>
    </div>
  </section>
</template>
