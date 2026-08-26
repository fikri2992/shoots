<script>
import { mapActions, mapState } from 'pinia'

import DisclosureRow from '@/components/DisclosureRow.vue'
import MeasuredStrip from '@/components/MeasuredStrip.vue'
import ShotCanvas from '@/components/ShotCanvas.vue'
import { plain, spanBox } from '@/domain/cells'
import { GUIDE_LABELS, verdict as guideVerdict } from '@/domain/guides'
import { useCoachStore } from '@/stores/coach'
import { useShootsStore } from '@/stores/shoots'

const PICKABLE = ['thirds', 'phi', 'diagonals', 'centre', 'none']
const KIND_LABEL = { move: 'reframe', crop: 'crop', camera: 'viewpoint' }

/** Three lenses describe the same frame, so the descriptions repeat. Keep one. */
function dedupe(lines, limit, grid) {
  const seen = new Set()
  const out = []
  for (const line of lines) {
    const clean = plain(line, grid).trim()
    const key = clean.toLowerCase().replace(/[^a-z ]/g, '').split(/\s+/).slice(0, 5).join(' ')
    if (!clean || seen.has(key)) continue
    seen.add(key)
    out.push(clean)
    if (out.length >= limit) break
  }
  return out
}

/**
 * One frame: what it looks like under the guide its own technique implies,
 * what the panel concluded, and one way in to talk about it. The cell grid the
 * lenses use to point at things never appears here — not as a mesh and not as
 * a coordinate in a sentence.
 */
