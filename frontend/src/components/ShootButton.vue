<script>
import { mapActions, mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/**
 * The phone's camera, straight into the pipeline. `capture="environment"`
 * opens the rear camera on Android/iOS; on desktop it is a file picker.
 *
 * For a quest, the frame goes through pre-flight first: the quest's criteria
 * checked on a preview in a few seconds, so a miss is reshot on the spot.
 */
export default {
  name: 'ShootButton',
  props: {
    questId: { type: String, default: '' },
    label: { type: String, default: 'Shoot' },
    floating: { type: Boolean, default: false },
  },
  emits: ['done'],
  data() {
    return { pending: null, check: null }
  },
  computed: {
    ...mapState(useShootsStore, ['busy', 'connected']),
    working() {
      return this.busy === 'shoot' || this.busy === 'preflight'
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['shoot', 'preflight']),
    async onPick(event) {
      const file = event.target.files?.[0]
      event.target.value = ''
      if (!file) return
      if (this.questId && file.type.startsWith('image/')) {
        const check = await this.preflight(file, this.questId)
        if (check && !check.ready) {
          this.pending = file
          this.check = check
          return
        }
      }
      await this.send(file)
    },
    async send(file) {
      this.pending = null
      this.check = null
      const result = await this.shoot(file, this.questId)
      if (result) this.$emit('done', result)
    },
    again() {
      this.pending = null
      this.check = null
      this.$refs.input?.click()
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
    <span v-if="!floating">{{ busy === 'preflight' ? 'Checking…' : working ? 'Uploading…' : label }}</span>
    <input
      ref="input"
      type="file"
      accept="image/*,video/*"
      capture="environment"
      class="hidden"
      :disabled="working || !connected"
      @change="onPick"
    />
  </label>

  <Teleport to="body">
    <div v-if="check" class="fixed inset-0 z-40 flex items-end justify-center bg-black/60 p-3 md:items-center">
      <div class="w-full max-w-md rounded-2xl border border-edge bg-panel p-4 shadow-2xl">
        <p class="text-[11px] font-medium uppercase tracking-wide text-amber-300">Shoot again</p>
        <p class="mt-1 text-base text-neutral-100">{{ check.say }}</p>
        <ul class="mt-3 space-y-1.5 text-sm">
          <li v-for="(c, i) in check.checks" :key="i" class="flex gap-2">
            <span :class="c.met ? 'text-emerald-400' : 'text-amber-400'">{{ c.met ? '✓' : '✗' }}</span>
            <span>
              <span :class="c.met ? 'text-neutral-400' : 'text-neutral-200'">{{ c.criterion }}</span>
              <span v-if="!c.met && c.fix" class="block text-neutral-400">{{ c.fix }}</span>
            </span>
          </li>
        </ul>
        <p class="mt-2 text-[10px] text-neutral-600">Checked on a preview in {{ check.seconds }} s. The full review happens after sending.</p>
        <div class="mt-4 flex gap-2">
          <button type="button" class="flex-1 rounded-lg bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-900" @click="again">Shoot again</button>
          <button type="button" class="rounded-lg border border-edge-strong px-3 py-2 text-sm text-neutral-300" @click="send(pending)">Send anyway</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
