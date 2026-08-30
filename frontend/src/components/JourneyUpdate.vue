<script>
import { mapState } from 'pinia'

import DisclosureRow from '@/components/DisclosureRow.vue'
import { humanizeLegacyText } from '@/domain/copy'
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
    latestBody() {
      return humanizeLegacyText(this.latest?.body)
    },
    earlier() {
      return this.journey.slice(1)
    },
    when() {
      return this.latest ? new Date(this.latest.created_at).toLocaleDateString() : ''
    },
    /** Which Shots, arithmetic, Analyst readings, and writer produced this. */
    provenance() {
      return this.latest?.provenance?.sample_size ? this.latest.provenance : null
    },
  },
  methods: {
    humanize(value) {
      return humanizeLegacyText(value)
    },
  },
}
</script>

<template>
  <section v-if="latest">
    <p v-if="latestBody" class="t-hero text-balance text-neutral-100">{{ latestBody }}</p>
    <p v-else class="t-body text-neutral-400">
      Shoots read {{ latest.shots }} Shots, but could not turn the pattern into a clear note this time.
    </p>
    <p class="mt-3 t-meta">{{ when }} · from {{ latest.shots }} Shots</p>

    <div class="mt-5">
      <DisclosureRow label="What that was read from" :count="latest.evidence.length">
        <ul class="space-y-1.5">
          <li v-for="line in latest.evidence" :key="line" class="t-meta text-neutral-400">{{ line }}</li>
        </ul>
        <p v-if="provenance" class="mt-4 t-meta text-muted">
          Computed from {{ provenance.sample_size }} Shots by {{ provenance.calc_version }}<template
            v-if="provenance.prompt_version"
          >, written by {{ provenance.model }} under prompt {{ provenance.prompt_version }}</template>.
          Deterministic dimensions replay from those Shots.
          <template v-if="provenance.inputs?.length">
            Placement and framing trace to
            {{ provenance.inputs.map((input) => `${input.model}/${input.prompt_version || 'legacy prompt'}`).join(', ') }};
            model readings may differ if regenerated.
          </template>
        </p>
      </DisclosureRow>

      <DisclosureRow v-if="earlier.length" label="Earlier" :count="earlier.length">
        <ul class="space-y-4">
          <li v-for="u in earlier" :key="u.id">
            <p class="t-body text-neutral-300">{{ humanize(u.body) }}</p>
            <p class="mt-1 t-meta">{{ new Date(u.created_at).toLocaleDateString() }}</p>
          </li>
        </ul>
      </DisclosureRow>
    </div>
  </section>
</template>
