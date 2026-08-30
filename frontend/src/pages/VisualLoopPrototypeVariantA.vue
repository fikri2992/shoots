<script>
import VisualLoopPrototypePhoto from '@/pages/VisualLoopPrototypePhoto.vue'

export default {
  name: 'VisualLoopPrototypeVariantA',
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
    isStory() {
      return this.step < 4
    },
    sectionLabel() {
      if (this.step < 4) return `Visual story · ${this.step + 1} of 4`
      if (this.step < 7) return 'Open Experiment'
      if (this.step === 7) return 'Experiment result'
      return 'What Shoots remembers'
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
  <div class="min-h-[844px] bg-ink pb-28">
    <header class="flex h-16 items-center justify-between border-b border-edge px-5">
      <button type="button" class="tap-target text-muted" aria-label="Back">←</button>
      <p class="text-[14px] font-semibold">Shot story</p>
      <span class="rounded-full bg-white/5 px-3 py-1.5 text-[10px] font-semibold tracking-[0.08em] text-muted uppercase">Prototype</span>
    </header>

    <div class="px-4 pt-4">
      <div class="overflow-hidden rounded-[24px] border border-edge bg-panel">
        <VisualLoopPrototypePhoto :image="shownImage" :mark="content.mark" :scene="shownScene" />
        <section class="p-5">
          <div class="flex items-center justify-between gap-4">
            <p class="eyebrow text-accent">{{ sectionLabel }}</p>
            <div v-if="isStory" class="flex gap-1.5" aria-hidden="true">
              <span v-for="index in 4" :key="index" class="h-1.5 w-1.5 rounded-full" :class="index - 1 === step ? 'bg-accent' : 'bg-neutral-700'" />
            </div>
          </div>
          <h1 class="mt-3 text-[27px] leading-8 font-semibold tracking-[-0.035em] text-paper">{{ content.title }}</h1>
          <p class="mt-3 text-[14px] leading-6 text-neutral-300">{{ content.body }}</p>

          <div v-if="content.detail" class="mt-4 rounded-xl border border-white/8 bg-white/[0.035] p-3">
            <p class="text-[12px] leading-5 text-neutral-300">{{ content.detail }}</p>
          </div>

          <div v-if="step === 4" class="mt-4 space-y-2 border-l-2 border-accent pl-3 text-[12px] leading-5 text-neutral-300">
            <p>At least two separate paths remain visible.</p>
            <p>Their direction converges near that Scene's subject.</p>
            <p>Leading lines is corroborated by the Analyst panel.</p>
          </div>

          <div v-if="step === 7" class="mt-4 grid grid-cols-3 gap-2">
            <div v-for="(state, index) in ['Not yet', 'Criteria met', 'Not yet']" :key="state + index" class="overflow-hidden rounded-xl border" :class="index === 1 ? 'border-accent/60' : 'border-edge'">
              <img :src="resultImages[index]" alt="" class="aspect-square w-full object-cover" />
              <p class="px-2 py-2 text-[9px] font-semibold" :class="index === 1 ? 'text-accent' : 'text-muted'">{{ state }}</p>
            </div>
          </div>

          <div class="mt-5 flex items-center gap-2">
            <button v-if="step > 0" type="button" class="btn-quiet w-24 px-3" @click="$emit('back')">Back</button>
            <button type="button" class="btn flex-1" @click="$emit('advance')">{{ actionLabel }}</button>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
