<script>
import { cameraMove, harmony, measured, readout } from '@/domain/tone'

/**
 * What the frame measures, under the frame, always visible.
 *
 * Deliberately not behind a disclosure and deliberately not amber. Amber means
 * "the agent decided this"; a measurement decided nothing — it is the instrument
 * reading that the critique, the findings and the panel all argue from, and the
 * one part of the page a photographer can check against their own camera.
 */
export default {
  name: 'MeasuredStrip',
  props: {
    tone: { type: Object, default: null },
    motion: { type: Object, default: null },
  },
  computed: {
    rows() {
      return readout(this.tone)
    },
    harmony() {
      return harmony(this.tone)
    },
    move() {
      return cameraMove(this.motion)
    },
    shown() {
      return measured(this.tone) || Boolean(this.move)
    },
  },
}
</script>

<template>
  <div v-if="shown" class="border-y border-edge bg-panel/60 py-3">
    <dl class="flex flex-wrap gap-x-6 gap-y-3">
      <div v-for="row in rows" :key="row.key">
        <dd class="t-num text-[15px] leading-none text-neutral-200">
          {{ row.value }}<span class="text-[11px] text-muted">{{ row.unit }}</span>
        </dd>
        <dt class="mt-1 t-meta">{{ row.label }}</dt>
      </div>
    </dl>
    <p v-if="harmony || move" class="mt-3 t-meta">
      <span v-if="harmony">{{ harmony }}</span>
      <span v-if="harmony && move"> · </span>
      <span v-if="move">{{ move }}</span>
    </p>
  </div>
</template>