export default {
  name: 'ShotPage',
  components: { DisclosureRow, ShotCanvas, MeasuredStrip },
  props: { shotId: { type: String, required: true } },
  data() {
    return {
      showRead: true,
      picked: '',
      guides: PICKABLE,
      labels: GUIDE_LABELS,
      keeping: false,
      correctingSource: false,
      confirmSource: false,
    }
  },
  computed: {
    ...mapState(useShootsStore, ['shotById', 'experimentById', 'runs']),
    view() {
      return this.shotById(this.shotId)
    },
    shot() {
      return this.view?.shot
    },
    analysis() {
      return this.view?.analysis
    },
    src() {
      const blobs = this.shot?.blobs || {}
      const key = blobs.sheet ? 'sheet' : 'original'
      return blobs[key] ? `/api/blobs/${blobs[key]}` : ''
    },
    /** The guide the frame's own technique implies, until the user picks one. */
    guide() {
      return this.picked || this.analysis?.composition?.guide || 'thirds'
    },
    subjectPoint() {
      const c = this.analysis?.composition
      if (!c) return null
      if (typeof c.subject_x === 'number' && typeof c.subject_y === 'number') {
        return { x: c.subject_x, y: c.subject_y }
      }
      const box = spanBox(c.subject_cells || [])
      const grid = this.shot?.grid
      if (!box || !grid) return null
      return { x: (box.x + box.w / 2) / grid.cols, y: (box.y + box.h / 2) / grid.rows }
    },
    /** How the frame sits on the guide — the only reason to draw one. */
    fit() {
      if (!this.showRead || !this.analysis) return ''
      if (this.guide === 'fill') {
        const box = spanBox(this.analysis.composition.subject_cells || [])
        const grid = this.shot?.grid
        if (!box || !grid) return ''
        return `the subject fills ${Math.round((box.w * box.h * 100) / (grid.cols * grid.rows))}% of the frame`
      }
      const cellWidth = this.shot?.grid ? 1 / this.shot.grid.cols : 1 / 7
      return guideVerdict(this.guide, this.subjectPoint, { cellWidth })
    },
    tags() {
      return (this.analysis?.techniques || []).slice(0, 3).map((t) => t.technique_id.replace(/_/g, ' '))
    },
    strongestTechnique() {
      const supported = [...(this.analysis?.techniques || [])]
        .filter((technique) => (technique.agreement || 0) >= 2)
        .sort((a, b) => (b.agreement || 0) - (a.agreement || 0) || (b.confidence || 0) - (a.confidence || 0))
      const technique = supported[0]
      if (!technique) return null
      return {
        name: technique.technique_id.replace(/_/g, ' '),
        proof: technique.note || `${technique.agreement} readers independently agreed`,
        agreement: technique.agreement,
        confidence: Math.round((technique.confidence || 0) * 100),
      }
    },
    observations() {
      return dedupe(this.analysis?.observations || [], 6, this.shot?.grid)
    },
    /**
     * What the arithmetic says is wrong. Not the lenses' opinion: every one of
     * these was computed from EXIF or from the grid, so each carries its own
     * number and is shown before the suggestions a model wrote.
     */
    findings() {
      return this.analysis?.findings || []
    },
    /** The critique, with any cell references said the way a person would. */
    critique() {
      return plain(this.analysis?.critique || '', this.shot?.grid)
    },
    moves() {
      const drawn = this.drawnMove
      return (this.analysis?.composition?.moves || [])
        .filter((m) => m.what)
        .map((m) => ({ ...m, kind: m.kind || 'move', shown: this.showRead && m === drawn }))
    },
    primaryMove() {
      return this.moves.find((move) => move.shown) || this.moves[0] || null
    },
    otherMoves() {
      return this.primaryMove ? this.moves.filter((move) => move !== this.primaryMove) : []
    },
    /** The one mark the canvas draws, so the list can say which it is. */
    drawnMove() {
      const composition = this.analysis?.composition
      if (!composition) return null
      const moves = composition.moves || []
      if (composition.suggested_crop_cells?.length) {
        return moves.find((m) => m.kind === 'crop') || null
      }
      return (
        moves.find(
          (m) => (m.kind || 'move') === 'move' && m.from_cells?.length && m.to_cells?.length,
        ) || null
      )
    },
    camera() {
      const e = this.shot?.exif || {}
      const v = this.shot?.video
      const out = []
      if (v) out.push(`${v.width}×${v.height}`, `${v.fps} fps`, `${v.duration_s.toFixed(1)} s`)
      if (e.exposure_time_s) out.push(e.exposure_time_s >= 1 ? `${e.exposure_time_s} s` : `1/${Math.round(1 / e.exposure_time_s)} s`)
      if (e.f_number) out.push(`f/${e.f_number}`)
      if (e.iso) out.push(`ISO ${e.iso}`)
      if (e.focal_length_35mm) out.push(`${e.focal_length_35mm} mm`)
      if (e.model) out.push(e.model)
      if (this.shot?.captured_at) out.push(new Date(this.shot.captured_at).toLocaleDateString())
      return out
    },
    cropUrl() {
      const path = this.shot?.blobs?.crop
      return path && this.analysis?.composition?.suggested_crop_cells?.length ? `/api/blobs/${path}` : ''
    },
    experiment() {
      return this.shot?.experiment_id ? this.experimentById(this.shot.experiment_id) : null
    },
    run() {
      return this.runs.find((item) => item.shot_id === this.shotId) || null
    },
    runSteps() {
      if (!this.run) return []
      return ['ingest', 'analyst', 'cartographer', 'judge', 'scribe', 'scout'].map((stage) => ({
        stage,
        ...this.run.steps[stage],
      }))
    },
    lenses() {
      return Object.keys(this.analysis?.panel || {}).join(', ') || 'three lenses'
    },
    kindLabel() {
      return (kind) => KIND_LABEL[kind] || kind
    },
    reason() {
      return (move) => plain(move.reason || '', this.shot?.grid)
    },
  },
  async created() {
    if (!this.view) await this.fetchShot(this.shotId)
    if (this.$route.hash === '#coach') this.openFor(this.shotId, {})
  },
  methods: {
    ...mapActions(useShootsStore, ['fetchShot', 'setKeeper', 'moveShotToInspiration']),
    ...mapActions(useCoachStore, ['openFor']),
    talk(opener) {
      this.openFor(this.shotId, { opener })
    },
    /**
     * One optional tap. The only thing in Shoots that carries the
     * photographer's own taste rather than the panel's: it separates what they
     * do often from what they actually value, and nothing else can.
     */
    async keep() {
      this.keeping = true
      try {
        await this.setKeeper(this.shotId, !this.shot.kept_at)
      } finally {
        this.keeping = false
      }
    },
    async moveToInspiration() {
      this.correctingSource = true
      try {
        await this.moveShotToInspiration(this.shotId)
        await this.$router.push({ name: 'shots' })
      } finally {
        this.correctingSource = false
      }
    },
  },
}
</script>

