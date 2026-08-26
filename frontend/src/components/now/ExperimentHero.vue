<script>
import { mapActions, mapState } from 'pinia'

import DisclosureRow from '@/components/DisclosureRow.vue'
import ShootAction from '@/components/ShootAction.vue'
import VerdictNote from '@/components/VerdictNote.vue'
import { useShootsStore } from '@/stores/shoots'

const EXIF_LABELS = {
  shutter_min_s: (value) => `shutter at least ${shutter(value)}`,
  shutter_max_s: (value) => `shutter no slower than ${shutter(value)}`,
  aperture_max: (value) => `aperture f/${value} or wider`,
  aperture_min: (value) => `aperture f/${value} or narrower`,
  iso_min: (value) => `ISO ${value} or higher`,
  iso_max: (value) => `ISO ${value} or lower`,
  focal_min_mm: (value) => `${value} mm or longer`,
  focal_max_mm: (value) => `${value} mm or shorter`,
  flash: (value) => (value ? 'flash must fire' : 'no flash'),
}

function shutter(seconds) {
  return seconds >= 1 ? `${seconds} s` : `1/${Math.round(1 / seconds)} s`
}

function clock(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default {
  name: 'ExperimentHero',
  components: { DisclosureRow, ShootAction, VerdictNote },
  props: { experiment: { type: Object, required: true } },
  computed: {
    ...mapState(useShootsStore, ['busy', 'shotById']),
    supported() {
      return this.experiment.type === 'reproduce' && Boolean(this.experiment.reference_shot_id)
    },
    technique() {
      return this.experiment.technique_id.replace(/_/g, ' ')
    },
    steps() {
      const brief = (this.experiment.brief || '').trim()
      const lines = brief.includes('\n') ? brief.split(/\n+/) : brief.split(/\s+(?=\d{1,2}[.)]\s)/)
      return lines.map((line) => line.replace(/^\s*\d+[.)]\s*/, '').trim()).filter(Boolean)
    },
    criteria() {
      return this.experiment.criteria?.text || []
    },
    cameraRules() {
      return Object.entries(this.experiment.criteria?.exif || {})
        .filter(([, value]) => value !== null && value !== undefined)
        .map(([key, value]) => EXIF_LABELS[key]?.(value) || `${key}: ${value}`)
    },
    when() {
      const bits = []
      if (this.experiment.timing) {
        if (this.experiment.deliver_at && new Date(this.experiment.deliver_at) > Date.now()) {
          bits.push(`Lands ${clock(this.experiment.deliver_at)}`)
        }
        bits.push(this.experiment.timing.reason)
      }
      if (this.experiment.status === 'open' && this.experiment.due_at) {
        const days = Math.ceil((new Date(this.experiment.due_at) - Date.now()) / 86400000)
        bits.push(days <= 0 ? 'due today' : `${days} day${days === 1 ? '' : 's'} left`)
      }
      return bits.filter(Boolean).join(' · ')
    },
    attempts() {
      return [...(this.experiment.verdicts || [])].reverse()
    },
    resultCount() {
      return this.experiment.result_shot_ids?.length || 0
    },
    referenceView() {
      return this.shotById(this.experiment.reference_shot_id)
    },
    referenceThumb() {
      const path = this.referenceView?.shot?.blobs?.thumb
      return path ? `/api/blobs/${path}` : ''
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['leaveExperiment']),
  },
}
</script>

