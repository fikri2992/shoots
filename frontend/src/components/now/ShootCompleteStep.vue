<script>
import { mapState } from 'pinia'

import CompanionReceipt from '@/components/CompanionReceipt.vue'
import { humanizeLegacyText, scoutStory, shootSummary } from '@/domain/copy'
import { useShootsStore } from '@/stores/shoots'

export default {
  name: 'ShootCompleteStep',
  components: { CompanionReceipt },
  props: {
    record: { type: Object, required: true },
    experiment: { type: Object, default: null },
    hasRecommendation: { type: Boolean, default: false },
  },
  computed: {
    ...mapState(useShootsStore, ['orderedShots', 'me']),
    isSampleRecord() {
      return this.me?.record_mode === 'sample'
    },
    members() {
      const byId = new Map(this.orderedShots.map((item) => [item.shot.id, item]))
      return (this.record.shot_ids || []).map((id) => byId.get(id)).filter(Boolean)
    },
    previewMembers() {
      if (this.members.length <= 3) return this.members
      const middle = Math.floor((this.members.length - 1) / 2)
      return [this.members[0], this.members[middle], this.members[this.members.length - 1]]
    },
    settledCount() {
      return Object.values(this.record.run_outcomes || {}).filter((status) =>
        ['completed', 'terminal'].includes(status),
      ).length
    },
    readableCount() {
      return this.record.receipt?.readable_shot_count ??
        Math.max(0, (this.record.shot_ids?.length || 0) - (this.record.unreadable_shot_ids?.length || 0))
    },
    recordTarget() {
      return {
        name: 'shoot-record',
        params: { shootId: this.record.shoot_id, revision: this.record.revision },
      }
    },
    experimentTarget() {
      return { name: 'now', query: { focus: 'experiment' } }
    },
    repeated() {
      return humanizeLegacyText(this.record.receipt?.repeated?.[0] || '')
    },
    varied() {
      return humanizeLegacyText(this.record.receipt?.varied?.[0] || '')
    },
    primaryDiscovery() {
      return this.repeated || this.varied || this.shootSummary
    },
    scoutCopy() {
      if (this.isSampleRecord) return 'Hand-authored Scout layout. It is not a model decision.'
      return scoutStory(this.record.scout)
    },
    shootSummary() {
      return shootSummary(this.record.receipt)
    },
    receiptItems() {
      const shots = this.record.receipt?.shot_count || this.record.shot_ids?.length || 0
      const scenes = this.record.receipt?.scene_count || 0
      if (this.isSampleRecord) {
        return [
          {
            label: 'Sample layout',
            text: `${shots} Shot cards and ${scenes} Scene groups were hand-authored to test the interface.`,
            state: 'limit',
          },
          {
            label: 'Agents',
            text: 'No agents ran. These timings and outcomes are fixture copy.',
            state: 'limit',
          },
          {
            label: 'Actions',
            text: 'Keeper marks, Experiments, and other writes are disabled.',
            state: 'waiting',
          },
          { label: 'Use', text: 'Judge the layout only, not the workflow.', state: 'current' },
        ]
      }
      const unreadable = this.record.unreadable_shot_ids?.length || 0
      const handled = unreadable
        ? `Shoots accounted for all ${shots} Shots, read ${this.readableCount}, and recorded ${unreadable} as unreadable.`
        : `Shoots accounted for all ${shots} Shots and read ${this.readableCount} across ${scenes} ${scenes === 1 ? 'Scene' : 'Scenes'}.`
      const next = this.experiment
        ? `An optional ${this.experiment.type || ''} Experiment is ready. Try it only if it fits today.`
        : this.scoutCopy
      return [
        {
          label: 'Shoots handled',
          text: handled,
          state: 'done',
        },
        {
          label: 'You decided',
          text: 'No Keeper mark or Experiment choice was required for this record.',
          state: 'waiting',
        },
        {
          label: 'The result',
          text: 'Your outing now has one story, with every Shot and Scene still accounted for.',
          state: 'done',
        },
        { label: 'Next', text: next, state: 'current' },
      ]
    },
  },
  methods: {
    thumb(view) {
      const path = view?.shot?.blobs?.thumb || view?.shot?.blobs?.original || ''
      return path ? `/api/blobs/${path}` : ''
    },
  },
}
</script>

