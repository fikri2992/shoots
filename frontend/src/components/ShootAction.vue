<script>
import { mapActions, mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

/**
 * The shutter, always attached to the experiment it answers. `capture="environment"`
 * opens the rear camera on a phone; on desktop it is a file picker.
 *
 * Every frame for a experiment goes through pre-flight first — the experiment's own
 * criteria read on a 640px preview in a few seconds — so a miss is reshot
 * where the user is standing rather than found out an hour later.
 */
export default {
  name: 'ShootAction',
  props: {
    questId: { type: String, default: '' },
    label: { type: String, default: 'Shoot' },
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
    text() {
      if (this.busy === 'preflight') return 'Checking the frame…'
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
  <label class="btn w-full cursor-pointer" :class="working || !connected ? 'pointer-events-none opacity-40' : ''">
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
      :disabled="working || !connected"
      @change="onPick"
    />
  </label>

  <Teleport to="body">
    <div v-if="check" class="fixed inset-0 z-40 flex items-end justify-center bg-black/70 md:items-center md:p-4">
      <div class="w-full max-w-[520px] rounded-t-3xl border-t border-edge bg-panel pb-[env(safe-area-inset-bottom)] md:rounded-3xl md:border">
        <div class="gutter pt-5">
          <p class="t-meta text-accent">Before you send it</p>
          <p class="t-hero mt-2">{{ check.say }}</p>
        </div>

        <ul class="gutter mt-5 space-y-3">
          <li v-for="(c, i) in check.checks" :key="i" class="flex gap-3">
            <span class="mt-0.5 shrink-0" :class="c.met ? 'text-good' : 'text-accent'">{{ c.met ? '✓' : '✗' }}</span>
            <span>
              <span class="t-body" :class="c.met ? 'text-neutral-500' : 'text-neutral-100'">{{ c.criterion }}</span>
              <span v-if="!c.met && c.fix" class="mt-0.5 block t-body text-neutral-400">{{ c.fix }}</span>
            </span>
          </li>
        </ul>

        <p class="gutter mt-4 t-meta">
          Read on a preview in {{ check.seconds }} s, before the upload. The full review runs after you send.
        </p>

        <div class="gutter mt-6 mb-5 flex gap-3">
          <button type="button" class="btn flex-1" @click="again">Shoot again</button>
          <button type="button" class="btn-quiet" @click="send(pending)">Send anyway</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