<template>
  <div class="page-shell pb-24 pt-6 md:pb-12 md:pt-8">
    <p v-if="!shot" class="pt-12 t-meta">Loading the Shot…</p>

    <template v-else>
      <header class="mb-5 flex items-center justify-between">
        <RouterLink :to="{ name: 'shots' }" class="t-meta hover:text-paper">← All Shots</RouterLink>
        <button
          type="button"
          class="rounded-xl border px-3 py-2 text-[12px] font-medium transition"
          :class="shot.kept_at ? 'border-accent/60 text-accent' : 'border-edge text-muted hover:text-paper'"
          :disabled="keeping"
          @click="keep"
        >
          {{ shot.kept_at ? 'Keeper · yours' : 'Mark as Keeper' }}
        </button>
      </header>

      <div class="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)] lg:items-start lg:gap-8">
        <div class="lg:sticky lg:top-6">
          <div class="relative overflow-hidden rounded-2xl border border-edge bg-panel">
          <ShotCanvas
            v-if="src && shot.grid"
            :src="src"
            :grid="shot.grid"
            :composition="analysis?.composition"
            :guide="guide"
            :show-findings="showRead"
          />
          <button
            type="button"
            class="absolute bottom-3 right-3 rounded-xl border border-white/10 bg-black/72 px-3 py-1.5 text-[11px]"
            :class="showRead ? 'text-paper' : 'text-muted'"
            @click="showRead = !showRead"
          >
            {{ showRead ? 'Hide read' : 'Show read' }}
          </button>
        </div>

          <div class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-edge bg-panel px-3 py-2.5">
            <span class="eyebrow mr-1">Guide</span>
          <button
            v-for="g in guides"
            :key="g"
            type="button"
            class="t-meta"
              :class="guide === g ? 'text-accent' : 'text-muted hover:text-paper'"
            @click="picked = g"
          >
            {{ labels[g] }}
          </button>
            <span v-if="fit" class="ml-auto t-meta text-neutral-300">{{ fit }}</span>
          </div>
        </div>

        <div>
          <template v-if="analysis">
            <p class="eyebrow">Shot read</p>
            <p class="mt-2 t-meta">{{ camera.slice(-2).join(' · ') || shot.filename }}</p>

            <section class="surface mt-5 p-5 sm:p-6">
              <p class="eyebrow">What held</p>
              <template v-if="strongestTechnique">
                <h1 class="mt-3 text-[28px] leading-8 font-semibold tracking-[-0.035em] text-paper capitalize">
                  {{ strongestTechnique.name }}
                </h1>
                <p class="mt-3 t-body text-neutral-300">{{ strongestTechnique.proof }}</p>
                <p class="mt-3 t-meta">
                  {{ strongestTechnique.agreement }} readers · {{ strongestTechnique.confidence }}% confidence
                </p>
              </template>
              <p v-else class="mt-3 t-body text-neutral-300">
                No Technique had enough independent agreement to lead with one.
              </p>
            </section>

            <MeasuredStrip class="mt-4" :tone="shot.tone" :motion="shot.motion" />

            <section v-if="critique" class="mt-5 border-l border-edge pl-4">
              <p class="eyebrow">Panel read · model opinion</p>
              <p class="mt-2 t-body text-neutral-200">{{ critique }}</p>
            </section>

            <section v-if="primaryMove" class="surface-active mt-6 p-5">
              <div class="flex items-center justify-between gap-3">
                <p class="eyebrow text-accent">One move to try</p>
                <span class="t-meta">{{ kindLabel(primaryMove.kind) }}</span>
              </div>
              <p class="mt-3 text-[18px] leading-6 font-medium text-paper">{{ primaryMove.what }}</p>
              <p v-if="reason(primaryMove)" class="mt-2 t-body">{{ reason(primaryMove) }}</p>
            </section>

            <section v-if="findings.length" class="mt-6 rounded-2xl border border-bad/45 bg-bad/8 p-5">
              <p class="eyebrow text-bad">Finding{{ findings.length === 1 ? '' : 's' }}</p>
              <ul class="mt-3 space-y-4">
                <li v-for="f in findings" :key="f.finding_id">
                  <p class="t-body text-paper">{{ f.what }}</p>
                  <p class="mt-1 t-num text-[11px] leading-4 text-muted">{{ f.why }}</p>
                </li>
              </ul>
            </section>

            <button type="button" class="btn mt-6 w-full" @click="talk('Talk me through this Shot.')">
              Ask about this Shot
            </button>

          <div class="mt-8">
              <DisclosureRow v-if="otherMoves.length" label="Other possible moves" :count="otherMoves.length">
                <ul class="space-y-4">
                  <li v-for="(move, i) in otherMoves" :key="i">
                    <p class="t-body text-paper">{{ move.what }}</p>
                    <p class="mt-1 t-meta">{{ kindLabel(move.kind) }} · {{ reason(move) }}</p>
                  </li>
                </ul>
              </DisclosureRow>

            <DisclosureRow v-if="observations.length" label="What it saw" :count="observations.length">
              <ul class="space-y-2">
                <li v-for="(o, i) in observations" :key="i" class="flex gap-3 t-body text-neutral-300">
                  <span class="mt-2 h-1 w-1 shrink-0 rounded-full bg-neutral-700" />
                  <span>{{ o }}</span>
                </li>
              </ul>
            </DisclosureRow>

            <DisclosureRow label="Techniques it agreed on" :count="analysis.techniques.length">
              <ul class="space-y-3">
                <li v-for="t in analysis.techniques" :key="t.technique_id">
                  <div class="flex items-center gap-2">
                      <span class="t-body text-paper">{{ t.technique_id.replace(/_/g, ' ') }}</span>
                    <span
                      v-if="t.agreement"
                        class="t-num text-[10px] tracking-widest text-muted"
                      :title="`seen by ${(t.lenses || []).join(', ')}`"
                    >
                      {{ '●'.repeat(t.agreement) + '○'.repeat(Math.max(0, 3 - t.agreement)) }}
                    </span>
                      <span class="ml-auto t-num text-[11px] text-muted">{{ Math.round(t.confidence * 100) }}%</span>
                  </div>
                  <p class="t-meta">{{ t.note }}</p>
                </li>
                <li v-if="!analysis.techniques.length" class="t-meta">Nothing reached agreement on this Shot.</li>
              </ul>
            </DisclosureRow>

            <DisclosureRow
              v-if="cropUrl"
              label="A crop it tested"
            >
              <img :src="cropUrl" alt="tested crop" class="max-h-64 rounded-xl object-contain" />
              <p class="mt-2 t-body text-neutral-400">
                {{ analysis.composition.crop_reason }}
                  <span class="mt-1 block t-meta">Rendered and compared against the original; the preference is the crop rater's model opinion.</span>
              </p>
            </DisclosureRow>

            <DisclosureRow label="Camera" :count="camera.length ? '' : 'none'">
              <p class="t-num text-[13px] text-neutral-400">{{ camera.join(' · ') || 'No EXIF in this file.' }}</p>
            </DisclosureRow>

            <DisclosureRow v-if="run" label="Autonomous Run" :count="run.status">
              <ul class="space-y-3">
                <li v-for="step in runSteps" :key="step.stage" class="flex gap-3">
                  <span class="w-24 shrink-0 t-meta capitalize">{{ step.stage }}</span>
                  <span class="t-body text-neutral-300">{{ step.outcome || step.state }}</span>
                </li>
              </ul>
            </DisclosureRow>
          </div>

            <div class="mt-8 space-y-2 border-t border-edge pt-4 t-meta">
            <a v-if="shot.drive_review_url" :href="shot.drive_review_url" target="_blank" rel="noopener" class="block hover:text-neutral-200">
              The reviewed copy is in your Drive ↗
            </a>
            <RouterLink v-if="experiment" :to="{ name: 'now' }" class="block hover:text-neutral-200">
              Sent for “{{ experiment.title }}” ▸
            </RouterLink>
            <p>{{ shot.filename }}</p>
            <button type="button" class="block text-left hover:text-neutral-200" @click="confirmSource = true">
              This is Inspiration, not my Shot
            </button>
          </div>

            <section v-if="confirmSource" class="mt-4 rounded-xl border border-accent/35 bg-accent/5 p-4">
              <p class="t-body text-paper">Move this to Inspiration?</p>
              <p class="mt-1 t-meta">It stays available as a reference but stops changing your Technique Map, Tendencies, Keepers, and Journey.</p>
              <div class="mt-4 flex gap-2">
                <button type="button" class="btn-quiet px-4" :disabled="correctingSource" @click="moveToInspiration">
                  {{ correctingSource ? 'Moving…' : 'Move' }}
                </button>
                <button type="button" class="btn-quiet px-4" @click="confirmSource = false">Keep as Shot</button>
              </div>
            </section>
          </template>

          <p v-else-if="shot.error" class="rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 t-body text-bad">
            {{ shot.error }}
          </p>
          <div v-else class="surface p-6">
            <p class="eyebrow text-accent">Reading</p>
            <p class="mt-3 t-body">The Analyst has not finished this Shot yet.</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
