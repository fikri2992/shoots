<script>
import VisualLoopPrototypePhoto from '@/pages/VisualLoopPrototypePhoto.vue'

export default {
  name: 'VisualLoopPrototypeVariantC',
  components: { VisualLoopPrototypePhoto },
  props: {
    image: { type: String, required: true },
    step: { type: Number, required: true },
    content: { type: Object, required: true },
    actionLabel: { type: String, required: true },
    resultImages: { type: Array, required: true },
  },
  emits: ['advance', 'back', 'jump'],
  computed: {
    chapter() {
      if (this.step < 4) return 'learn'
      if (this.step < 7) return 'test'
      return 'proof'
    },
    storyRows() {
      return [
        { label: 'KEEP', title: 'Two aisle edges lead to the umbrella', mark: 'paths' },
        { label: 'NOTICE', title: 'The left foreground interrupts one path', mark: 'notice' },
        { label: 'TRY', title: 'Carry the two-path idea elsewhere', mark: 'try' },
        { label: 'CHECK', title: 'Two paths should meet near a new subject', mark: 'check' },
      ]
    },
  },
  methods: {
    selectChapter(chapter) {
      this.$emit('jump', { learn: 0, test: 4, proof: 7 }[chapter])
    },
  },
}
</script>

<template>
  <div class="min-h-[844px] bg-ink pb-28">
    <header class="px-5 pb-4 pt-6">
      <p class="eyebrow text-accent">Leading lines</p>
      <h1 class="mt-2 text-[29px] leading-8 font-semibold tracking-[-0.04em]">Technique notebook</h1>
      <nav class="mt-5 grid grid-cols-3 rounded-xl bg-panel p-1" aria-label="Prototype chapters">
        <button v-for="name in ['learn', 'test', 'proof']" :key="name" type="button" class="min-h-10 rounded-lg text-[11px] font-semibold capitalize" :class="chapter === name ? 'bg-paper text-ink' : 'text-muted'" @click="selectChapter(name)">
          {{ name }}
        </button>
      </nav>
    </header>

    <section v-if="chapter === 'learn'" class="px-4">
      <div class="overflow-hidden rounded-[24px] border border-edge bg-panel">
        <VisualLoopPrototypePhoto :image="image" :mark="content.mark" compact />
        <div class="p-4">
          <p class="eyebrow text-accent">One thread</p>
          <div class="mt-3 space-y-1">
            <button
              v-for="(row, index) in storyRows"
              :key="row.label"
              type="button"
              class="grid w-full grid-cols-[58px_1fr] gap-2 rounded-xl px-3 py-3 text-left"
              :class="step === index ? 'bg-accent/10 ring-1 ring-accent/35' : 'bg-white/[0.025]'"
              @click="$emit('jump', index)"
            >
              <span class="text-[9px] font-bold tracking-[0.08em]" :class="step === index ? 'text-accent' : 'text-muted'">{{ row.label }}</span>
              <span class="text-[12px] leading-4 text-neutral-200">{{ row.title }}</span>
            </button>
          </div>
          <button type="button" class="btn mt-4 w-full" @click="$emit('advance')">{{ actionLabel }}</button>
        </div>
      </div>
    </section>

    <section v-else-if="chapter === 'test'" class="space-y-4 px-4">
      <div class="rounded-[24px] border border-accent/40 bg-accent/[0.055] p-5">
        <div class="flex items-center justify-between gap-3">
          <p class="eyebrow text-accent">Experiment</p>
          <span class="rounded-full border border-accent/30 px-2.5 py-1 text-[9px] font-semibold text-accent">{{ step === 4 ? 'READY' : step === 5 ? 'CAPTURING' : 'PROCESSING' }}</span>
        </div>
        <h2 class="mt-3 text-[24px] leading-7 font-semibold tracking-[-0.03em]">Can you use this idea elsewhere?</h2>
        <p class="mt-2 text-[13px] leading-5 text-neutral-300">This can wait for another day. The Criteria describe the Technique, not the market.</p>
      </div>

      <div class="rounded-[20px] border border-edge bg-panel p-4">
        <p class="eyebrow">Shoots will check</p>
        <ol class="mt-3 space-y-3 text-[12px] leading-5 text-neutral-300">
          <li class="flex gap-3"><span class="text-accent">01</span><span>At least two separate paths remain visible.</span></li>
          <li class="flex gap-3"><span class="text-accent">02</span><span>Their direction converges near that Scene's subject.</span></li>
          <li class="flex gap-3"><span class="text-accent">03</span><span>The Analyst panel corroborates Leading lines.</span></li>
        </ol>
      </div>

      <div class="rounded-[20px] border border-edge bg-panel p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-[13px] font-semibold">Capture Session</p>
            <p class="mt-1 text-[11px] text-muted">{{ step === 4 ? 'Saved until you are ready' : step === 5 ? 'Reserved on another day, camera owns the shutter' : '3 exact members committed' }}</p>
          </div>
          <span class="h-3 w-3 rounded-full" :class="step >= 5 ? 'bg-accent' : 'bg-neutral-700'" />
        </div>
      </div>

      <div class="flex gap-2">
        <button type="button" class="btn-quiet w-24" @click="$emit('back')">Back</button>
        <button type="button" class="btn flex-1" @click="$emit('advance')">{{ actionLabel }}</button>
      </div>
    </section>

    <section v-else class="space-y-4 px-4">
      <div class="overflow-hidden rounded-[24px] border border-accent/45 bg-panel">
        <VisualLoopPrototypePhoto :image="resultImages[1]" mark="result" scene="stairwell" compact />
        <div class="p-5">
          <p class="eyebrow text-accent">Representative result · Shot 2</p>
          <h2 class="mt-2 text-[26px] leading-7 font-semibold tracking-[-0.035em]">Criteria met once</h2>
          <p class="mt-2 text-[13px] leading-5 text-neutral-300">All three later Shots settled. The stairwell is the earliest result where two new paths met near a new subject.</p>
        </div>
      </div>

      <div class="grid grid-cols-3 gap-2">
        <div v-for="(state, index) in ['Not yet', 'Met', 'Not yet']" :key="state + index" class="overflow-hidden rounded-xl border" :class="index === 1 ? 'border-accent/60 bg-accent/[0.05]' : 'border-edge bg-panel'">
          <img :src="resultImages[index]" alt="" class="aspect-square w-full object-cover" />
          <p class="px-2 py-2 text-[9px] font-semibold" :class="index === 1 ? 'text-accent' : 'text-muted'">{{ index + 1 }} · {{ state }}</p>
        </div>
      </div>

      <div class="rounded-[20px] border border-edge bg-panel p-4">
        <p class="eyebrow">Memory changed</p>
        <p class="mt-3 text-[14px] leading-6 text-paper">Leading lines now has one evaluable Reproduce session across a different Scene, with Criteria met.</p>
        <div v-if="step >= 8" class="mt-4 border-t border-edge pt-4">
          <p class="text-[11px] font-semibold text-accent">SCOUT ADAPTED</p>
          <p class="mt-1 text-[12px] leading-5 text-neutral-300">It withholds another Leading lines test and can offer warm against cool next.</p>
        </div>
      </div>

      <div class="flex gap-2">
        <button type="button" class="btn-quiet w-24" @click="$emit('back')">Back</button>
        <button type="button" class="btn flex-1" @click="$emit('advance')">{{ actionLabel }}</button>
      </div>
    </section>
  </div>
</template>
