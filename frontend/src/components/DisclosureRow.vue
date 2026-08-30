<script>
let nextDisclosureId = 0

/**
 * One line, a count, a chevron; the detail opens in place. Everything that is
 * evidence rather than instruction lives behind one of these, so the default
 * screen stays one decision long.
 */
export default {
  name: 'DisclosureRow',
  props: {
    label: { type: String, required: true },
    count: { type: [Number, String], default: '' },
    open: { type: Boolean, default: false },
  },
  data() {
    nextDisclosureId += 1
    return { shown: this.open, panelId: `disclosure-${nextDisclosureId}` }
  },
}
</script>

<template>
  <div class="border-b border-edge last:border-b-0">
    <button
      type="button"
      class="flex w-full items-center gap-2 py-3.5 text-left text-[13px] text-neutral-400 transition hover:text-paper"
      :aria-expanded="shown"
      :aria-controls="panelId"
      @click="shown = !shown"
    >
      <span>{{ label }}</span>
      <span v-if="count !== ''" class="t-num text-[11px] text-muted">{{ count }}</span>
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        class="ml-auto h-4 w-4 transition-transform"
        :class="shown ? 'rotate-90' : ''"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M9 6l6 6-6 6" />
      </svg>
    </button>
    <div v-if="shown" :id="panelId" class="pb-4"><slot /></div>
  </div>
</template>
