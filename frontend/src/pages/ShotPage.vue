<script>
import { mapActions, mapState } from 'pinia'

import CompanionReceipt from '@/components/CompanionReceipt.vue'
import CropComparison from '@/components/CropComparison.vue'
import DisclosureRow from '@/components/DisclosureRow.vue'
import MeasuredStrip from '@/components/MeasuredStrip.vue'
import ShotCanvas from '@/components/ShotCanvas.vue'
import ShotDeconstruction from '@/components/ShotDeconstruction.vue'
import { plain, spanBox } from '@/domain/cells'
import { humanizeLegacyText, metricLabel, repeatabilitySummary, techniqueHistory } from '@/domain/copy'
import { GUIDE_LABELS, verdict as guideVerdict } from '@/domain/guides'
import { artifactIsRenderable, buildVisualStory } from '@/domain/visualStory'
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
  components: { CompanionReceipt, CropComparison, DisclosureRow, ShotCanvas, ShotDeconstruction, MeasuredStrip },
  props: { shotId: { type: String, required: true } },
  data() {
    return {
      showRead: true,
      picked: '',
      storyIndex: 0,
      guides: PICKABLE,
      labels: GUIDE_LABELS,
      keeping: false,
      correctingSource: false,
      confirmSource: false,
      loadingShot: false,
      loadFailed: false,
    }
  },
  computed: {
    ...mapState(useShootsStore, ['shotById', 'experimentById', 'runs', 'mobile', 'busy', 'me']),
    isSampleRecord() {
      return this.me?.record_mode === 'sample'
    },
    view() {
      return this.shotById(this.shotId)
    },
    shot() {
      return this.view?.shot
    },
    analysis() {
      return this.view?.analysis
    },
    teaching() {
      return this.view?.teaching
    },
    visualStory() {
      return buildVisualStory(this.view)
    },
    currentStory() {
      return this.visualStory[this.storyIndex] || this.visualStory[0] || null
    },
    currentTechniqueId() {
      return this.currentStory?.mark?.technique_id || ''
    },
    currentTechniqueContext() {
      if (!this.currentTechniqueId) return null
      return this.view?.technique_context?.[this.currentTechniqueId] || null
    },
    currentExperimentDirection() {
      if (!this.currentTechniqueId) return null
      return (this.mobile?.experiment_directions || []).find(
        (direction) =>
          direction.source_shot_id === this.shotId &&
          direction.technique_id === this.currentTechniqueId,
      ) || null
    },
    techniqueHistoryLine() {
      return techniqueHistory(this.currentTechniqueContext)
    },
    repeatabilityLine() {
      return repeatabilitySummary(this.currentTechniqueContext)
    },
    keeperReceiptItems() {
      if (!this.shot?.kept_at) return []
      let next = 'Shoots will remember that this Shot matters to you.'
      if (this.currentExperimentDirection?.state === 'saved') {
        next = 'Your question is saved for another day. Nothing has started.'
      } else if (this.currentExperimentDirection?.state === 'started') {
        next = 'Your saved question is now an Experiment. Open Now to see what you chose to repeat.'
      } else if (this.currentTechniqueContext?.positive_keeper_shots) {
        next = 'If this is a choice you want to repeat, save the question for later.'
      }
      return [
        {
          label: 'Shoots handled',
          text: 'The visual read stays exactly as it was.',
          state: 'done',
        },
        {
          label: 'You decided',
          text: `You marked ${this.shot.filename} as a Keeper.`,
          state: 'done',
        },
        {
          label: 'The result',
          text: 'Shoots can now use this mark when it looks for the choices you value.',
          state: 'done',
        },
        { label: 'Next', text: next, state: 'current' },
      ]
    },
    currentArtifactPath() {
      const artifact = this.currentStory?.mark?.visual_artifact
      return artifact?.status === 'rendered' ? artifact.blob_path || '' : ''
    },
    currentArtifactRendered() {
      return artifactIsRenderable(this.currentStory?.mark?.visual_artifact)
    },
    canvasMark() {
      return this.showRead && !this.picked && !this.currentArtifactRendered
        ? this.currentStory?.mark || null
        : null
    },
    src() {
      const blobs = this.shot?.blobs || {}
      const key = blobs.sheet ? 'sheet' : 'original'
      return blobs[key] ? `/api/blobs/${blobs[key]}` : ''
    },
    canvasLayer() {
      if (!this.showRead) return 'clean'
      if (this.picked) return 'guide'
      if (this.currentArtifactRendered) return 'clean'
      return this.currentStory?.layer || 'all'
    },
    canvasSrc() {
      const marked = this.shot?.blobs?.finding_marked
      if (this.showRead && !this.picked && this.currentArtifactPath) {
        return `/api/blobs/${this.currentArtifactPath}`
      }
      return this.canvasLayer === 'finding' && marked ? `/api/blobs/${marked}` : this.src
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
        outcome: humanizeLegacyText(this.run.steps[stage]?.outcome),
      }))
    },
    shootContext() {
      if (this.$route.query.from !== 'shoot') return null
      const record = this.mobile?.latest_shoot_record
      if (!record) return null
      if (
        record.shoot_id !== this.$route.query.shootId ||
        String(record.revision) !== String(this.$route.query.revision)
      ) {
        return null
      }
      const index = record.shot_ids.indexOf(this.shotId)
      return index >= 0 ? { record, index } : null
    },
    fromNowQuestion() {
      return this.$route.query.from === 'now'
    },
    backTarget() {
      if (this.fromNowQuestion) return { name: 'now' }
      if (!this.shootContext) return { name: 'shots' }
      return {
        name: 'shoot-record',
        params: {
          shootId: this.shootContext.record.shoot_id,
          revision: this.shootContext.record.revision,
        },
      }
    },
    backLabel() {
      if (this.fromNowQuestion) return 'Back to the question'
      return this.shootContext ? 'Back to Shoot Record' : 'Back to all Shots'
    },
    shotContextLabel() {
      if (this.fromNowQuestion) return 'Evidence for your current question'
      if (!this.shootContext) return 'Shot detail'
      return `Shot ${this.shootContext.index + 1} of ${this.shootContext.record.shot_ids.length} · Shoot ready`
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
    await this.loadShot()
  },
  watch: {
    async shotId() {
      this.storyIndex = 0
      this.picked = ''
      this.showRead = true
      await this.loadShot()
    },
    visualStory(story) {
      this.storyIndex = Math.min(this.storyIndex, Math.max(0, story.length - 1))
    },
  },
  methods: {
    ...mapActions(useShootsStore, [
      'fetchShot',
      'setKeeper',
      'moveShotToInspiration',
      'chooseExperimentDirection',
    ]),
    async loadShot() {
      this.loadingShot = true
      this.loadFailed = false
      try {
        if (!this.view) {
          const loaded = await this.fetchShot(this.shotId)
          this.loadFailed = !loaded
        }
      } finally {
        this.loadingShot = false
      }
    },
    nextStory() {
      if (this.storyIndex < this.visualStory.length - 1) this.storyIndex += 1
      this.picked = ''
      this.showRead = true
    },
    previousStory() {
      if (this.storyIndex > 0) this.storyIndex -= 1
      this.picked = ''
      this.showRead = true
    },
    selectGuide(guide) {
      this.picked = guide
      this.showRead = true
    },
    artifactMetrics(artifact) {
      return Object.entries(artifact?.metrics || {})
        .slice(0, 3)
        .map(([key, value]) => `${metricLabel(key)} ${String(value).replace(/^"|"$/g, '')}`)
        .join(' · ')
    },
    async chooseDirection(save) {
      if (!this.currentTechniqueId) return
      await this.chooseExperimentDirection(this.shotId, this.currentTechniqueId, save)
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
        const moved = await this.moveShotToInspiration(this.shotId)
        if (moved) await this.$router.push({ name: 'shots' })
      } finally {
        this.correctingSource = false
      }
    },
  },
}
</script>

