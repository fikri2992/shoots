<script>
import { mapState } from 'pinia'

import DisclosureRow from '@/components/DisclosureRow.vue'
import { useShootsStore } from '@/stores/shoots'

/**
 * The agent's current conclusion about this photographer.
 *
 * The finished artifact of the whole product: what they lean toward, what has
 * become theirs, and one direction offered. It is written only when the
 * Tendency Profile actually moved, so it is never the same paragraph twice,
 * and every clause in it points at a figure — which is why the evidence sits
 * one tap away rather than out of sight.
 */
export default {
  name: 'JourneyUpdate',
  components: { DisclosureRow },
  computed: {
    ...mapState(useShootsStore, ['journey']),
    latest() {
      return this.journey[0] || null
    },
    earlier() {
      return this.journey.slice(1)
    },
    when() {
      return this.latest ? new Date(this.latest.created_at).toLocaleDateString() : ''
    },
  },
}
</script>

<template>
  <section v-if="latest">
    <p v-if="latest.body" class="t-hero text-balance text-neutral-100">{{ latest.body }}</p>
    <p v-else class="t-body text-neutral-400">
      Read {{ latest.shots }} frames. The figures are below; the words did not come back this time.
    </p>
    <p class="mt-3 t-meta">{{ when }} · from {{ latest.shots }} frames</p>

    <div class="mt-5">
      <DisclosureRow label="What that was read from" :count="latest.evidence.length">
        <ul class="space-y-1.5">
          <li v-for="line in latest.evidence" :key="line" class="t-meta text-neutral-400">{{ line }}</li>
        </ul>
      </DisclosureRow>

      <DisclosureRow v-if="earlier.length" label="Earlier" :count="earlier.length">
        <ul class="space-y-4">
          <li v-for="u in earlier" :key="u.id">
            <p class="t-body text-neutral-300">{{ u.body }}</p>
            <p class="mt-1 t-meta">{{ new Date(u.created_at).toLocaleDateString() }}</p>
          </li>
        </ul>
      </DisclosureRow>
    </div>
  </section>
</template>
