<script>
import { arrow, center, spanBox } from '@/domain/cells'
import { geometry } from '@/domain/guides'

/**
 * The frame with the read drawn over it, in three layers of decreasing
 * quietness: the photographer's guide, then what the panel saw, then exactly
 * one instruction.
 *
 * The SVG viewBox is the cell grid (cols x rows) stretched over the image box,
 * so a cell ref lands in the same place at any screen size and pixels never
 * appear in this component. Guide geometry arrives in frame units (0-1) and is
 * scaled into the same box.
 */
export default {
  name: 'ShotCanvas',
  props: {
    src: { type: String, required: true },
    grid: { type: Object, required: true }, // { cols, rows, width, height }
    composition: { type: Object, default: null },
    guide: { type: String, default: 'none' },
    showFindings: { type: Boolean, default: true },
    layer: { type: String, default: 'all' },
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
    showGuide() {
      return this.showFindings && (this.layer === 'all' || this.layer === 'guide')
    },
    showPanel() {
      return this.showFindings && (this.layer === 'all' || this.layer === 'finding')
    },
    showAction() {
      return this.showFindings && (this.layer === 'all' || this.layer === 'action')
    },
    /** Guide geometry, frame units scaled into the cell viewBox. */
    guideLines() {
      if (!this.showGuide) return []
      const { lines } = geometry(this.guide, this.grid.width / this.grid.height)
      return lines.map((l) => ({
        x1: l.x1 * this.grid.cols,
        y1: l.y1 * this.grid.rows,
        x2: l.x2 * this.grid.cols,
        y2: l.y2 * this.grid.rows,
      }))
    },
    guidePoints() {
      if (!this.showGuide) return []
      const { points } = geometry(this.guide, this.grid.width / this.grid.height)
      return points.map((p) => ({ x: p.x * this.grid.cols, y: p.y * this.grid.rows }))
    },
    subject() {
      if (!this.showPanel || !this.composition) return null
      return spanBox(this.composition.subject_cells)
    },
    /** Where the subject's centre actually landed: the guide's whole point. */
    subjectPoint() {
      if (!this.showPanel || !this.composition) return null
      const { subject_x: x, subject_y: y } = this.composition
      if (typeof x === 'number' && typeof y === 'number') {
        return { x: x * this.grid.cols, y: y * this.grid.rows }
      }
      const box = spanBox(this.composition.subject_cells)
      return box ? center(box) : null
    },
    horizonY() {
      const row = this.showPanel ? this.composition?.horizon_row : null
      return row ? row - 0.5 : null
    },
    crop() {
      return this.showAction && this.composition
        ? spanBox(this.composition.suggested_crop_cells)
        : null
    },
    cropMask() {
      if (!this.crop) return null
      const { x, y, w, h } = this.crop
      // Even-odd path: whole frame minus the crop = the dimmed region.
      return `M0 0H${this.grid.cols}V${this.grid.rows}H0Z M${x} ${y}H${x + w}V${y + h}H${x}Z`
    },
    /**
     * One instruction at a time. A crop wins because it changes the frame
     * itself; otherwise the first change that is genuinely a repositioning.
     * Camera changes are never drawn — a viewpoint is not a vector.
     */
    move() {
      if (this.crop || !this.composition) return null
      const found = (this.composition.moves || []).find(
        (m) => (m.kind || 'move') === 'move' && m.from_cells?.length && m.to_cells?.length,
      )
      if (!found) return null
      const geo = arrow(found.from_cells, found.to_cells)
      const target = spanBox(found.to_cells)
      return geo && target ? { what: found.what, geo, target } : null
    },
    points() {
      return (pts) => pts.map((p) => `${p.x},${p.y}`).join(' ')
    },
  },
}
</script>

<template>
  <div
    class="relative w-full overflow-hidden bg-black md:rounded-xl"
    :data-layer="showFindings ? layer : 'clean'"
    :style="{ aspectRatio: aspect }"
  >
    <img :src="src" alt="" class="absolute inset-0 h-full w-full object-fill" />
    <svg :viewBox="viewBox" preserveAspectRatio="none" class="absolute inset-0 h-full w-full" aria-hidden="true">
      <!-- 1. the photographer's guide: thin, dim, unlabelled -->
      <g stroke="rgba(255,255,255,0.34)" :stroke-width="stroke / 2.4">
        <line v-for="(l, i) in guideLines" :key="'g' + i" v-bind="l" />
      </g>
      <g fill="none" stroke="rgba(255,255,255,0.45)" :stroke-width="stroke / 2.4">
        <circle v-for="(p, i) in guidePoints" :key="'p' + i" :cx="p.x" :cy="p.y" :r="stroke * 1.6" />
      </g>

      <!-- 2. what the panel saw -->
      <line
        v-if="horizonY !== null"
        :x1="0"
        :y1="horizonY"
        :x2="grid.cols"
        :y2="horizonY"
        stroke="#f5f0e7"
        stroke-opacity="0.75"
        :stroke-width="stroke * 0.8"
      />
      <rect
        v-if="subject"
        :x="subject.x"
        :y="subject.y"
        :width="subject.w"
        :height="subject.h"
        fill="none"
        stroke="#f5f0e7"
        stroke-opacity="0.8"
        :stroke-width="stroke * 0.8"
      />
      <circle
        v-if="subjectPoint"
        :cx="subjectPoint.x"
        :cy="subjectPoint.y"
        :r="stroke * 1.5"
        fill="#f5f0e7"
      />

      <!-- 3. one instruction -->
      <template v-if="crop">
        <path :d="cropMask" fill="rgba(0,0,0,0.55)" fill-rule="evenodd" />
        <rect
          :x="crop.x"
          :y="crop.y"
          :width="crop.w"
          :height="crop.h"
          fill="none"
          stroke="white"
          :stroke-width="stroke"
        />
      </template>

      <g v-else-if="move">
        <rect
          :x="move.target.x"
          :y="move.target.y"
          :width="move.target.w"
          :height="move.target.h"
          fill="none"
          stroke="#f0b429"
          stroke-opacity="0.6"
          :stroke-width="stroke * 0.8"
          :stroke-dasharray="`${stroke * 2} ${stroke * 1.5}`"
        />
        <line
          :x1="move.geo.start.x"
          :y1="move.geo.start.y"
          :x2="move.geo.end.x"
          :y2="move.geo.end.y"
          stroke="#f0b429"
          :stroke-width="stroke * 1.2"
        />
        <polygon :points="points(move.geo.head)" fill="#f0b429" />
        <circle :cx="move.geo.start.x" :cy="move.geo.start.y" :r="stroke * 1.4" fill="#f0b429" />
      </g>
    </svg>
  </div>
</template>
