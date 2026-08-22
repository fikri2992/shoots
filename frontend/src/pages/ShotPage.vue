<script>
import { mapActions, mapState } from 'pinia'

import CoachPanel from '@/components/CoachPanel.vue'
import ShotCanvas from '@/components/ShotCanvas.vue'
import StatusChip from '@/components/StatusChip.vue'
import { useShootsStore } from '@/stores/shoots'

/** One shot: the frame with the composition read drawn on it, the evidence, the critique. */
export default {
  name: 'ShotPage',
  components: { CoachPanel, ShotCanvas, StatusChip },
  props: { shotId: { type: String, required: true } },
  data() {
    return { showGrid: false, showOverlay: true }
  },
  computed: {
    ...mapState(useShootsStore, ['shotById', 'questById']),
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
    facts() {
      const e = this.shot?.exif || {}
      const v = this.shot?.video
      const out = []
      if (v) out.push(`${v.width}×${v.height}`, `${v.fps} fps`, `${v.duration_s.toFixed(1)} s`)
      if (e.exposure_time_s) out.push(e.exposure_time_s >= 1 ? `${e.exposure_time_s} s` : `1/${Math.round(1 / e.exposure_time_s)} s`)
      if (e.f_number) out.push(`f/${e.f_number}`)
      if (e.iso) out.push(`ISO ${e.iso}`)
      if (e.focal_length_35mm) out.push(`${e.focal_length_35mm} mm`)
      if (e.model) out.push(e.model)
      return out
    },
    quest() {
      return this.shot?.quest_id ? this.questById(this.shot.quest_id) : null
    },
  },
  async created() {
    if (!this.view) await this.fetchShot(this.shotId)
  },
  methods: {
    ...mapActions(useShootsStore, ['fetchShot']),
  },
}
</script>

<template>
  <div class="mx-auto max-w-3xl p-4 pb-24 md:pb-8">
    <div v-if="!shot" class="py-10 text-center text-sm text-neutral-500">Loading…</div>
    <template v-else>
      <header class="mb-3 flex items-center justify-between gap-3">
        <div class="min-w-0">
          <RouterLink :to="{ name: 'shots' }" class="text-xs text-neutral-500 hover:text-neutral-200">← Shots</RouterLink>
          <h1 class="truncate text-sm font-semibold">{{ shot.filename }}</h1>
        </div>
        <StatusChip :status="shot.status" />
      </header>

      <ShotCanvas
        v-if="src && shot.grid"
        :src="src"
        :grid="shot.grid"
        :composition="showOverlay ? analysis?.composition : null"
        :show-grid="showGrid"
      />

      <div class="mt-2 flex flex-wrap items-center gap-3 text-xs text-neutral-400">
        <label class="flex items-center gap-1.5"><input v-model="showOverlay" type="checkbox" class="accent-neutral-300" />overlay</label>
        <label class="flex items-center gap-1.5"><input v-model="showGrid" type="checkbox" class="accent-neutral-300" />grid</label>
        <span class="ml-auto font-mono text-[11px] text-neutral-500">{{ facts.join(' · ') }}</span>
      </div>

      <a
        v-if="shot.drive_review_url"
        :href="shot.drive_review_url"
        target="_blank"
        rel="noopener"
        class="mt-3 flex items-center justify-between rounded-xl border border-lime-900/60 bg-lime-950/20 px-4 py-3 text-sm text-lime-100 hover:border-lime-700"
      >
        <span>The reviewed copy is in your Drive, under <span class="font-mono">Shoots/Reviewed</span>.</span>
        <span class="text-xs text-lime-300">open ↗</span>
      </a>

      <p v-if="shot.error" class="mt-3 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{{ shot.error }}</p>

      <section v-if="analysis" class="mt-4 space-y-4">
        <div class="rounded-xl border border-edge bg-panel p-4">
          <div class="flex items-baseline justify-between">
            <h2 class="text-sm font-semibold">Critique</h2>
            <span class="font-mono text-sm">{{ analysis.score }}/10</span>
          </div>
          <p class="mt-2 text-sm leading-relaxed text-neutral-200">{{ analysis.critique }}</p>
        </div>

        <div v-if="analysis.composition.moves.length" class="rounded-xl border border-edge bg-panel p-4">
          <h2 class="text-sm font-semibold">Moves</h2>
          <ol class="mt-2 space-y-2 text-sm">
            <li v-for="(m, i) in analysis.composition.moves" :key="i" class="flex gap-3">
              <span class="h-5 w-5 shrink-0 rounded-full bg-[#ff5a5a] text-center font-mono text-[11px] leading-5 text-black">{{ i + 1 }}</span>
              <span><span class="text-neutral-100">{{ m.what }}</span> <span class="text-neutral-500">{{ m.from_cells.join(',') }} → {{ m.to_cells.join(',') }}</span><br /><span class="text-neutral-300">{{ m.reason }}</span></span>
            </li>
          </ol>
        </div>

        <CoachPanel :shot-id="shotId" />

        <div class="rounded-xl border border-edge bg-panel p-4">
          <h2 class="text-sm font-semibold">Evidence</h2>
          <ul class="mt-2 space-y-2 text-sm">
            <li v-for="t in analysis.techniques" :key="t.technique_id">
              <div class="flex items-center gap-2">
                <span class="text-neutral-100">{{ t.technique_id.replace(/_/g, ' ') }}</span>
                <span class="h-1.5 flex-1 overflow-hidden rounded bg-neutral-800"><span class="block h-full bg-sky-400" :style="{ width: `${Math.round(t.confidence * 100)}%` }" /></span>
                <span class="w-10 text-right font-mono text-[11px] text-neutral-400">{{ Math.round(t.confidence * 100) }}%</span>
              </div>
              <p class="text-xs text-neutral-400">{{ t.note }} <span v-if="t.cells.length" class="font-mono text-neutral-600">{{ t.cells.join(' ') }}</span></p>
            </li>
            <li v-if="!analysis.techniques.length" class="text-neutral-500">No technique tagged with confidence.</li>
          </ul>
        </div>

        <RouterLink v-if="quest" :to="{ name: 'dashboard' }" class="block rounded-xl border border-edge bg-panel p-4 text-sm hover:border-edge-strong">
          Submitted for <span class="text-neutral-100">{{ quest.title }}</span>
          <StatusChip :status="quest.status" class="ml-2" />
        </RouterLink>
      </section>
      <p v-else-if="shot.status !== 'failed'" class="mt-4 text-sm text-neutral-500">The Analyst has not read this one yet.</p>
    </template>
  </div>
</template>
