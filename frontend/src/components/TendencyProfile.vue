<script>
import { mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/**
 * What the photographer keeps doing, drawn as counts before claims.
 *
 * Every bar is a number of their own photographs, re-derivable from the file
 * it came from. A dimension with too few readable shots shows its counts and
 * says nothing else; a dimension that could not be read at all says so rather
 * than implying it was explored. Nothing here is a score, and the word is
 * tendency and not habit on purpose: a repeated centred frame might be
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
      <h2 class="t-title">What you keep doing</h2>
      <span class="t-meta">{{ profile.shots }} frames read</span>
    </header>

    <p v-if="profile.walks_on" class="mt-3 t-body text-neutral-300">
      {{ profile.scenes }} scenes, {{ profile.frames_per_scene }} frames each — you usually take one and move on.
    </p>

    <ul class="mt-6 space-y-5">
      <li v-for="d in dimensions" :key="d.id">
        <div class="flex items-baseline justify-between">
          <span class="t-body text-neutral-100">{{ d.label }}</span>
          <span v-if="!d.readable" class="t-meta">too few to say yet</span>
          <span v-else-if="d.narrow" class="t-meta text-accent">barely varies</span>
        </div>

        <ul class="mt-2 space-y-1">
          <li v-for="b in d.buckets" :key="b.bucket" class="flex items-center gap-3">
            <span class="w-28 shrink-0 t-meta" :class="b.count ? 'text-neutral-300' : 'text-neutral-600'">
              {{ b.bucket }}
            </span>
            <span class="h-1.5 flex-1 overflow-hidden rounded bg-edge">
              <span class="block h-full" :class="b.count ? 'bg-neutral-400' : ''" :style="{ width: `${share(d, b)}%` }" />
            </span>
            <span class="w-8 shrink-0 text-right t-meta">{{ b.count || '—' }}</span>
            <span v-if="b.keeper_lift" class="w-16 shrink-0 text-right t-meta" :class="b.keeper_lift >= 1.5 ? 'text-accent' : 'text-neutral-600'">
              kept ×{{ b.keeper_lift }}
            </span>
          </li>
        </ul>

        <p v-if="d.unreadable" class="mt-1 t-meta text-neutral-600">
          {{ d.unreadable }} frames could not be read on this
        </p>
      </li>
    </ul>

    <p v-if="!profile.taste_is_known" class="mt-6 t-meta text-neutral-500">
      Mark a few frames you like and this can also show where your keepers gather, not only where your shooting does. Leaving a frame unmarked says nothing about it.
    </p>

    <div v-if="unread.length" class="mt-6">
      <p class="t-meta text-neutral-500">Still cannot see:</p>
      <ul class="mt-1 space-y-0.5">
        <li v-for="d in unread" :key="d.id" class="t-meta text-neutral-600">{{ d.label }}</li>
      </ul>
    </div>
  </section>
</template>
