<script>
import { mapActions, mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/** Optional Drive setup. Core capture and direct upload stay independent. */
export default {
  name: 'ConnectStep',
  computed: {
    ...mapState(useShootsStore, ['busy']),
  },
  methods: {
    ...mapActions(useShootsStore, ['connect']),
  },
}
</script>

<template>
  <section class="rounded-2xl border border-edge bg-panel-2/45 p-5 sm:p-6">
    <p class="eyebrow text-accent">Optional Drive connection</p>
    <h2 class="mt-2 t-title">Import existing files and keep reviewed copies.</h2>
    <p class="mt-3 t-body">
      Phone Source and direct upload work without Drive. Connecting creates one folder named
      <span class="t-num text-paper">Shoots</span>. Existing files are read only when you select them.
    </p>
    <button type="button" class="btn mt-5 w-full sm:w-auto" :disabled="busy === 'connect'" @click="connect">
      {{ busy === 'connect' ? 'Connecting…' : 'Connect optional Drive' }}
    </button>
  </section>
</template>
