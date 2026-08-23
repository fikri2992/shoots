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
  <section class="col gutter pt-12">
    <p class="t-meta text-accent">Setup, once</p>
    <h1 class="mt-2 t-hero">Let it watch a folder in your Drive.</h1>
    <p class="mt-4 t-body text-neutral-300">
      Shoots makes a <span class="t-num">Shoots</span> folder in your Google Drive. Anything that lands there gets
      read, and the review is written back beside the photo — so the work reaches you where your photos already are,
      not only in here.
    </p>

    <button type="button" class="btn mt-8 w-full" :disabled="busy === 'connect'" @click="connect">
      {{ busy === 'connect' ? 'Connecting…' : 'Connect Drive' }}
    </button>
    <p class="mt-3 t-meta">It only ever sees the folder it made.</p>
  </section>
</template>