<template>
  <div class="page-shell pb-24 pt-6 md:pb-12 md:pt-8">
    <header class="mb-5 flex min-h-16 items-center gap-3 border-b border-edge">
      <RouterLink :to="backTarget" class="tap-target text-paper" :aria-label="backLabel">
        <svg aria-hidden="true" viewBox="0 0 24 24" class="h-6 w-6 fill-none stroke-current stroke-2">
          <path d="m15 18-6-6 6-6" />
        </svg>
      </RouterLink>
      <div v-if="shot" class="min-w-0 flex-1">
        <p class="truncate text-[15px] font-medium text-paper">{{ shot.filename }}</p>
        <p class="mt-0.5 text-[11px] text-muted">{{ shotContextLabel }}</p>
      </div>
      <button
        v-if="shot && !isSampleRecord"
        type="button"
        class="flex min-h-11 items-center gap-2 rounded-full border px-3 text-[12px] transition"
        :class="shot.kept_at ? 'border-accent/60 bg-accent/10 text-accent' : 'border-edge-strong text-muted hover:text-paper'"
        :disabled="keeping"
        :aria-pressed="Boolean(shot.kept_at)"
        @click="keep"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 stroke-current stroke-2" :class="shot.kept_at ? 'fill-current' : 'fill-none'">
          <path d="M6 3h12v18l-6-4-6 4z" />
        </svg>
        {{ shot.kept_at ? 'Keeper' : 'Keep' }}
      </button>
      <span v-else-if="shot" class="rounded-full border border-edge px-3 py-2 text-[11px] text-muted">
        Sample · read only
      </span>
    </header>

    <p v-if="loadingShot" class="surface p-6 t-body" aria-live="polite">Loading the Shot…</p>

    <section v-else-if="loadFailed" class="surface p-6 sm:p-8" role="alert">
      <p class="eyebrow text-bad">Shot unavailable</p>
      <h1 class="mt-3 t-title">This Shot could not be opened.</h1>
      <p class="mt-3 t-body">It may have been removed, reclassified as Inspiration, or failed to load.</p>
      <RouterLink :to="backTarget" class="btn-quiet mt-5">{{ backLabel }}</RouterLink>
    </section>

    <template v-else-if="shot">
      <div class="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)] lg:items-start lg:gap-8">
        <div class="lg:sticky lg:top-6">
          <div class="relative overflow-hidden rounded-2xl border border-edge bg-panel">
          <ShotCanvas
            v-if="src && shot.grid"
            :src="canvasSrc"
            :grid="shot.grid"
            :composition="analysis?.composition"
            :guide="guide"
            :show-findings="showRead"
            :layer="canvasLayer"
            :mark="canvasMark"
          />
          <button
            type="button"
            class="absolute bottom-3 right-3 min-h-11 rounded-xl border border-white/10 bg-black/72 px-3 py-2 text-[11px]"
            :class="showRead ? 'text-paper' : 'text-muted'"
            @click="showRead = !showRead"
          >
            {{ showRead ? 'See clean' : 'Show visual' }}
          </button>
        </div>

          <div class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-edge bg-panel px-3 py-2.5">
            <span class="eyebrow mr-1">Guide</span>
          <button
            v-for="g in guides"
            :key="g"
            type="button"
            class="tap-target justify-center px-2 t-meta"
              :class="guide === g ? 'text-accent' : 'text-muted hover:text-paper'"
            @click="selectGuide(g)"
          >
            {{ labels[g] }}
          </button>
            <button v-if="picked" type="button" class="tap-target px-2 t-meta text-accent" @click="picked = ''">
              Back to story
            </button>
            <span v-if="fit" class="ml-auto t-meta text-neutral-300">{{ fit }}</span>
          </div>
        </div>

        <div class="min-w-0">
          <template v-if="analysis">
            <h1 class="eyebrow">A closer look</h1>
            <p class="mt-2 t-meta">{{ camera.slice(-2).join(' · ') || shot.filename }}</p>

            <section v-if="currentStory" class="surface mt-5 p-5 sm:p-6">
              <div class="flex items-center justify-between gap-4">
                <p class="eyebrow">What this Shot is doing</p>
                <p class="t-num text-[11px] text-muted">{{ storyIndex + 1 }} of {{ visualStory.length }}</p>
              </div>
              <div v-if="visualStory.length > 1" class="mt-3 flex gap-2" aria-hidden="true">
                <span
                  v-for="(_, index) in visualStory"
                  :key="index"
                  class="h-1.5 w-1.5 rounded-full"
                  :class="index === storyIndex ? 'bg-accent' : 'bg-neutral-700'"
                />
              </div>
              <p
                class="eyebrow mt-5"
                :class="currentStory.layer === 'finding' ? 'text-bad' : currentStory.layer === 'action' ? 'text-accent' : 'text-muted'"
              >
                {{ currentStory.label }}
              </p>
              <h2 class="mt-2 text-[24px] leading-8 font-semibold tracking-[-0.025em] text-paper">
                {{ currentStory.title }}
              </h2>
              <p v-if="currentStory.body" class="mt-2 t-body text-neutral-300">{{ currentStory.body }}</p>
              <template v-if="currentStory.mark?.visual_artifact?.status === 'rendered'">
                <p class="mt-4 t-meta text-paper">
                  {{ currentStory.mark.visual_artifact.authority === 'measured' ? 'Measured from this Shot' : "Shoots' visual read" }} ·
                  {{ currentStory.mark.visual_artifact.label }}
                </p>
                <p v-if="currentStory.mark.visual_artifact.legend" class="mt-1 t-meta">
                  {{ currentStory.mark.visual_artifact.legend }}
                </p>
                <p v-if="artifactMetrics(currentStory.mark.visual_artifact)" class="mt-1 t-num text-[11px] text-muted">
                  {{ artifactMetrics(currentStory.mark.visual_artifact) }}
                </p>
              </template>
              <div v-if="currentTechniqueContext" class="mt-5 border-t border-edge pt-5">
                <p class="text-[13px] leading-5 font-medium text-paper">{{ techniqueHistoryLine }}</p>
                <p
                  class="mt-1 t-meta"
                  :class="currentTechniqueContext.criteria_met_sessions ? 'text-accent' : ''"
                >
                  {{ repeatabilityLine }}
                </p>

                <p v-if="isSampleRecord" class="mt-3 t-meta">
                  Sample layout only. No Keeper mark or Experiment can be saved here.
                </p>
                <template v-else>
                  <RouterLink
                    v-if="currentTechniqueContext.reproduce_sessions"
                    :to="{ name: 'journey' }"
                    class="tap-target mt-2 t-meta text-accent"
                  >
                    See where it appears again
                  </RouterLink>

                  <RouterLink
                    v-else-if="currentExperimentDirection?.state === 'started'"
                    :to="{ name: 'now', query: { focus: 'experiment' } }"
                    class="tap-target mt-2 t-meta text-accent"
                  >
                    Open Experiment
                  </RouterLink>

                  <div v-else-if="currentExperimentDirection?.state === 'saved'" class="mt-4 rounded-xl border border-edge bg-panel-2/55 p-4">
                    <p class="eyebrow text-accent">Saved for another day</p>
                    <p class="mt-2 t-body text-paper">{{ currentExperimentDirection.question }}</p>
                    <p class="mt-1 t-meta">Nothing has started yet.</p>
                    <button
                      type="button"
                      class="tap-target mt-2 t-meta text-muted hover:text-paper"
                      :disabled="busy === 'direction-choice'"
                      @click="chooseDirection(false)"
                    >
                      {{ busy === 'direction-choice' ? 'Updating…' : 'Delete saved question' }}
                    </button>
                  </div>

                  <p v-else-if="currentExperimentDirection?.state === 'left'" class="mt-3 t-meta">
                    You left this question. No Experiment was created.
                  </p>

                  <div v-else-if="currentTechniqueContext.positive_keeper_shots" class="mt-4">
                    <p class="eyebrow text-accent">A question for another day</p>
                    <p class="mt-2 t-body text-paper">
                      Want to try this same choice in a different Scene?
                    </p>
                    <button
                      type="button"
                      class="btn mt-4 w-full"
                      :disabled="busy === 'direction-choice'"
                      @click="chooseDirection(true)"
                    >
                      {{ busy === 'direction-choice' ? 'Saving…' : 'Try another day' }}
                    </button>
                    <button
                      type="button"
                      class="tap-target mt-2 w-full justify-center t-meta text-muted hover:text-paper"
                      :disabled="busy === 'direction-choice'"
                      @click="chooseDirection(false)"
                    >
                      Leave it
                    </button>
                  </div>

                  <p v-else class="mt-3 t-meta">Mark a Keeper if this is a choice you may want to try again.</p>
                </template>
              </div>
              <div class="mt-5 grid grid-cols-3 items-center gap-2">
                <button type="button" class="tap-target justify-start t-meta disabled:opacity-35" :disabled="storyIndex === 0" @click="previousStory">
                  Previous
                </button>
                <button type="button" class="tap-target justify-center t-meta text-accent" @click="showRead = !showRead">
                  {{ showRead ? 'See clean' : 'Show visual' }}
                </button>
                <button
                  type="button"
                  class="tap-target justify-end t-meta text-right text-accent disabled:text-muted disabled:opacity-35"
                  :disabled="storyIndex >= visualStory.length - 1"
                  @click="nextStory"
                >
                  Next
                </button>
              </div>
            </section>

            <details v-if="keeperReceiptItems.length" class="mt-4 rounded-2xl border border-edge bg-panel">
              <summary class="flex min-h-14 cursor-pointer list-none items-center gap-3 px-5 py-4 t-body text-neutral-200">
                <span>Why this Keeper matters</span>
                <span class="ml-auto text-muted" aria-hidden="true">+</span>
              </summary>
              <CompanionReceipt
                class="border-x-0 border-b-0"
                title="What your Keeper changed"
                :items="keeperReceiptItems"
                compact
              />
            </details>

            <section v-if="shootContext" class="surface-soft mt-4 p-4">
              <div class="flex items-center gap-3">
                <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-neutral-800 text-neutral-300">
                  <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-2">
                    <path d="m5 12 4 4L19 6" />
                  </svg>
                </span>
                <div>
                  <p class="text-[14px] font-medium text-paper">This outing stays finished</p>
                  <p class="mt-0.5 text-[12px] leading-5 text-muted">The Keeper tells Shoots what matters to you. It does not rewrite the outing.</p>
                </div>
              </div>
              <RouterLink :to="backTarget" class="btn-quiet mt-4 w-full">Return to Shoot Record</RouterLink>
            </section>

            <MeasuredStrip class="mt-4" :tone="shot.tone" :motion="shot.motion" />

            <ShotDeconstruction :shot="shot" :analysis="analysis" :read-only="isSampleRecord" />

          <div class="mt-8">
              <DisclosureRow v-if="otherMoves.length" label="Other possible moves" :count="otherMoves.length">
                <ul class="space-y-4">
                  <li v-for="(move, i) in otherMoves" :key="i">
                    <p class="t-body text-paper">{{ move.what }}</p>
                    <p class="mt-1 t-meta">
                      {{ kindLabel(move.kind) }} · {{ (move.warrant || 'unspecified').replace(/_/g, ' ') }} · {{ reason(move) }}
                    </p>
                    <p v-if="move.challenges_technique_ids?.length" class="mt-1 t-meta text-accent">
                      Alternative challenges {{ move.challenges_technique_ids.map((id) => id.replace(/_/g, ' ')).join(', ') }}
                    </p>
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

            <DisclosureRow v-if="critique" label="How Shoots read it · visual opinion">
              <p class="t-body text-neutral-300">{{ critique }}</p>
            </DisclosureRow>

            <DisclosureRow label="Techniques retained from the visual reads" :count="analysis.techniques.length">
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
                <li v-if="!analysis.techniques.length" class="t-meta">No Technique met the stored confidence rules for this Shot.</li>
              </ul>
            </DisclosureRow>

            <DisclosureRow
              v-if="cropUrl"
              label="A crop it tested"
            >
              <CropComparison
                :before-src="src"
                :after-src="cropUrl"
                :reason="analysis.composition.crop_reason"
              />
            </DisclosureRow>

            <DisclosureRow label="Camera" :count="camera.length ? '' : 'none'">
              <p class="t-num text-[13px] text-neutral-400">{{ camera.join(' · ') || 'No EXIF in this file.' }}</p>
            </DisclosureRow>

            <DisclosureRow
              v-if="run"
              :label="isSampleRecord ? 'Sample workflow layout' : 'Autonomous Run'"
              :count="isSampleRecord ? 'fixture' : run.status"
            >
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
            <button v-if="!isSampleRecord" type="button" class="tap-target text-left hover:text-neutral-200" @click="confirmSource = true">
              This is Inspiration, not my Shot
            </button>
          </div>

            <section v-if="confirmSource && !isSampleRecord" class="mt-4 rounded-xl border border-accent/35 bg-accent/5 p-4">
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
            <p class="mt-3 t-body">Shoots has not finished reading this Shot yet.</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
