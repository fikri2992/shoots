<script>
import { mapActions, mapState } from 'pinia'

import ConnectStep from '@/components/now/ConnectStep.vue'
import IdleStep from '@/components/now/IdleStep.vue'
import ExperimentHero from '@/components/now/ExperimentHero.vue'
import ReadingStep from '@/components/now/ReadingStep.vue'
import SeedStep from '@/components/now/SeedStep.vue'
import { useShootsStore } from '@/stores/shoots'

/**
 * One screen, one state, one decision. Which state shows is decided by where
 * the user actually is in the loop — never a dashboard of everything at once.
 */
export default {
  name: 'NowPage',
  components: { ConnectStep, IdleStep, ExperimentHero, ReadingStep, SeedStep },
  computed: {
    ...mapState(useShootsStore, ['experiment', 'shots', 'connected', 'loading', 'error', 'push', 'busy', 'working', 'seeding']),
    step() {
      if (this.loading && !this.shots.length && !this.connected) return 'loading'
      if (!this.connected) return 'connect'
      if (this.seeding || (!this.shots.length && !this.experiment)) return 'seed'
      if (this.working.length) return 'reading'
      if (this.experiment) return 'experiment'
      return 'idle'
    },
  },
  created() {
    this.checkPush()
  },
  methods: {
    ...mapActions(useShootsStore, ['checkPush', 'enablePush']),
  },
}
</script>

<template>
  <div class="pb-24 md:pb-10">
    <p v-if="error" class="col gutter pt-4">
      <span class="block rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 t-body text-bad">{{ error }}</span>
    </p>

    <ConnectStep v-if="step === 'connect'" />
    <SeedStep v-else-if="step === 'seed'" />
    <ReadingStep v-else-if="step === 'reading'" :shots="working" />
    <ExperimentHero v-else-if="step === 'experiment'" :experiment="experiment" />
    <IdleStep v-else-if="step === 'idle'" />
    <p v-else class="col gutter pt-12 t-meta">Loading…</p>

    <div v-if="push === 'off' && experiment" class="col gutter mt-8">
      <button
        type="button"
        class="flex w-full items-center gap-3 rounded-2xl bg-panel px-4 py-3 text-left"
        :disabled="busy === 'push'"
        @click="enablePush"
      >
        <span class="text-accent">◐</span>
        <span class="t-body text-neutral-300">
          {{ busy === 'push' ? 'Asking your browser…' : 'Let it buzz your phone when the light is right' }}
        </span>
        <span class="ml-auto t-meta">Turn on ▸</span>
      </button>
    </div>
  </div>
</template>
