<script>
import { mapActions, mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/**
 * The phone's camera, straight into the pipeline. `capture="environment"`
 * opens the rear camera on Android/iOS; on desktop it is a file picker.
 */
export default {
  name: 'ShootButton',
  props: {
    questId: { type: String, default: '' },
    label: { type: String, default: 'Shoot' },
    floating: { type: Boolean, default: false },
  },
  emits: ['done'],
  computed: {
    ...mapState(useShootsStore, ['busy', 'connected']),
    working() {
      return this.busy === 'shoot'
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['shoot']),
    async onPick(event) {
      const file = event.target.files?.[0]
      event.target.value = ''
      if (!file) return
      const result = await this.shoot(file, this.questId)
      if (result) this.$emit('done', result)
    },
  },
}
</script>

<template>
  <label
    :class="[
      'inline-flex cursor-pointer items-center justify-center gap-2 font-medium select-none',
      floating
        ? 'h-14 w-14 rounded-full bg-neutral-100 text-neutral-900 shadow-lg shadow-black/40'
        : 'rounded-lg bg-neutral-100 px-3 py-2 text-sm text-neutral-900 hover:bg-white',
      working || !connected ? 'pointer-events-none opacity-40' : '',
    ]"
    :title="connected ? label : 'Connect Drive first'"
  >
    <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
      <circle cx="12" cy="13" r="3.5" />
    </svg>
    <span v-if="!floating">{{ working ? 'Uploading…' : label }}</span>
    <input
      type="file"
      accept="image/*,video/*"
      capture="environment"
      class="hidden"
      :disabled="working || !connected"
      @change="onPick"
    />
  </label>
</template>
