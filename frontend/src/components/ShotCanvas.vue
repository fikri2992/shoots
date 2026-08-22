<script>
import { arrow, spanBox } from '@/domain/cells'

/**
 * The image with the Analyst's composition read drawn over it in cell units.
 * The SVG's viewBox is the grid (cols x rows) stretched over the image box, so
 * a cell ref maps to the same place whatever the screen size. Pixels never
 * appear in this component.
 */
export default {
  name: 'ShotCanvas',
  props: {
    src: { type: String, required: true },
    grid: { type: Object, required: true }, // { cols, rows, width, height }
    composition: { type: Object, default: null },
    showGrid: { type: Boolean, default: false },
  },
  computed: {
    viewBox() {
      return `0 0 ${this.grid.cols} ${this.grid.rows}`
    },
    aspect() {
      return `${this.grid.width} / ${this.grid.height}`
    },
    stroke() {
      // A constant-looking line: ~2px on a 400px-wide image, in cell units.
      return (this.grid.cols / 400) * 2.2
    },
    fontSize() {
      return this.stroke * 5
    },
    subject() {
      return this.composition ? spanBox(this.composition.subject_cells) : null
    },
    crop() {
      return this.composition ? spanBox(this.composition.suggested_crop_cells) : null
    },
    horizonY() {
      const row = this.composition?.horizon_row
      return row ? row - 0.5 : null
    },
    arrows() {
      if (!this.composition) return []
      return this.composition.moves
        .map((move, index) => ({ index: index + 1, move, geo: arrow(move.from_cells, move.to_cells) }))
        .filter((a) => a.geo)
    },
    gridLines() {
      if (!this.showGrid) return []
      const lines = []
      for (let c = 1; c < this.grid.cols; c += 1) lines.push({ x1: c, y1: 0, x2: c, y2: this.grid.rows })
      for (let r = 1; r < this.grid.rows; r += 1) lines.push({ x1: 0, y1: r, x2: this.grid.cols, y2: r })
      return lines
    },
    cropMask() {
      if (!this.crop) return null
      const { x, y, w, h } = this.crop
      const W = this.grid.cols
      const H = this.grid.rows
      // Even-odd path: whole frame minus the crop = the dimmed region.
      return `M0 0H${W}V${H}H0Z M${x} ${y}H${x + w}V${y + h}H${x}Z`
    },
    points() {
      return (pts) => pts.map((p) => `${p.x},${p.y}`).join(' ')
    },
  },
}
</script>

<template>
  <div class="relative w-full overflow-hidden rounded-lg bg-black" :style="{ aspectRatio: aspect }">
    <img :src="src" alt="" class="absolute inset-0 h-full w-full object-fill" />
    <svg
      :viewBox="viewBox"
      preserveAspectRatio="none"
      class="absolute inset-0 h-full w-full"
      aria-hidden="true"
    >
      <g v-if="showGrid" stroke="rgba(255,255,255,0.35)" :stroke-width="stroke / 2">
        <line v-for="(l, i) in gridLines" :key="i" v-bind="l" />
      </g>

      <path v-if="cropMask" :d="cropMask" fill="rgba(0,0,0,0.5)" fill-rule="evenodd" />
      <rect
        v-if="crop"
        :x="crop.x"
        :y="crop.y"
        :width="crop.w"
        :height="crop.h"
        fill="none"
        stroke="white"
        :stroke-width="stroke"
        :stroke-dasharray="`${stroke * 3} ${stroke * 2}`"
      />

      <line
        v-if="horizonY !== null"
        :x1="0"
        :y1="horizonY"
        :x2="grid.cols"
        :y2="horizonY"
        stroke="#ffdc5a"
        :stroke-width="stroke"
      />

      <rect
        v-if="subject"
        :x="subject.x"
        :y="subject.y"
        :width="subject.w"
        :height="subject.h"
        fill="none"
        stroke="#50c8ff"
        :stroke-width="stroke"
      />

      <g v-for="a in arrows" :key="a.index">
        <line
          :x1="a.geo.start.x"
          :y1="a.geo.start.y"
          :x2="a.geo.end.x"
          :y2="a.geo.end.y"
          stroke="#ff5a5a"
          :stroke-width="stroke * 1.3"
        />
        <polygon :points="points(a.geo.head)" fill="#ff5a5a" />
        <circle :cx="a.geo.start.x" :cy="a.geo.start.y" :r="stroke * 1.6" fill="#ff5a5a" />
        <text
          :x="a.geo.end.x + stroke * 3"
          :y="a.geo.end.y - stroke * 2"
          fill="white"
          :font-size="fontSize"
          stroke="black"
          :stroke-width="stroke / 3"
          paint-order="stroke"
          font-family="system-ui, sans-serif"
        >
          {{ a.index }}
        </text>
      </g>
    </svg>
  </div>
</template>
