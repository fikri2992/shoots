<script>
export default {
  name: 'JourneyPrototypeSwitcher',
  props: {
    variants: { type: Array, required: true },
    current: { type: String, required: true },
  },
  emits: ['select'],
  data() {
    return { isDev: import.meta.env.DEV }
  },
  computed: {
    index() {
      return Math.max(0, this.variants.findIndex((item) => item.key === this.current))
    },
    label() {
      const variant = this.variants[this.index]
      return `${variant.key} · ${variant.name}`
    },
  },
  mounted() {
    window.addEventListener('keydown', this.onKeydown)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    cycle(step) {
      const next = (this.index + step + this.variants.length) % this.variants.length
      this.$emit('select', this.variants[next].key)
    },
    onKeydown(event) {
      if (event.target?.matches?.('input, textarea, [contenteditable]')) return
      if (event.key === 'ArrowLeft') {
        event.preventDefault()
        this.cycle(-1)
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault()
        this.cycle(1)
      }
    },
  },
}
</script>

<template>
  <nav
    v-if="isDev"
    class="fixed bottom-4 left-1/2 z-[100] flex -translate-x-1/2 items-center rounded-full border border-white/15 bg-paper p-1.5 text-ink shadow-[0_18px_55px_rgba(0,0,0,0.55)]"
    aria-label="Journey prototype variants"
  >
    <button
      type="button"
      class="flex h-11 w-11 items-center justify-center rounded-full transition hover:bg-black/10"
      aria-label="Previous variant"
      @click="cycle(-1)"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" class="h-5 w-5 fill-none stroke-current stroke-2">
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>
    <span class="min-w-[178px] px-2 text-center sm:min-w-[230px]">
      <span class="block text-[9px] font-bold tracking-[0.16em] uppercase opacity-55">Prototype</span>
      <span class="block text-[12px] font-semibold tracking-[-0.01em]">{{ label }}</span>
    </span>
    <button
      type="button"
      class="flex h-11 w-11 items-center justify-center rounded-full transition hover:bg-black/10"
      aria-label="Next variant"
      @click="cycle(1)"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" class="h-5 w-5 fill-none stroke-current stroke-2">
        <path d="m9 18 6-6-6-6" />
      </svg>
    </button>
  </nav>
</template>
