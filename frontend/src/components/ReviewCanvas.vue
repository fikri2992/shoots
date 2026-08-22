<script>
import { severityRank } from '@/domain/defects'

const SEVERITY_HEX = { blocker: '#E24B4A', warning: '#EF9F27', nitpick: '#378ADD' }
const CLOSED_STATES = ['verified_resolved', 'dismissed', 'override_approved']
const MIN_ZOOM = 1
const MAX_ZOOM = 8
//: Freehand paths keep at most this many points; further moves thin themselves out.
const MAX_PATH_POINTS = 400

/**
 * The review canvas: zoom, pan, and frame.io-style drawing.
 *
 * The image is contain-fit inside the viewport — never taller than the screen —
 * and everything on it lives in natural pixel space: defect regions, human
 * shapes, and the shape being drawn. One transform maps it all to the screen.
 *
 * Idle state shows only numbered pins; a marker's full geometry draws when its
 * pin, card, or selection makes it active. Keeps red rings off faces.
 */
export default {
  name: 'ReviewCanvas',
  props: {
    src: { type: String, required: true },
    width: { type: Number, required: true },
    height: { type: Number, required: true },
    defects: { type: Array, default: () => [] },
    threads: { type: Array, default: () => [] }, // [{ thread, comments }]
    pendingShapes: { type: Array, default: () => [] },
    tool: { type: String, default: 'select' },
    color: { type: String, default: '#E24B4A' },
    selectedId: { type: String, default: '' },
    hoveredId: { type: String, default: '' },
  },
  emits: ['select', 'shape'],
  data() {
    return {
      zoom: 1,
      tx: 0,
      ty: 0,
      fit: 1,
      dragging: false,
      moved: false,
      origin: null,
      draft: null, // shape-in-progress, natural coords
      hoverPin: '', // badge under the cursor
      observer: null,
    }
  },
  computed: {
    pins() {
      return [...this.defects]
        .sort((a, b) => severityRank(a.severity) - severityRank(b.severity))
        .map((defect) => ({
          id: defect.id,
          kind: 'defect',
          pin: defect.pin,
          box: this.defectBox(defect),
          cx: defect.circle.cx,
          cy: defect.circle.cy,
          color: SEVERITY_HEX[defect.severity] || '#888',
          closed: CLOSED_STATES.includes(defect.status),
          payload: defect,
        }))
    },
    threadPins() {
      return this.threads.map(({ thread }) => {
        const box = this.bboxOf(thread.shapes)
        return {
          id: thread.id,
          kind: 'thread',
          pin: thread.pin,
          box,
          cx: (box.left + box.right) / 2,
          cy: (box.top + box.bottom) / 2,
          shapes: thread.shapes,
          color: thread.shapes[0]?.color || '#378ADD',
          closed: thread.resolved,
          payload: thread,
        }
      })
    },
    stageStyle() {
      return {
        width: `${this.width * this.fit}px`,
        height: `${this.height * this.fit}px`,
        transform: `translate(${this.tx}px, ${this.ty}px) scale(${this.zoom})`,
        transformOrigin: 'top left',
        transition: this.dragging || this.draft ? 'none' : 'transform 140ms ease-out',
      }
    },
    zoomLabel() {
      return `${Math.round(this.zoom * 100)}%`
    },
    drawing() {
      return this.tool !== 'select'
    },
    cursor() {
      if (this.drawing) return 'cursor-crosshair'
      if (this.zoom > 1) return this.dragging ? 'cursor-grabbing' : 'cursor-grab'
      return 'cursor-zoom-in'
    },
    strokeWidth() {
      // A constant 2px on screen, whatever the image size or zoom.
      return 2 / Math.max(this.fit * this.zoom, 0.0001)
    },
    cornerRadius() {
      return 6 / Math.max(this.fit * this.zoom, 0.0001)
    },
  },
  watch: {
    src() {
      this.measure()
    },
  },
  mounted() {
    this.measure()
    this.observer = new ResizeObserver(this.measure)
    this.observer.observe(this.$refs.viewport)
  },
  beforeUnmount() {
    this.observer?.disconnect()
  },
  methods: {
    isActive(id) {
      return id === this.selectedId || id === this.hoveredId || id === this.hoverPin
    },

    measure() {
      const viewport = this.$refs.viewport
      if (!viewport || !this.width || !this.height) return
      const vw = viewport.clientWidth
      const vh = viewport.clientHeight
      if (!vw || !vh) return
      this.fit = Math.min(vw / this.width, vh / this.height)
      this.resetView()
    },

    /** A defect's tight extent; old records without one fall back to the circle. */
    defectBox(defect) {
      if (defect.region) {
        const { left, top, width, height } = defect.region
        return { left, top, right: left + width, bottom: top + height }
      }
      const { cx, cy, radius } = defect.circle
      const half = radius * 0.7071
      return { left: cx - half, top: cy - half, right: cx + half, bottom: cy + half }
    },

    bboxOf(shapes) {
      let left = Infinity
      let top = Infinity
      let right = -Infinity
      let bottom = -Infinity
      for (const shape of shapes) {
        const points = shape.points
        if (shape.kind === 'circle') {
          left = Math.min(left, points[0] - points[2])
          top = Math.min(top, points[1] - points[2])
          right = Math.max(right, points[0] + points[2])
          bottom = Math.max(bottom, points[1] + points[2])
        } else if (shape.kind === 'rect') {
          left = Math.min(left, points[0])
          top = Math.min(top, points[1])
          right = Math.max(right, points[0] + points[2])
          bottom = Math.max(bottom, points[1] + points[3])
        } else {
          for (let i = 0; i < points.length; i += 2) {
            left = Math.min(left, points[i])
            top = Math.min(top, points[i + 1])
            right = Math.max(right, points[i])
            bottom = Math.max(bottom, points[i + 1])
          }
        }
      }
      return { left, top, right, bottom }
    },

    toNatural(event) {
      const box = this.$refs.viewport.getBoundingClientRect()
      const x = (event.clientX - box.left - this.tx) / (this.fit * this.zoom)
      const y = (event.clientY - box.top - this.ty) / (this.fit * this.zoom)
      return {
        x: Math.max(0, Math.min(this.width, x)),
        y: Math.max(0, Math.min(this.height, y)),
      }
    },

    // --- zoom and pan ---

    clampZoom(value) {
      return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value))
    },

    zoomAt(next, px, py) {
      const zoom = this.clampZoom(next)
      const ratio = zoom / this.zoom
      this.tx = px - (px - this.tx) * ratio
      this.ty = py - (py - this.ty) * ratio
      this.zoom = zoom
      this.constrain()
    },

    onWheel(event) {
      event.preventDefault()
      const box = this.$refs.viewport.getBoundingClientRect()
      const factor = event.deltaY < 0 ? 1.2 : 1 / 1.2
      this.zoomAt(this.zoom * factor, event.clientX - box.left, event.clientY - box.top)
    },

    zoomBy(factor) {
      const box = this.$refs.viewport.getBoundingClientRect()
      this.zoomAt(this.zoom * factor, box.width / 2, box.height / 2)
    },

    resetView() {
      this.zoom = 1
      this.constrain()
    },

    /** Keep the image on screen; centre any axis it doesn't fill. */
    constrain() {
      const viewport = this.$refs.viewport
      if (!viewport) return
      const vw = viewport.clientWidth
      const vh = viewport.clientHeight
      const sw = this.width * this.fit * this.zoom
      const sh = this.height * this.fit * this.zoom
      this.tx = sw <= vw ? (vw - sw) / 2 : Math.min(0, Math.max(vw - sw, this.tx))
      this.ty = sh <= vh ? (vh - sh) / 2 : Math.min(0, Math.max(vh - sh, this.ty))
    },

    centerOn(point, minZoom = 2.5) {
      const viewport = this.$refs.viewport
      if (!viewport) return
      this.zoom = this.clampZoom(Math.max(this.zoom, minZoom))
      this.tx = viewport.clientWidth / 2 - point.cx * this.fit * this.zoom
      this.ty = viewport.clientHeight / 2 - point.cy * this.fit * this.zoom
      this.constrain()
    },

    // --- pointer flow: draw when a tool is armed, otherwise pan ---

    onPointerDown(event) {
      if (this.drawing) {
        const point = this.toNatural(event)
        this.draft =
          this.tool === 'path'
            ? { kind: 'path', points: [point.x, point.y], color: this.color }
            : { kind: this.tool, start: point, end: point, color: this.color }
        event.currentTarget.setPointerCapture?.(event.pointerId)
        return
      }
      if (this.zoom === 1) return
      this.dragging = true
      this.moved = false
      this.origin = { x: event.clientX - this.tx, y: event.clientY - this.ty }
      event.currentTarget.setPointerCapture?.(event.pointerId)
    },

    onPointerMove(event) {
      if (this.draft) {
        const point = this.toNatural(event)
        if (this.draft.kind === 'path') {
          const pts = this.draft.points
          if (pts.length >= MAX_PATH_POINTS * 2) {
            this.draft.points = pts.filter((_, i) => i < 2 || i % 4 < 2)
          }
          this.draft.points.push(point.x, point.y)
        } else {
          this.draft.end = point
        }
        return
      }
      if (!this.dragging) return
      this.moved = true
      this.tx = event.clientX - this.origin.x
      this.ty = event.clientY - this.origin.y
      this.constrain()
    },

    onPointerUp() {
      if (this.draft) {
        const shape = this.finishDraft(this.draft)
        this.draft = null
        if (shape) this.$emit('shape', shape)
        return
      }
      this.dragging = false
    },

    /** Convert a draft into the wire Shape format; drop accidental dots. */
    finishDraft(draft) {
      const round = (value) => Math.round(value * 10) / 10
      if (draft.kind === 'path') {
        if (draft.points.length < 4) return null
        return { kind: 'path', points: draft.points.map(round), color: draft.color }
      }
      const { start, end } = draft
      if (draft.kind === 'circle') {
        // The drag is a bounding area, like every design tool — not centre-out.
        const r = Math.max(Math.abs(end.x - start.x), Math.abs(end.y - start.y)) / 2
        if (r < 4) return null
        const cx = (start.x + end.x) / 2
        const cy = (start.y + end.y) / 2
        return { kind: 'circle', points: [round(cx), round(cy), round(r)], color: draft.color }
      }
      if (draft.kind === 'rect') {
        const x = Math.min(start.x, end.x)
        const y = Math.min(start.y, end.y)
        const w = Math.abs(end.x - start.x)
        const h = Math.abs(end.y - start.y)
        if (w < 4 || h < 4) return null
        return { kind: 'rect', points: [round(x), round(y), round(w), round(h)], color: draft.color }
      }
      if (Math.hypot(end.x - start.x, end.y - start.y) < 4) return null
      return {
        kind: 'arrow',
        points: [round(start.x), round(start.y), round(end.x), round(end.y)],
        color: draft.color,
      }
    },

    draftAsShape() {
      if (!this.draft) return null
      if (this.draft.kind === 'path') return this.draft
      const { start, end, kind, color } = this.draft
      if (kind === 'circle') {
        return {
          kind,
          points: [
            (start.x + end.x) / 2,
            (start.y + end.y) / 2,
            Math.max(Math.abs(end.x - start.x), Math.abs(end.y - start.y)) / 2,
          ],
          color,
        }
      }
      if (kind === 'rect') {
        return {
          kind,
          points: [
            Math.min(start.x, end.x),
            Math.min(start.y, end.y),
            Math.abs(end.x - start.x),
            Math.abs(end.y - start.y),
          ],
          color,
        }
      }
      return { kind, points: [start.x, start.y, end.x, end.y], color }
    },

    arrowHead(points) {
      const [x1, y1, x2, y2] = points
      const angle = Math.atan2(y2 - y1, x2 - x1)
      const size = this.strokeWidth * 4
      const left = angle + Math.PI * 0.85
      const right = angle - Math.PI * 0.85
      return `${x2},${y2} ${x2 + size * Math.cos(left)},${y2 + size * Math.sin(left)} ${
        x2 + size * Math.cos(right)
      },${y2 + size * Math.sin(right)}`
    },

    pathData(points) {
      let d = `M ${points[0]} ${points[1]}`
      for (let i = 2; i < points.length; i += 2) d += ` L ${points[i]} ${points[i + 1]}`
      return d
    },

    onDoubleClick(event) {
      if (this.drawing) return
      const box = this.$refs.viewport.getBoundingClientRect()
      if (this.zoom > 1) this.resetView()
      else this.zoomAt(3, event.clientX - box.left, event.clientY - box.top)
    },

    onBadgeClick(item) {
      if (this.moved || this.drawing) return
      this.$emit('select', item)
      this.centerOn(item)
    },
  },
}
</script>

