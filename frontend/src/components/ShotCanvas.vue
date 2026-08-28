<script>
import { arrow, center, collinearLine, parseRef, spanBox } from '@/domain/cells'
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
    mark: { type: Object, default: null },
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
      return !this.storyActive && this.showFindings && (this.layer === 'all' || this.layer === 'guide')
    },
    showPanel() {
      return !this.storyActive && this.showFindings && (this.layer === 'all' || this.layer === 'finding')
    },
    showAction() {
      return !this.storyActive && this.showFindings && (this.layer === 'all' || this.layer === 'action')
    },
    storyActive() {
      return this.showFindings && Boolean(this.mark?.kind && this.mark.kind !== 'none')
    },
    storyPaths() {
      if (!this.storyActive || this.mark.kind !== 'line') return []
      const explicit = (this.mark.paths || [])
        .map((path) => ({
          points: this.cellPoints(path.points),
          targets: this.cellPoints(path.leads_to),
        }))
        .filter((path) => path.points.length >= 2)
      if (explicit.length) return explicit
      const line = collinearLine(this.mark.cells)
      return line ? [{ points: [line.start, line.end], targets: [] }] : []
    },
    storyBoxes() {
      if (!this.storyActive) return []
      const kind = this.mark.kind
      if (['pair', 'planes', 'instances'].includes(kind)) {
        return (this.mark.regions || [])
          .map((region) => ({ ...spanBox(region.cells), role: region.role, order: region.order }))
          .filter((box) => Number.isFinite(box.x))
          .sort((a, b) => (a.order || 0) - (b.order || 0))
      }
      if (['region', 'frame', 'finding'].includes(kind)) {
        const box = spanBox(this.mark.cells)
        return box ? [box] : []
      }
      return []
    },
    storyPoint() {
      if (!this.storyActive || this.mark.kind !== 'point') return null
      const box = spanBox(this.mark.cells)
      return box ? center(box) : this.locatedSubjectPoint
    },
    storyMove() {
      if (!this.storyActive || this.mark.kind !== 'move') return null
      const geo = arrow(this.mark.cells, this.mark.to_cells)
      const target = spanBox(this.mark.to_cells)
      return geo && target ? { geo, target } : null
    },
    storyCrop() {
      return this.storyActive && this.mark.kind === 'crop' ? spanBox(this.mark.cells) : null
    },
    storyCropMask() {
      if (!this.storyCrop) return ''
      const { x, y, w, h } = this.storyCrop
      return `M0 0H${this.grid.cols}V${this.grid.rows}H0Z M${x} ${y}H${x + w}V${y + h}H${x}Z`
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
    locatedSubjectPoint() {
      if (!this.composition) return null
      const { subject_x: x, subject_y: y } = this.composition
      if (typeof x === 'number' && typeof y === 'number') {
        return { x: x * this.grid.cols, y: y * this.grid.rows }
      }
      const box = spanBox(this.composition.subject_cells)
      return box ? center(box) : null
    },
    subjectPoint() {
      return this.showPanel ? this.locatedSubjectPoint : null
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
      if (!this.showAction || this.crop || !this.composition) return null
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
  methods: {
    cellPoints(refs = []) {
      return refs
        .map(parseRef)
        .filter(
          (cell) =>
            cell &&
            cell.col >= 0 &&
            cell.col < this.grid.cols &&
            cell.row >= 0 &&
            cell.row < this.grid.rows,
        )
        .map((cell) => ({ x: cell.col + 0.5, y: cell.row + 0.5 }))
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
      <!-- One selected visual-story claim. No geometry means no story mark. -->
      <g v-if="storyActive">
        <template v-if="mark.kind === 'line'">
          <g v-for="(path, i) in storyPaths" :key="`story-line-${i}`">
            <polyline
              :points="points(path.points)"
              fill="none"
              stroke="rgba(0,0,0,0.6)"
              :stroke-width="stroke * 2.2"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
            <polyline
              data-story-line
              :points="points(path.points)"
              fill="none"
              stroke="#36c4dc"
              :stroke-width="stroke"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
            <circle
              v-for="(target, j) in path.targets"
              :key="`target-${i}-${j}`"
              data-story-target
              :cx="target.x"
              :cy="target.y"
              :r="stroke * 2.3"
              fill="rgba(54,196,220,0.18)"
              stroke="#36c4dc"
              :stroke-width="stroke * 0.7"
            />
          </g>
        </template>

        <template v-if="['region', 'pair', 'instances', 'planes'].includes(mark.kind)">
          <rect
            v-for="(box, i) in storyBoxes"
            :key="`story-region-${i}`"
            data-story-region
            :x="box.x"
            :y="box.y"
            :width="box.w"
            :height="box.h"
            :fill="i % 2 ? 'rgba(203,126,235,0.13)' : 'rgba(54,196,220,0.13)'"
            :stroke="i % 2 ? '#cb7eeb' : '#36c4dc'"
            :stroke-width="stroke * 0.85"
          />
          <line
            v-if="mark.kind === 'pair' && storyBoxes.length >= 2"
            data-story-pair
            :x1="storyBoxes[0].x + storyBoxes[0].w / 2"
            :y1="storyBoxes[0].y + storyBoxes[0].h / 2"
            :x2="storyBoxes[1].x + storyBoxes[1].w / 2"
            :y2="storyBoxes[1].y + storyBoxes[1].h / 2"
            stroke="rgba(245,240,231,0.75)"
            :stroke-width="stroke * 0.65"
            :stroke-dasharray="`${stroke * 2} ${stroke * 1.4}`"
          />
          <text
            v-for="(box, i) in mark.kind === 'planes' ? storyBoxes : []"
            :key="`plane-label-${i}`"
            :x="box.x + stroke"
            :y="box.y + fontSize"
            fill="#f5f0e7"
            :font-size="fontSize"
          >{{ i + 1 }}</text>
        </template>

        <template v-if="mark.kind === 'frame' && storyBoxes[0]">
          <rect
            data-story-frame
            :x="storyBoxes[0].x"
            :y="storyBoxes[0].y"
            :width="storyBoxes[0].w"
            :height="storyBoxes[0].h"
            fill="rgba(54,196,220,0.08)"
            stroke="#36c4dc"
            :stroke-width="stroke"
          />
          <rect
            :x="storyBoxes[0].x + stroke * 2"
            :y="storyBoxes[0].y + stroke * 2"
            :width="Math.max(0, storyBoxes[0].w - stroke * 4)"
            :height="Math.max(0, storyBoxes[0].h - stroke * 4)"
            fill="none"
            stroke="rgba(54,196,220,0.65)"
            :stroke-width="stroke * 0.7"
          />
        </template>

        <circle
          v-if="storyPoint"
          data-story-point
          :cx="storyPoint.x"
          :cy="storyPoint.y"
          :r="stroke * 2.5"
          fill="rgba(54,196,220,0.18)"
          stroke="#36c4dc"
          :stroke-width="stroke"
        />

        <rect
          v-if="mark.kind === 'whole_frame' || (mark.kind === 'finding' && !storyBoxes.length)"
          data-story-whole-frame
          x="0"
          y="0"
          :width="grid.cols"
          :height="grid.rows"
          fill="rgba(255,84,90,0.05)"
          stroke="#ff545a"
          :stroke-width="stroke"
        />
        <rect
          v-for="(box, i) in mark.kind === 'finding' ? storyBoxes : []"
          :key="`story-finding-${i}`"
          data-story-finding
          :x="box.x"
          :y="box.y"
          :width="box.w"
          :height="box.h"
          fill="rgba(255,84,90,0.12)"
          stroke="#ff545a"
          :stroke-width="stroke"
        />

        <template v-if="storyCrop">
          <path :d="storyCropMask" fill="rgba(0,0,0,0.55)" fill-rule="evenodd" />
          <rect
            data-story-crop
            :x="storyCrop.x"
            :y="storyCrop.y"
            :width="storyCrop.w"
            :height="storyCrop.h"
            fill="none"
            stroke="white"
            :stroke-width="stroke"
          />
        </template>

        <g v-if="storyMove">
          <rect
            data-story-move-target
            :x="storyMove.target.x"
            :y="storyMove.target.y"
            :width="storyMove.target.w"
            :height="storyMove.target.h"
            fill="none"
            stroke="#f0b429"
            :stroke-width="stroke * 0.8"
            :stroke-dasharray="`${stroke * 2} ${stroke * 1.5}`"
          />
          <line
            data-story-move
            :x1="storyMove.geo.start.x"
            :y1="storyMove.geo.start.y"
            :x2="storyMove.geo.end.x"
            :y2="storyMove.geo.end.y"
            stroke="#f0b429"
            :stroke-width="stroke * 1.2"
          />
          <polygon :points="points(storyMove.geo.head)" fill="#f0b429" />
        </g>
      </g>

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
