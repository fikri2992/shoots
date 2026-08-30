<script>
export default {
  name: 'VisualLoopPrototypePhoto',
  props: {
    image: { type: String, required: true },
    mark: { type: String, default: 'paths' },
    compact: { type: Boolean, default: false },
    scene: { type: String, default: 'market' },
  },
  computed: {
    showPaths() {
      return ['paths', 'try', 'check', 'result'].includes(this.mark)
    },
    showTarget() {
      return ['check', 'result'].includes(this.mark)
    },
    label() {
      return {
        paths: 'Two visible paths',
        notice: 'Foreground interruption',
        try: 'Current path structure',
        check: 'Check both paths and endpoint',
        result: 'Criteria-met result',
        clean: 'Clean Shot',
      }[this.mark]
    },
    leftPath() {
      return this.scene === 'stairwell'
        ? '0,74 17,65 35,54 45,47'
        : '42,124 46,101 50,80 54,62 59,48'
    },
    rightPath() {
      return this.scene === 'stairwell'
        ? '100,76 82,66 65,55 55,47'
        : '94,124 87,103 81,82 75,63 69,48'
    },
    leftOrigin() {
      return this.scene === 'stairwell' ? { x: 0, y: 74 } : { x: 42, y: 124 }
    },
    rightOrigin() {
      return this.scene === 'stairwell' ? { x: 100, y: 76 } : { x: 94, y: 124 }
    },
    target() {
      return this.scene === 'stairwell' ? { x: 50, y: 42 } : { x: 64, y: 43 }
    },
  },
}
</script>

<template>
  <figure class="relative overflow-hidden bg-black" :class="compact ? 'aspect-[16/11]' : 'aspect-[4/5]'">
    <img :src="image" alt="Rainy market aisle with a person carrying a red umbrella" class="h-full w-full object-cover" />
    <div class="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/25 via-transparent to-black/10" />

    <svg
      v-if="mark !== 'clean'"
      aria-hidden="true"
      viewBox="0 0 100 125"
      preserveAspectRatio="none"
      class="pointer-events-none absolute inset-0 h-full w-full"
    >
      <defs>
        <filter id="line-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="0.7" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      <template v-if="showPaths">
        <polyline
          :points="leftPath"
          fill="none"
          stroke="#59d8e6"
          stroke-width="1.35"
          stroke-linecap="round"
          stroke-linejoin="round"
          filter="url(#line-glow)"
          :stroke-dasharray="mark === 'try' ? '3 2' : ''"
        />
        <polyline
          :points="rightPath"
          fill="none"
          stroke="#59d8e6"
          stroke-width="1.35"
          stroke-linecap="round"
          stroke-linejoin="round"
          filter="url(#line-glow)"
          :stroke-dasharray="mark === 'try' ? '3 2' : ''"
        />
        <circle :cx="leftOrigin.x" :cy="leftOrigin.y" r="1.8" fill="#59d8e6" />
        <circle :cx="rightOrigin.x" :cy="rightOrigin.y" r="1.8" fill="#59d8e6" />
      </template>

      <template v-if="mark === 'notice'">
        <polygon
          points="0,58 34,58 47,76 51,125 0,125"
          fill="#f0b429"
          fill-opacity="0.16"
          stroke="#f0b429"
          stroke-width="1.2"
          stroke-dasharray="3 2"
        />
        <polyline
          points="42,124 46,101 50,80 54,62 59,48"
          fill="none"
          stroke="#f0b429"
          stroke-width="1.2"
          stroke-linecap="round"
        />
      </template>

      <template v-if="showTarget">
        <circle :cx="target.x" :cy="target.y" r="8" fill="none" stroke="#f0b429" stroke-width="1.2" />
        <circle :cx="target.x" :cy="target.y" r="1.5" fill="#f0b429" />
      </template>
    </svg>

    <figcaption class="absolute right-3 top-3 rounded-full border border-white/15 bg-black/72 px-3 py-1.5 text-[10px] font-semibold tracking-[0.08em] text-white uppercase">
      {{ label }}
    </figcaption>
  </figure>
</template>
