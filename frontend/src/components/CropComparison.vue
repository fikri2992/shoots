<script>
export default {
  name: 'CropComparison',
  props: {
    beforeSrc: { type: String, required: true },
    afterSrc: { type: String, required: true },
    reason: { type: String, default: '' },
  },
  data() {
    return {
      open: false,
      position: 50,
      previousFocus: null,
      bodyOverflow: '',
      pageLocked: false,
    }
  },
  computed: {
    cropClip() {
      return { clipPath: `inset(0 ${100 - this.position}% 0 0)` }
    },
    handlePosition() {
      return { left: `${this.position}%` }
    },
  },
  beforeUnmount() {
    this.unlockPage()
    window.removeEventListener('keydown', this.onWindowKeydown)
  },
  methods: {
    async openComparison(event) {
      this.previousFocus = event?.currentTarget || document.activeElement
      this.open = true
      this.position = 50
      this.bodyOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      this.pageLocked = true
      window.addEventListener('keydown', this.onWindowKeydown)
      await this.$nextTick()
      this.$refs.dialog?.focus()
    },
    closeComparison() {
      this.open = false
      this.unlockPage()
      window.removeEventListener('keydown', this.onWindowKeydown)
      this.$nextTick(() => this.previousFocus?.focus?.())
    },
    unlockPage() {
      if (!this.pageLocked) return
      if (this.bodyOverflow !== '') document.body.style.overflow = this.bodyOverflow
      else document.body.style.removeProperty('overflow')
      this.bodyOverflow = ''
      this.pageLocked = false
    },
    onWindowKeydown(event) {
      if (!this.open) return
      if (event.key === 'Escape') {
        event.preventDefault()
        this.closeComparison()
        return
      }
      if (event.key !== 'Tab') return
      const focusable = [...this.$refs.dialog.querySelectorAll('button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])')]
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    },
  },
}
</script>

<template>
  <div>
    <button
      type="button"
      class="group relative block w-full overflow-hidden rounded-2xl border border-edge bg-black text-left transition hover:border-neutral-500"
      data-tested-crop-preview
      aria-label="Open large before and after crop comparison"
      @click="openComparison"
    >
      <span class="flex min-h-[320px] items-center justify-center sm:min-h-[400px]">
        <img :src="afterSrc" alt="Tested crop preview" class="max-h-[520px] w-full object-contain" />
      </span>
      <span class="absolute inset-x-0 bottom-0 flex items-center justify-between gap-3 bg-gradient-to-t from-black/95 via-black/72 to-transparent px-4 pb-4 pt-16 text-white">
        <span>
          <span class="block text-[13px] font-medium">Open before and after</span>
          <span class="mt-0.5 block text-[11px] text-white/65">Drag the slider to compare</span>
        </span>
        <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-white/25 bg-black/45 transition group-hover:bg-white group-hover:text-black">
          <svg aria-hidden="true" viewBox="0 0 24 24" class="h-5 w-5 fill-none stroke-current stroke-2">
            <circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /><path d="M8 11h6M11 8v6" />
          </svg>
        </span>
      </span>
    </button>

    <p v-if="reason" class="mt-3 t-body text-neutral-300">{{ reason }}</p>
    <p class="mt-1 t-meta">Rendered and compared against the original. The preference is the crop rater's model opinion.</p>

    <div
      v-if="open"
      ref="dialog"
      class="fixed inset-0 z-[120] flex flex-col bg-ink/98 outline-none"
      role="dialog"
      aria-modal="true"
      aria-labelledby="crop-comparison-title"
      tabindex="-1"
    >
      <header class="flex min-h-16 shrink-0 items-center gap-3 border-b border-edge px-4 sm:px-6">
        <div class="min-w-0 flex-1">
          <p class="eyebrow text-accent">Model-tested reframe</p>
          <h2 id="crop-comparison-title" class="mt-1 truncate text-[17px] font-semibold text-paper">Original and tested crop</h2>
        </div>
        <button type="button" class="flex h-11 w-11 items-center justify-center rounded-full border border-edge-strong text-paper hover:border-neutral-500" aria-label="Close crop comparison" @click="closeComparison">
          <svg aria-hidden="true" viewBox="0 0 24 24" class="h-5 w-5 fill-none stroke-current stroke-2">
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
        </button>
      </header>

      <div class="flex min-h-0 flex-1 flex-col p-3 sm:p-6">
        <div class="mx-auto flex w-full max-w-[1280px] shrink-0 justify-end pb-3">
          <p class="hidden max-w-xl text-right t-meta sm:block">The crop changes framing only. It does not change the stored Analysis or call the Shot better.</p>
        </div>

        <div class="relative mx-auto min-h-0 w-full max-w-[1280px] flex-1 overflow-hidden rounded-2xl border border-edge bg-black" data-crop-comparison-stage>
          <img :src="beforeSrc" alt="Original Shot" class="absolute inset-0 h-full w-full object-contain" />
          <div class="absolute inset-0 overflow-hidden" :style="cropClip">
            <img :src="afterSrc" alt="Tested crop" class="absolute inset-0 h-full w-full object-contain" />
          </div>
          <span class="absolute left-3 top-3 rounded-full bg-black/72 px-3 py-1.5 text-[10px] font-semibold tracking-[0.1em] text-white uppercase">Tested crop</span>
          <span class="absolute right-3 top-3 rounded-full bg-black/72 px-3 py-1.5 text-[10px] font-semibold tracking-[0.1em] text-white uppercase">Original</span>
          <span class="pointer-events-none absolute inset-y-0 z-10 w-0.5 -translate-x-1/2 bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.35)]" :style="handlePosition">
            <span class="absolute left-1/2 top-1/2 flex h-12 w-12 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-black/30 bg-white text-black shadow-xl">
              <svg aria-hidden="true" viewBox="0 0 24 24" class="h-5 w-5 fill-none stroke-current stroke-2">
                <path d="m9 7-5 5 5 5M15 7l5 5-5 5" />
              </svg>
            </span>
          </span>
          <input
            v-model.number="position"
            type="range"
            min="0"
            max="100"
            step="1"
            class="absolute inset-0 z-20 h-full w-full cursor-ew-resize opacity-0"
            aria-label="Before and after position"
          />
        </div>

        <p v-if="reason" class="mx-auto mt-3 w-full max-w-[1280px] text-[12px] leading-5 text-muted">{{ reason }}</p>
      </div>
    </div>
  </div>
</template>
