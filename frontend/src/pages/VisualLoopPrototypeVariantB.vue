<script>
import VisualLoopPrototypePhoto from '@/pages/VisualLoopPrototypePhoto.vue'

export default {
  name: 'VisualLoopPrototypeVariantB',
  components: { VisualLoopPrototypePhoto },
  props: {
    image: { type: String, required: true },
    step: { type: Number, required: true },
    content: { type: Object, required: true },
    actionLabel: { type: String, required: true },
    resultImages: { type: Array, required: true },
  },
  emits: ['advance', 'back'],
  computed: {
    stages() {
      return [
        { name: 'Read', threshold: 0, note: 'One supported lesson from this Shot' },
        { name: 'Plan', threshold: 4, note: 'Experiment and Criteria fixed first' },
        { name: 'Act', threshold: 5, note: 'Capture Session owns exact result Shots' },
        { name: 'Check', threshold: 7, note: 'Judge settles every explicit result' },
        { name: 'Adapt', threshold: 8, note: 'Technique memory changes the next route' },
      ]
    },
    stageStatus() {
      return (stage, index) => {
        const next = this.stages[index + 1]
        if (this.step < stage.threshold) return 'waiting'
        if (!next || this.step < next.threshold) return 'current'
        return 'done'
      }
    },
    shownImage() {
      return this.step >= 7 ? this.resultImages[1] : this.image
    },
    shownScene() {
      return this.step >= 7 ? 'stairwell' : 'market'
    },
  },
}
</script>

<template>
  <div class="min-h-[844px] bg-[#0d0d10] pb-32">
    <header class="border-b border-edge px-5 pb-4 pt-6">
      <p class="eyebrow text-accent">One managed job</p>
      <div class="mt-2 flex items-start justify-between gap-4">
        <div>
          <h1 class="text-[25px] leading-7 font-semibold tracking-[-0.03em]">Can I use this idea elsewhere?</h1>
          <p class="mt-2 text-[12px] leading-5 text-muted">Every action and result stays attached to Leading lines.</p>
        </div>
        <span class="rounded-full border border-white/10 px-2.5 py-1 text-[9px] font-semibold text-muted">LIVE RECEIPT</span>
      </div>
    </header>

    <section class="border-b border-edge bg-black">
      <VisualLoopPrototypePhoto :image="shownImage" :mark="content.mark" :scene="shownScene" compact />
      <div class="border-t border-white/8 px-5 py-4">
        <p class="eyebrow text-accent">Now</p>
        <h2 class="mt-1 text-[19px] font-semibold tracking-[-0.02em]">{{ content.title }}</h2>
        <p class="mt-1 text-[12px] leading-5 text-neutral-400">{{ content.body }}</p>
      </div>
    </section>

    <ol class="px-5 py-5">
      <li v-for="(stage, index) in stages" :key="stage.name" class="relative grid grid-cols-[24px_1fr] gap-3 pb-5 last:pb-0">
        <span v-if="index < stages.length - 1" class="absolute left-[11px] top-6 h-full w-px bg-edge" />
        <span
          class="relative z-10 mt-0.5 flex h-6 w-6 items-center justify-center rounded-full border text-[10px] font-bold"
          :class="stageStatus(stage, index) === 'done' ? 'border-accent bg-accent text-ink' : stageStatus(stage, index) === 'current' ? 'border-accent bg-accent/15 text-accent' : 'border-edge-strong bg-panel text-muted'"
        >
          {{ stageStatus(stage, index) === 'done' ? '✓' : index + 1 }}
        </span>
        <div class="rounded-2xl border p-3.5" :class="stageStatus(stage, index) === 'current' ? 'border-accent/45 bg-accent/[0.06]' : 'border-edge bg-panel/60'">
          <div class="flex items-center justify-between gap-3">
            <p class="text-[13px] font-semibold">{{ stage.name }}</p>
            <span class="text-[9px] font-semibold uppercase" :class="stageStatus(stage, index) === 'current' ? 'text-accent' : 'text-muted'">{{ stageStatus(stage, index) }}</span>
          </div>
          <p class="mt-1 text-[11px] leading-4 text-muted">{{ stage.note }}</p>

          <div v-if="stage.name === 'Plan' && step >= 4" class="mt-3 border-t border-white/8 pt-3 text-[11px] leading-5 text-neutral-300">
            <p><span class="text-muted">Criteria locked</span> · 3 checks</p>
            <p><span class="text-muted">Source</span> · Shot 13, Keeper</p>
          </div>
          <div v-if="stage.name === 'Act' && step >= 5" class="mt-3 border-t border-white/8 pt-3 text-[11px] leading-5 text-neutral-300">
            <p><span class="text-muted">Capture Session</span> · {{ step >= 6 ? '3 members committed' : 'reserved' }}</p>
          </div>
          <div v-if="stage.name === 'Check' && step >= 7" class="mt-3 border-t border-white/8 pt-3 text-[11px] leading-5 text-neutral-300">
            <p><span class="text-muted">Result</span> · Criteria met by stairwell Shot 2 of 3</p>
          </div>
          <div v-if="stage.name === 'Adapt' && step >= 8" class="mt-3 border-t border-white/8 pt-3 text-[11px] leading-5 text-neutral-300">
            <p>1 evaluable Reproduce session across a different Scene. Scout now withholds another Leading lines test.</p>
          </div>
        </div>
      </li>
    </ol>

    <div class="sticky bottom-20 px-5">
      <div class="flex gap-2 rounded-2xl border border-white/10 bg-black/90 p-2 shadow-2xl backdrop-blur">
        <button v-if="step > 0" type="button" class="btn-quiet w-20 px-2" @click="$emit('back')">Back</button>
        <button type="button" class="btn flex-1" @click="$emit('advance')">{{ actionLabel }}</button>
      </div>
    </div>
  </div>
</template>
