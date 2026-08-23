<script>
import { mapActions, mapState } from 'pinia'

import DisclosureRow from '@/components/DisclosureRow.vue'
import ShotCanvas from '@/components/ShotCanvas.vue'
import { useCoachStore } from '@/stores/coach'
import { useShootsStore } from '@/stores/shoots'

const ELEMENTS = ['impact', 'composition', 'lighting', 'technical', 'story']

/** Cell refs are precise and unreadable in prose; keep them out of the sentence. */
function withoutCells(text) {
  return text
    .replace(/\b[A-H][1-9](\s*(?:to|-|–|,)\s*[A-H][1-9])?\b/g, '')
    .replace(/\s{2,}/g, ' ')
    .replace(/\s+([.,])/g, '$1')
    .trim()
}

/** Three lenses describe the same frame, so the descriptions repeat. Keep one. */
function dedupe(lines, limit) {
  const seen = new Set()
  const out = []
  for (const line of lines) {
    const clean = withoutCells(line)
    const key = clean.toLowerCase().replace(/[^a-z ]/g, '').split(/\s+/).slice(0, 5).join(' ')
    if (!clean || seen.has(key)) continue
    seen.add(key)
    out.push(clean)
    if (out.length >= limit) break
  }
  return out
}

/**
 * One frame: what it looks like with the read drawn on it, what the panel
 * concluded, and one way in to talk about it. Evidence is available but never
 * in the way.
 */
export default {
  name: 'FramePage',
  components: { DisclosureRow, ShotCanvas },
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
    tags() {
      return (this.analysis?.techniques || []).slice(0, 3).map((t) => t.technique_id.replace(/_/g, ' '))
    },
    observations() {
      return dedupe(this.analysis?.observations || [], 6)
    },
    moves() {
      return (this.analysis?.composition?.moves || []).filter((m) => m.what)
    },
    elements() {
      const scored = this.analysis?.elements || {}
      return ELEMENTS.filter((k) => k in scored).map((k) => ({ key: k, value: scored[k] }))
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
    quest() {
      return this.shot?.quest_id ? this.questById(this.shot.quest_id) : null
    },
    lenses() {
      return this.analysis?.panel?.lenses?.join(', ') || 'technician, composer, storyteller'
    },
  },
  async created() {
    if (!this.view) await this.fetchShot(this.shotId)
    if (this.$route.hash === '#coach') this.openFor(this.shotId, {})
  },
  methods: {
    ...mapActions(useShootsStore, ['fetchShot']),
    ...mapActions(useCoachStore, ['openFor']),
    talk(opener) {
      this.openFor(this.shotId, { opener })
    },
  },
}
</script>