<template>
  <article class="page-shell pb-28 pt-7 md:pb-12 md:pt-10">
    <header class="flex items-end justify-between gap-5">
      <div>
        <p class="eyebrow">Now</p>
        <p class="mt-1 text-sm text-muted">One optional Experiment. Free Shots remain free.</p>
      </div>
      <p class="hidden max-w-xs text-right t-meta sm:block">The Companion waits until you choose to use it.</p>
    </header>

    <section v-if="!supported" class="surface mt-7 p-6 sm:p-8">
      <p class="eyebrow text-accent">Legacy Experiment</p>
      <h1 class="mt-4 max-w-2xl t-hero">This old Experiment used the retired contract.</h1>
      <p class="mt-5 max-w-2xl t-body text-neutral-300">
        Shoots will not grade an Explore as though it were Reproduce. Leave it, then Scout will wait for a marked Keeper that supports an honest result.
      </p>
      <button class="btn mt-7" :disabled="busy === 'leave'" @click="leaveExperiment(experiment.id)">
        {{ busy === 'leave' ? 'Leaving…' : 'Leave this Experiment' }}
      </button>
    </section>

    <div v-else class="mt-7 grid gap-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)] lg:items-start">
      <section class="surface-active overflow-hidden">
        <div class="h-1 bg-accent" />
        <div class="p-5 sm:p-7 lg:p-9">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <p class="eyebrow text-accent">Reproduce · {{ technique }}</p>
            <p v-if="when" class="t-meta">{{ when }}</p>
          </div>
          <h1 class="mt-5 max-w-3xl t-hero lg:text-[48px]">{{ experiment.title }}</h1>

          <RouterLink
            v-if="referenceView"
            :to="{ name: 'shot', params: { shotId: experiment.reference_shot_id } }"
            class="mt-7 grid overflow-hidden rounded-2xl border border-edge bg-panel-2 sm:grid-cols-[150px_1fr]"
          >
            <img v-if="referenceThumb" :src="referenceThumb" alt="" class="h-40 w-full object-cover sm:h-full" />
            <span class="p-4 sm:p-5">
              <span class="eyebrow">The Keeper to repeat</span>
              <span class="mt-2 block text-[17px] leading-6 text-paper">{{ referenceView.shot.filename }}</span>
              <span class="mt-2 block t-meta">This exact Shot was fixed before any result.</span>
            </span>
          </RouterLink>

          <div class="mt-8 border-t border-edge pt-7">
            <p class="eyebrow">Declared before the result</p>
            <ol class="mt-4 space-y-3">
              <li v-for="(criterion, index) in criteria" :key="index" class="flex gap-4 rounded-xl bg-panel-2/55 px-4 py-3.5">
                <span class="t-num text-[12px] text-accent">0{{ index + 1 }}</span>
                <span class="t-body text-paper">{{ criterion }}</span>
              </li>
            </ol>
            <p v-if="cameraRules.length" class="mt-4 t-meta">Measured from EXIF: {{ cameraRules.join(' · ') }}</p>
          </div>

          <div v-if="attempts.length" class="mt-7 surface-soft p-4">
            <p class="eyebrow mb-3">Latest result</p>
            <VerdictNote :verdict="attempts[0]" />
            <p v-if="resultCount > 1" class="mt-3 t-meta">{{ resultCount }} explicit result Shots recorded</p>
          </div>
        </div>
      </section>

      <aside class="surface p-5 sm:p-6 lg:sticky lg:top-7">
        <p class="eyebrow text-accent">One move</p>
        <p class="mt-3 text-[20px] leading-7 font-medium text-paper">
          {{ steps[0] || 'Make the same decision again, deliberately.' }}
        </p>

        <div v-if="experiment.status === 'open'" class="mt-6 hidden lg:block">
          <ShootAction :experiment-id="experiment.id" label="Use a Shot as the result" />
          <button
            type="button"
            class="mt-2 w-full py-2 text-center t-meta hover:text-paper"
            :disabled="busy === 'leave'"
            @click="leaveExperiment(experiment.id)"
          >
            {{ busy === 'leave' ? 'Leaving…' : 'Leave without a judgment' }}
          </button>
        </div>

        <div class="mt-7 border-t border-edge pt-2">
          <DisclosureRow label="The full approach" :count="steps.length">
            <ol class="space-y-3">
              <li v-for="(step, index) in steps" :key="index" class="flex gap-3 t-body">
                <span class="w-4 shrink-0 t-num text-[11px] text-muted">{{ index + 1 }}</span>
                <span>{{ step }}</span>
              </li>
            </ol>
          </DisclosureRow>
          <DisclosureRow label="Why Scout chose it">
            <p class="t-body">{{ experiment.why_now }}</p>
          </DisclosureRow>
          <DisclosureRow v-if="experiment.references?.length" label="Sourced Inspiration" :count="experiment.references.length">
            <ul class="space-y-2">
              <li v-for="reference in experiment.references" :key="reference.url">
                <a :href="reference.url" target="_blank" rel="noopener" class="t-body text-neutral-400 hover:text-paper">
                  {{ reference.title }} ↗
                </a>
              </li>
            </ul>
          </DisclosureRow>
        </div>
      </aside>
    </div>

    <div
      v-if="supported && experiment.status === 'open'"
      class="fixed inset-x-0 bottom-[68px] z-20 border-t border-edge bg-ink/96 px-5 py-3 backdrop-blur-xl lg:hidden"
    >
      <div class="mx-auto flex max-w-lg items-center gap-3">
        <div class="flex-1"><ShootAction :experiment-id="experiment.id" label="Use a result Shot" /></div>
        <button class="btn-quiet px-4" :disabled="busy === 'leave'" @click="leaveExperiment(experiment.id)">
          Leave
        </button>
      </div>
    </div>
  </article>
</template>
