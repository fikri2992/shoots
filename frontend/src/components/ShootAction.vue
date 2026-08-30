<script>
import { mapActions, mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/**
 * The shutter, always attached to the experiment it answers. `capture="environment"`
 * opens the rear camera on a phone; on desktop it is a file picker.
 *
 * Every Shot for an Experiment goes through pre-flight first — the Experiment's own
 * criteria read on a 640px preview in a few seconds — so a miss is reshot
 * where the user is standing rather than found out an hour later.
 */
export default {
  name: 'ShootAction',
  props: {
    experimentId: { type: String, default: '' },
    label: { type: String, default: 'Shoot' },
  },
  emits: ['done'],
  data() {
    return { pending: null, check: null }
  },
  computed: {
    ...mapState(useShootsStore, ['busy', 'accountReady']),
    working() {
      return this.busy === 'shoot' || this.busy === 'preflight'
    },
    text() {
      if (this.busy === 'preflight') return 'Checking the Shot…'
      if (this.busy === 'shoot') return 'Sending…'
      return this.label
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['shoot', 'preflight']),
    async onPick(event) {
      const file = event.target.files?.[0]
      event.target.value = ''
      if (!file) return
      if (this.experimentId && file.type.startsWith('image/')) {
        const check = await this.preflight(file, this.experimentId)
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
      const result = await this.shoot(file, this.experimentId)
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
  <label class="btn w-full cursor-pointer" :class="working || !accountReady ? 'pointer-events-none opacity-40' : ''">
    <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
      <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
      <circle cx="12" cy="13" r="3.4" />
    </svg>
    {{ text }}
    <input
      ref="input"
      type="file"
      accept="image/*,video/*"
      capture="environment"
      class="hidden"
      :disabled="working || !accountReady"
      @change="onPick"
    />
  </label>

  <Teleport to="body">
    <div v-if="check" class="fixed inset-0 z-40 flex items-end justify-center bg-black/76 md:items-center md:p-4">
      <div class="w-full max-w-[540px] rounded-t-[28px] border-t border-edge bg-panel pb-[env(safe-area-inset-bottom)] shadow-2xl md:rounded-[28px] md:border">
        <div class="mx-auto mt-3 h-1 w-10 rounded-full bg-edge-strong" />
        <div class="gutter pt-5">
          <p class="eyebrow text-accent">Before this becomes a Shot</p>
          <p class="mt-3 text-[25px] leading-8 font-semibold tracking-[-0.03em] text-paper">{{ check.say }}</p>
        </div>

        <ul class="gutter mt-6 space-y-2">
          <li v-for="(c, i) in check.checks" :key="i" class="flex gap-3 rounded-xl border border-edge bg-panel-2/50 p-3.5">
            <span class="mt-0.5 shrink-0 text-[12px]" :class="c.met ? 'text-muted' : 'text-accent'">{{ c.met ? 'SEEN' : 'MOVE' }}</span>
            <span>
              <span class="t-body" :class="c.met ? 'text-muted' : 'text-paper'">{{ c.criterion }}</span>
              <span v-if="!c.met && c.fix" class="mt-1 block t-body text-accent">{{ c.fix }}</span>
            </span>
          </li>
        </ul>

        <p class="gutter mt-4 t-meta">
          Temporary preview · {{ check.seconds }} s · no Shot created yet. Full Analysis begins only after you send.
        </p>

        <div class="gutter mt-6 mb-5 flex gap-3">
          <button type="button" class="btn flex-1" @click="again">Shoot again</button>
          <button type="button" class="btn-quiet px-4" @click="send(pending)">Use it anyway</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