<template>
  <div class="pb-24 md:pb-10">
    <p v-if="!shot" class="col gutter pt-12 t-meta">Loading…</p>

    <div v-else class="mx-auto w-full max-w-5xl md:grid md:grid-cols-2 md:gap-8 md:px-6 md:pt-8">
      <div class="md:sticky md:top-20 md:self-start">
        <div class="relative">
          <ShotCanvas
            v-if="src && shot.grid"
            :src="src"
            :grid="shot.grid"
            :composition="showOverlay ? analysis?.composition : null"
            :show-grid="showGrid"
          />
          <div class="absolute bottom-3 right-3 flex gap-2">
            <button
              type="button"
              class="rounded-full bg-black/70 px-3 py-1 t-num text-[11px]"
              :class="showOverlay ? 'text-neutral-100' : 'text-neutral-500'"
              @click="showOverlay = !showOverlay"
            >
              read
            </button>
            <button
              type="button"
              class="rounded-full bg-black/70 px-3 py-1 t-num text-[11px]"
              :class="showGrid ? 'text-neutral-100' : 'text-neutral-500'"
              @click="showGrid = !showGrid"
            >
              grid
            </button>
          </div>
        </div>
      </div>

      <div class="gutter md:px-0">
        <div class="flex items-baseline gap-3 pt-6">
          <RouterLink :to="{ name: 'frames' }" class="t-meta hover:text-neutral-200">← Frames</RouterLink>
          <span v-if="analysis" class="ml-auto t-num text-[15px] text-neutral-300">{{ analysis.score }}/10</span>
        </div>

        <template v-if="analysis">
          <p class="mt-1 t-meta">{{ tags.join(' · ') }}</p>
          <p class="mt-4 t-body">{{ analysis.critique }}</p>

          <ol v-if="moves.length" class="mt-6 space-y-3">
            <li v-for="(m, i) in moves" :key="i" class="flex gap-3">
              <span class="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-[#ff5a5a] text-center t-num text-[11px] leading-5 text-black">
                {{ i + 1 }}
              </span>
              <span class="t-body">
                <span class="text-neutral-100">{{ m.what }}</span>
                <span class="mt-0.5 block text-neutral-400">{{ m.reason }}</span>
              </span>
            </li>
          </ol>

          <button type="button" class="btn-quiet mt-6 w-full" @click="talk('Talk me through this frame.')">
            Talk it through with the Coach
          </button>

          <div class="mt-8">
            <DisclosureRow v-if="observations.length" label="What it saw" :count="observations.length">
              <ul class="space-y-2">
                <li v-for="(o, i) in observations" :key="i" class="flex gap-3 t-body text-neutral-300">
                  <span class="mt-2 h-1 w-1 shrink-0 rounded-full bg-neutral-700" />
                  <span>{{ o }}</span>
                </li>
              </ul>
            </DisclosureRow>

            <DisclosureRow label="How it scored" :count="`${analysis.score}/10`">
              <ul class="space-y-2">
                <li v-for="e in elements" :key="e.key">
                  <div class="flex items-baseline justify-between t-meta">
                    <span>{{ e.key }}</span>
                    <span class="t-num text-neutral-400">{{ e.value }}</span>
                  </div>
                  <span class="mt-1 block h-1 overflow-hidden rounded bg-edge">
                    <span class="block h-full bg-accent/80" :style="{ width: `${e.value * 10}%` }" />
                  </span>
                </li>
              </ul>
              <p class="mt-3 t-meta">
                The PPA merit-image elements, weighted. Scored by {{ lenses }} and averaged.
              </p>
            </DisclosureRow>

            <DisclosureRow label="Techniques it agreed on" :count="analysis.techniques.length">
              <ul class="space-y-3">
                <li v-for="t in analysis.techniques" :key="t.technique_id">
                  <div class="flex items-center gap-2">
                    <span class="t-body text-neutral-100">{{ t.technique_id.replace(/_/g, ' ') }}</span>
                    <span
                      v-if="t.agreement"
                      class="t-num text-[10px] tracking-widest text-neutral-500"
                      :title="`seen by ${(t.lenses || []).join(', ')}`"
                    >
                      {{ '●'.repeat(t.agreement) + '○'.repeat(Math.max(0, 3 - t.agreement)) }}
                    </span>
                    <span class="ml-auto t-num text-[11px] text-neutral-500">{{ Math.round(t.confidence * 100) }}%</span>
                  </div>
                  <p class="t-meta">{{ t.note }}</p>
                </li>
                <li v-if="!analysis.techniques.length" class="t-meta">Nothing reached agreement on this frame.</li>
              </ul>
            </DisclosureRow>

            <DisclosureRow v-if="cropUrl" label="A crop it tested" :count="`${analysis.composition.crop_before} → ${analysis.composition.crop_after}`">
              <img :src="cropUrl" alt="tested crop" class="max-h-64 rounded-xl object-contain" />
              <p class="mt-2 t-body text-neutral-400">
                {{ analysis.composition.crop_reason }}
                <span class="mt-1 block t-meta">Rendered and scored as a finished frame; kept only because it scored higher.</span>
              </p>
            </DisclosureRow>

            <DisclosureRow label="Camera" :count="camera.length ? '' : 'none'">
              <p class="t-num text-[13px] text-neutral-400">{{ camera.join(' · ') || 'No EXIF in this file.' }}</p>
            </DisclosureRow>
          </div>

          <div class="mt-8 space-y-2 border-t border-edge pt-4 t-meta">
            <a v-if="shot.drive_review_url" :href="shot.drive_review_url" target="_blank" rel="noopener" class="block hover:text-neutral-200">
              The reviewed copy is in your Drive ↗
            </a>
            <RouterLink v-if="quest" :to="{ name: 'now' }" class="block hover:text-neutral-200">
              Sent for “{{ quest.title }}” ▸
            </RouterLink>
            <p>{{ shot.filename }}</p>
          </div>
        </template>

        <p v-else-if="shot.error" class="mt-4 rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 t-body text-bad">
          {{ shot.error }}
        </p>
        <p v-else class="mt-4 t-body text-neutral-500">The Analyst has not read this one yet.</p>
      </div>
    </div>
  </div>
</template>