<template>
  <div
    ref="viewport"
    class="absolute inset-0 overflow-hidden bg-[#0e0f11] select-none touch-none"
    :class="cursor"
    @wheel="onWheel"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
    @dblclick="onDoubleClick"
  >
    <div class="absolute left-0 top-0" :style="stageStyle">
      <img :src="src" alt="Asset under review" class="block size-full" draggable="false" />

      <svg
        class="pointer-events-none absolute inset-0 size-full"
        :viewBox="`0 0 ${width} ${height}`"
        preserveAspectRatio="none"
      >
        <!-- Agent defects: a tight rounded box, drawn only for the active pin -->
        <template v-for="pin in pins" :key="pin.id">
          <rect
            v-if="isActive(pin.id)"
            :x="pin.box.left"
            :y="pin.box.top"
            :width="pin.box.right - pin.box.left"
            :height="pin.box.bottom - pin.box.top"
            :rx="cornerRadius"
            :fill="pin.color"
            fill-opacity="0.08"
            :stroke="pin.color"
            :stroke-width="selectedId === pin.id ? strokeWidth * 1.5 : strokeWidth"
            :opacity="pin.closed ? 0.5 : 1"
          />
        </template>

        <!-- Human threads: the drawn shapes, only for the active pin -->
        <g
          v-for="item in threadPins"
          :key="item.id"
          :opacity="item.closed ? 0.5 : 1"
        >
          <template v-if="isActive(item.id)">
            <template v-for="(shape, index) in item.shapes" :key="index">
              <circle
                v-if="shape.kind === 'circle'"
                :cx="shape.points[0]"
                :cy="shape.points[1]"
                :r="shape.points[2]"
                fill="none"
                :stroke="shape.color"
                :stroke-width="selectedId === item.id ? strokeWidth * 1.5 : strokeWidth"
              />
              <rect
                v-else-if="shape.kind === 'rect'"
                :x="shape.points[0]"
                :y="shape.points[1]"
                :width="shape.points[2]"
                :height="shape.points[3]"
                :rx="cornerRadius"
                fill="none"
                :stroke="shape.color"
                :stroke-width="selectedId === item.id ? strokeWidth * 1.5 : strokeWidth"
              />
              <g v-else-if="shape.kind === 'arrow'">
                <line
                  :x1="shape.points[0]"
                  :y1="shape.points[1]"
                  :x2="shape.points[2]"
                  :y2="shape.points[3]"
                  :stroke="shape.color"
                  :stroke-width="strokeWidth"
                />
                <polygon :points="arrowHead(shape.points)" :fill="shape.color" />
              </g>
              <path
                v-else
                :d="pathData(shape.points)"
                fill="none"
                :stroke="shape.color"
                :stroke-width="strokeWidth"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </template>
          </template>
        </g>

        <!-- Pending shapes for the comment being composed -->
        <g v-for="(shape, index) in pendingShapes" :key="`pending-${index}`">
          <circle
            v-if="shape.kind === 'circle'"
            :cx="shape.points[0]" :cy="shape.points[1]" :r="shape.points[2]"
            fill="none" :stroke="shape.color" :stroke-width="strokeWidth" stroke-dasharray="6 4"
          />
          <rect
            v-else-if="shape.kind === 'rect'"
            :x="shape.points[0]" :y="shape.points[1]"
            :width="shape.points[2]" :height="shape.points[3]"
            fill="none" :stroke="shape.color" :stroke-width="strokeWidth" stroke-dasharray="6 4"
          />
          <g v-else-if="shape.kind === 'arrow'">
            <line
              :x1="shape.points[0]" :y1="shape.points[1]"
              :x2="shape.points[2]" :y2="shape.points[3]"
              :stroke="shape.color" :stroke-width="strokeWidth" stroke-dasharray="6 4"
            />
            <polygon :points="arrowHead(shape.points)" :fill="shape.color" />
          </g>
          <path
            v-else
            :d="pathData(shape.points)"
            fill="none" :stroke="shape.color" :stroke-width="strokeWidth"
            stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="6 4"
          />
        </g>

        <!-- Live draft while the pointer is down -->
        <template v-if="draftAsShape()">
          <circle
            v-if="draftAsShape().kind === 'circle'"
            :cx="draftAsShape().points[0]" :cy="draftAsShape().points[1]" :r="draftAsShape().points[2]"
            fill="none" :stroke="color" :stroke-width="strokeWidth"
          />
          <rect
            v-else-if="draftAsShape().kind === 'rect'"
            :x="draftAsShape().points[0]" :y="draftAsShape().points[1]"
            :width="draftAsShape().points[2]" :height="draftAsShape().points[3]"
            fill="none" :stroke="color" :stroke-width="strokeWidth"
          />
          <line
            v-else-if="draftAsShape().kind === 'arrow'"
            :x1="draftAsShape().points[0]" :y1="draftAsShape().points[1]"
            :x2="draftAsShape().points[2]" :y2="draftAsShape().points[3]"
            :stroke="color" :stroke-width="strokeWidth"
          />
          <path
            v-else
            :d="pathData(draftAsShape().points)"
            fill="none" :stroke="color" :stroke-width="strokeWidth"
            stroke-linecap="round" stroke-linejoin="round"
          />
        </template>
      </svg>

      <!-- Numbered pins on the marker's top-left corner, counter-scaled -->
      <button
        v-for="item in [...pins, ...threadPins]"
        :key="`badge-${item.id}`"
        type="button"
        class="absolute flex size-5 items-center justify-center rounded-full text-[10px] font-bold text-black shadow-md ring-1 transition-transform hover:scale-110"
        :class="selectedId === item.id ? 'ring-2 ring-white' : 'ring-black/50'"
        :style="{
          left: `${(item.box.left / width) * 100}%`,
          top: `${(item.box.top / height) * 100}%`,
          transform: `translate(-50%, -50%) scale(${1 / zoom})`,
          background: item.color,
          opacity: item.closed ? 0.45 : 1,
        }"
        :aria-label="`Pin ${item.pin}`"
        @click.stop="onBadgeClick(item)"
        @pointerenter="hoverPin = item.id"
        @pointerleave="hoverPin = ''"
      >
        {{ item.pin }}
      </button>
    </div>

    <!-- Zoom controls -->
    <div
      class="absolute bottom-3 right-3 flex items-center gap-1 rounded-lg border border-neutral-700 bg-neutral-900/90 p-1 backdrop-blur"
    >
      <button type="button" class="rounded px-2 py-1 text-sm hover:bg-neutral-800" aria-label="Zoom out" @click="zoomBy(1 / 1.4)">−</button>
      <span class="min-w-12 text-center font-mono text-xs text-neutral-400">{{ zoomLabel }}</span>
      <button type="button" class="rounded px-2 py-1 text-sm hover:bg-neutral-800" aria-label="Zoom in" @click="zoomBy(1.4)">+</button>
      <button
        v-if="zoom !== 1"
        type="button"
        class="rounded px-2 py-1 text-xs text-neutral-400 hover:bg-neutral-800 hover:text-neutral-100"
        @click="resetView"
      >
        Fit
      </button>
    </div>
  </div>
</template>
