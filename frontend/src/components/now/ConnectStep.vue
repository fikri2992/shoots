<script>
import { mapActions, mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/** First screen after sign-in. One promise, one button. */
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
  <section class="page-shell py-8 md:py-12">
    <p class="eyebrow">Now · Setup once</p>
    <div class="mt-6 grid gap-5 lg:grid-cols-[1fr_360px] lg:items-start">
      <div class="surface-active p-6 sm:p-9">
        <p class="eyebrow text-accent">Optional connection</p>
        <h1 class="mt-4 max-w-2xl t-hero lg:text-[48px]">Use Drive for imports and reviewed copies.</h1>
        <p class="mt-5 max-w-2xl text-[16px] leading-7 text-neutral-300">
          Phone Source and direct upload work without Drive. Connecting creates one folder named
          <span class="t-num text-paper">Shoots</span> for optional archive imports and Scribe output.
        </p>
      </div>
      <div class="surface p-5 sm:p-6">
        <p class="eyebrow">Scope</p>
        <p class="mt-3 t-body">
          The folder is only for automatic reconciliation and reviewed copies. Existing files are read only when you select them in Google Drive.
        </p>
        <button type="button" class="btn mt-6 w-full" :disabled="busy === 'connect'" @click="connect">
          {{ busy === 'connect' ? 'Connecting…' : 'Connect optional Drive' }}
        </button>
      </div>
    </div>
  </section>
</template>