<template>
  <section class="page-shell pb-8 pt-6 md:pt-10">
    <div class="grid gap-5 lg:grid-cols-[minmax(0,0.92fr)_minmax(420px,1.08fr)] lg:items-stretch">
      <div class="surface order-2 flex flex-col p-6 sm:p-8 lg:order-1 lg:p-9">
        <div class="flex items-center gap-2">
          <span class="flex h-7 w-7 items-center justify-center rounded-full bg-accent text-ink" aria-hidden="true">
            <svg viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-[2.4]">
              <path d="m5 12 4 4L19 6" />
            </svg>
          </span>
          <p class="eyebrow text-accent">{{ isSampleRecord ? 'Sample Shoot layout' : 'Shoot complete' }}</p>
        </div>

        <h1 class="mt-6 t-hero lg:text-[48px]">
          {{ isSampleRecord ? 'This is what a settled Shoot could look like.' : 'Your Shoot is ready.' }}
        </h1>
        <div class="mt-5 max-w-xl">
          <p class="eyebrow">One thing worth noticing</p>
          <p class="mt-2 text-[19px] font-medium leading-7 text-paper">{{ primaryDiscovery }}</p>
          <p v-if="primaryDiscovery !== shootSummary" class="mt-3 t-body text-neutral-300">{{ shootSummary }}</p>
        </div>

        <div class="mt-7 grid grid-cols-3 gap-3 border-y border-edge py-5">
          <div>
            <p class="t-num text-[22px] font-semibold text-paper">{{ readableCount }}</p>
            <p class="mt-1 text-[11px] text-muted">Shots read</p>
          </div>
          <div>
            <p class="t-num text-[22px] font-semibold text-paper">{{ record.receipt?.scene_count }}</p>
            <p class="mt-1 text-[11px] text-muted">Scenes grouped</p>
          </div>
          <div>
            <p class="t-num text-[22px] font-semibold text-paper">{{ settledCount }}/{{ record.shot_ids?.length }}</p>
            <p class="mt-1 text-[11px] text-muted">Accounted for</p>
          </div>
        </div>

        <p class="mt-5 t-body text-neutral-300">
          {{ isSampleRecord
            ? 'This fixture did not ingest, analyse, group, or settle these Shots.'
            : 'After these Shots arrived, Shoots handled the reading, grouping, record, and next-step decision in the background.' }}
        </p>
        <RouterLink :to="recordTarget" class="btn mt-6 w-full sm:w-auto">
          {{ isSampleRecord ? 'Inspect the sample layout' : 'Open Shoot Record' }}
        </RouterLink>
      </div>

      <div class="surface order-1 overflow-hidden p-3 sm:p-4 lg:order-2">
        <div class="grid h-[340px] grid-cols-[1.05fr_0.95fr] grid-rows-2 gap-2 sm:h-[440px]">
          <img
            v-if="previewMembers[0]"
            :src="thumb(previewMembers[0])"
            alt="First Shot in this Shoot"
            class="row-span-2 h-full w-full rounded-2xl object-cover"
          />
          <img
            v-if="previewMembers[1]"
            :src="thumb(previewMembers[1])"
            alt="Middle Shot in this Shoot"
            class="h-full w-full rounded-2xl object-cover"
          />
          <img
            v-if="previewMembers[2]"
            :src="thumb(previewMembers[2])"
            alt="Last Shot in this Shoot"
            class="h-full w-full rounded-2xl object-cover"
          />
        </div>
      </div>
    </div>

    <div class="mt-5 grid gap-3 sm:grid-cols-2">
      <article v-if="repeated" class="surface-soft p-5">
        <p class="eyebrow">What stayed</p>
        <p class="mt-3 t-body text-neutral-200">{{ repeated }}</p>
      </article>
      <article v-if="varied" class="surface-soft p-5">
        <p class="eyebrow">What varied</p>
        <p class="mt-3 t-body text-neutral-200">{{ varied }}</p>
      </article>
    </div>

    <details class="mt-5 rounded-2xl border border-edge bg-panel">
      <summary class="flex min-h-14 cursor-pointer list-none items-center gap-3 px-5 py-4 t-body text-neutral-200">
        <span>{{ isSampleRecord ? 'What this fixture represents' : 'How Shoots handled this Shoot' }}</span>
        <span class="ml-auto text-muted" aria-hidden="true">+</span>
      </summary>
      <CompanionReceipt
        class="border-x-0 border-b-0"
        :title="isSampleRecord ? 'Sample workflow' : 'Background work'"
        :items="receiptItems"
      />
    </details>

    <div v-if="!hasRecommendation" class="mt-5 flex flex-col gap-3 rounded-2xl border border-edge px-5 py-4 sm:flex-row sm:items-center">
      <div class="min-w-0 flex-1">
        <p class="eyebrow">{{ isSampleRecord ? 'Sample next-step layout' : 'What Shoots suggests' }}</p>
        <p class="mt-2 t-body">{{ scoutCopy }}</p>
      </div>
      <RouterLink v-if="experiment" :to="experimentTarget" class="btn-quiet shrink-0">
        Open optional Experiment
      </RouterLink>
    </div>
  </section>
</template>
