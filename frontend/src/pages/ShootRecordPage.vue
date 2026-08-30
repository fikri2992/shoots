<script>
import { mapActions, mapState } from 'pinia'

import CompanionReceipt from '@/components/CompanionReceipt.vue'
import { humanizeLegacyText, scoutStory, shootSummary } from '@/domain/copy'
import { useShootsStore } from '@/stores/shoots'

const SETTLED_RUNS = new Set(['completed', 'terminal'])
const SCOUT_LABELS = {
  explain: 'Explained',
  ask: 'Asked',
  recommend: 'Recommended',
  explore: 'Explore offered',
  reproduce: 'Reproduce offered',
  silence: 'Stayed silent',
}

export default {
  name: 'ShootRecordPage',
  components: { CompanionReceipt },
  props: {
    shootId: { type: String, required: true },
    revision: { type: [String, Number], required: true },
  },
  data() {
    return {
      auditOpen: false,
      loadingMembers: false,
      keepingIds: [],
    }
  },
  computed: {
    ...mapState(useShootsStore, ['loading', 'mobile', 'shotById', 'me']),
    isSampleRecord() {
      return this.me?.record_mode === 'sample'
    },
    record() {
      const record = this.mobile?.latest_shoot_record
      if (!record) return null
      if (record.shoot_id !== this.shootId || String(record.revision) !== String(this.revision)) return null
      return record
    },
    recordShoot() {
      const shoot = this.mobile?.latest_shoot
      return shoot?.id === this.record?.shoot_id ? shoot : null
    },
    receipt() {
      return this.record?.receipt || {}
    },
    scoutCopy() {
      if (this.isSampleRecord) return 'Hand-authored Scout layout. It is not a model decision.'
      return scoutStory(this.record?.scout)
    },
    shootSummary() {
      return shootSummary(this.receipt)
    },
    repeatedCopy() {
      return (this.receipt.repeated || []).map(humanizeLegacyText)
    },
    variedCopy() {
      return (this.receipt.varied || []).map(humanizeLegacyText)
    },
    blindSpotCopy() {
      return (this.receipt.blind_spots || []).map(humanizeLegacyText)
    },
    title() {
      const captured = new Date(this.recordShoot?.started_at || '')
      if (!Number.isNaN(captured.getTime())) {
        return captured.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })
      }
      const settled = new Date(this.record?.settled_at || '')
      if (Number.isNaN(settled.getTime())) return 'Settled Shoot'
      return settled.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })
    },
    settledRuns() {
      return Object.values(this.record?.run_outcomes || {}).filter((status) => SETTLED_RUNS.has(status)).length
    },
    readableCount() {
      return this.receipt.readable_shot_count ??
        Math.max(0, (this.record?.shot_ids?.length || 0) - (this.record?.unreadable_shot_ids?.length || 0))
    },
    memberRows() {
      return (this.record?.shot_ids || []).map((id, index) => ({
        id,
        index,
        view: this.shotById(id),
      }))
    },
    previewRows() {
      const rows = this.memberRows.filter((row) => row.view)
      if (rows.length <= 3) return rows
      const middle = Math.floor((rows.length - 1) / 2)
      return [rows[0], rows[middle], rows[rows.length - 1]]
    },
    keeperRows() {
      return this.memberRows.filter((row) => row.view?.shot?.kept_at)
    },
    scoutAnswer() {
      const questionId = this.record?.scout?.question?.id
      if (!questionId) return null
      return (this.mobile?.recent_scout_answers || []).find(
        (answer) => answer.question_id === questionId,
      ) || null
    },
    scoutIntervention() {
      return (this.mobile?.recent_interventions || []).find(
        (item) => item.shoot_id === this.record?.shoot_id && Number(item.shoot_revision) === Number(this.record?.revision),
      ) || null
    },
    choiceText() {
      const bits = []
      if (this.scoutAnswer) {
        const option = this.record.scout.question.options?.find(
          (item) => item.id === this.scoutAnswer.option_id,
        )
        bits.push(
          option?.technique_id
            ? `You said "${option.label}" was the choice you were exploring.`
            : 'You said you were just shooting, so Shoots left the meaning open.',
        )
      }
      if (this.scoutIntervention?.attempt_state === 'accepted') {
        bits.push('You accepted the recommended Experiment. The Camera has not started yet.')
      } else if (this.scoutIntervention?.attempt_state === 'left') {
        bits.push('You left the recommendation for today.')
      }
      if (this.keeperRows.length) {
        bits.push(
          `${this.keeperRows.length} member ${this.keeperRows.length === 1 ? 'Shot is' : 'Shots are'} marked as ${this.keeperRows.length === 1 ? 'a Keeper' : 'Keepers'}.`,
        )
      }
      return bits.join(' ') || 'No Keeper mark or Experiment choice was required.'
    },
    choiceEffect() {
      if (this.isSampleRecord) return 'Sample only. No user action or background result was recorded.'
      if (this.scoutAnswer) {
        return this.scoutAnswer.detail || 'Shoots will use that answer for this Shoot only.'
      }
      if (this.scoutIntervention && this.scoutIntervention.attempt_state !== 'offered') {
        return this.scoutIntervention.outcome_reason
      }
      if (this.keeperRows.length) {
        return 'Those Keeper marks now tell Shoots which Shots mattered to you. The outing itself did not change.'
      }
      return 'Shoots finished the background work without asking you to start an Experiment.'
    },
    memoryEffect() {
      const rejected = (this.record?.scout?.rejected_routes || []).find(
        (item) => item.route === 'reproduce' && /deprioriti|unchanged outcomes/i.test(item.reason || ''),
      )
      if (!rejected) return ''
      const counts = new Map()
      for (const item of this.mobile?.recent_interventions || []) {
        if (
          item.technique_id &&
          item.attempt_state === 'completed' &&
          item.observable_outcome === 'unchanged' &&
          (!item.comparability || item.comparability === 'comparable')
        ) {
          counts.set(item.technique_id, (counts.get(item.technique_id) || 0) + 1)
        }
      }
      const evidence = [...counts.entries()]
        .filter(([, count]) => count >= 2)
        .map(([techniqueId, count]) => `${count} comparable ${techniqueId.replace(/_/g, ' ')} outcomes stayed unchanged`)
      return evidence.length ? `${evidence.join('; ')}. ${rejected.reason}` : rejected.reason
    },
    receiptItems() {
      const count = this.receipt.shot_count || this.record?.shot_ids?.length || 0
      const scenes = this.receipt.scene_count || 0
      if (this.isSampleRecord) {
        return [
          {
            label: 'Sample layout',
            text: `${count} Shot cards and ${scenes} Scene groups were hand-authored to test this page.`,
            state: 'limit',
          },
          {
            label: 'Agents',
            text: 'No agents ran. The stored steps and timings are fixture copy.',
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
      const unreadable = this.record?.unreadable_shot_ids?.length || 0
      const handled = unreadable
        ? `Shoots accounted for all ${count} Shots, read ${this.readableCount}, and recorded ${unreadable} as unreadable.`
        : `Shoots accounted for all ${count} Shots and read ${this.readableCount} across ${scenes} ${scenes === 1 ? 'Scene' : 'Scenes'}.`
      const next = ['recommend', 'ask'].includes(this.record?.scout?.route) &&
        !this.scoutAnswer && this.scoutIntervention?.attempt_state === 'offered'
        ? scoutStory(this.record.scout)
        : scoutStory(this.record?.scout)
      const items = [
        {
          label: 'Shoots handled',
          text: handled,
          state: 'done',
        },
        {
          label: 'You decided',
          text: this.choiceText,
          state: this.scoutAnswer || ['accepted', 'entered', 'left', 'completed'].includes(this.scoutIntervention?.attempt_state) || this.keeperRows.length ? 'done' : 'waiting',
        },
        {
          label: 'The result',
          text: this.choiceEffect,
          state: this.scoutAnswer || ['accepted', 'entered', 'left', 'completed'].includes(this.scoutIntervention?.attempt_state) || this.keeperRows.length ? 'done' : 'limit',
        },
        { label: 'Next', text: next, state: 'current' },
      ]
      if (this.memoryEffect) {
        items.push({ label: 'What Shoots remembered', text: this.memoryEffect, state: 'done' })
      }
      return items
    },
    scoutLabel() {
      const route = this.record?.scout?.route || 'silence'
      return SCOUT_LABELS[route] || route.replace(/_/g, ' ')
    },
    primaryDiscovery() {
      return this.repeatedCopy[0] || this.variedCopy[0] || this.shootSummary
    },
    settledLabel() {
      const settled = new Date(this.record?.settled_at || '')
      if (Number.isNaN(settled.getTime())) return 'Settlement time unavailable'
      return settled.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
    },
  },
  watch: {
    record: {
      immediate: true,
      async handler(record) {
        if (record) await this.ensureMembers(record)
      },
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['fetchShot', 'setKeeper']),
    async ensureMembers(record) {
      const missing = record.shot_ids.filter((id) => !this.shotById(id))
      if (!missing.length) return
      this.loadingMembers = true
      try {
        for (const id of missing) await this.fetchShot(id)
      } finally {
        this.loadingMembers = false
      }
    },
    thumb(view) {
      const blobs = view?.shot?.blobs || {}
      const path = blobs.thumb || blobs.original || ''
      return path ? `/api/blobs/${path}` : ''
    },
    capturedLabel(view) {
      const captured = new Date(view?.shot?.captured_at || view?.shot?.ingested_at || '')
      if (Number.isNaN(captured.getTime())) return 'Open Shot'
      return captured.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    },
    shotTarget(row) {
      return {
        name: 'shot',
        params: { shotId: row.id },
        query: {
          from: 'shoot',
          shootId: this.record.shoot_id,
          revision: this.record.revision,
        },
      }
    },
    async toggleKeeper(row) {
      if (this.keepingIds.includes(row.id)) return
      this.keepingIds.push(row.id)
      try {
        await this.setKeeper(row.id, !row.view.shot.kept_at)
      } finally {
        this.keepingIds = this.keepingIds.filter((id) => id !== row.id)
      }
    },
  },
}
</script>

<template>
  <div class="page-shell pb-24 pt-6 md:pb-12 md:pt-8">
    <p v-if="loading && !mobile" class="surface mx-auto max-w-[760px] p-6 t-body" aria-live="polite">
      Loading the Shoot Record…
    </p>

    <section v-else-if="!record" class="surface mx-auto max-w-[760px] p-6 sm:p-8" role="alert">
      <p class="eyebrow text-bad">This outing changed</p>
      <h1 class="mt-3 t-title">A newer version is available.</h1>
      <p class="mt-3 t-body">Shoots found another Camera Shot or a later correction.</p>
      <RouterLink :to="{ name: 'now' }" class="btn-quiet mt-5">Return to Now</RouterLink>
    </section>

    <div v-else class="mx-auto max-w-[760px]">
      <header class="flex items-center gap-3 border-b border-edge pb-5">
        <RouterLink :to="{ name: 'now' }" class="tap-target text-paper" aria-label="Back to Now">
          <svg aria-hidden="true" viewBox="0 0 24 24" class="h-6 w-6 fill-none stroke-current stroke-2">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </RouterLink>
        <div class="min-w-0 flex-1">
          <p class="eyebrow text-accent">{{ isSampleRecord ? 'Sample Shoot Record layout' : 'Your Shoot · ready' }}</p>
          <h1 class="mt-2 text-[24px] leading-7 font-semibold tracking-[-0.03em] text-paper">{{ title }}</h1>
        </div>
        <span class="flex h-10 w-10 items-center justify-center rounded-full border border-neutral-700 text-neutral-300" :aria-label="isSampleRecord ? 'Fixture' : 'Settled'">
          <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-2">
            <path d="m5 12 4 4L19 6" />
          </svg>
        </span>
      </header>

      <section class="mt-6 overflow-hidden rounded-[22px] border border-edge bg-panel p-2">
        <div class="grid h-[300px] grid-cols-[1.05fr_0.95fr] grid-rows-2 gap-2 sm:h-[390px]">
          <img
            v-if="previewRows[0]"
            :src="thumb(previewRows[0].view)"
            :alt="previewRows[0].view.shot.filename"
            class="row-span-2 h-full w-full rounded-2xl object-cover"
          />
          <img
            v-if="previewRows[1]"
            :src="thumb(previewRows[1].view)"
            :alt="previewRows[1].view.shot.filename"
            class="h-full w-full rounded-2xl object-cover"
          />
          <img
            v-if="previewRows[2]"
            :src="thumb(previewRows[2].view)"
            :alt="previewRows[2].view.shot.filename"
            class="h-full w-full rounded-2xl object-cover"
          />
        </div>
      </section>

      <section class="mt-6 rounded-[22px] border border-neutral-700 bg-[linear-gradient(145deg,rgba(255,255,255,0.055),rgba(255,255,255,0.015))] p-5 sm:p-7">
        <p class="eyebrow text-accent">{{ isSampleRecord ? 'Hand-authored example' : 'One thing worth noticing' }}</p>
        <h2 class="mt-3 text-[23px] font-medium leading-8 tracking-[-0.025em] text-paper">
          {{ primaryDiscovery }}
        </h2>
        <p v-if="primaryDiscovery !== shootSummary" class="mt-3 t-body text-neutral-300">{{ shootSummary }}</p>

        <div class="mt-6 grid grid-cols-3 gap-3 border-y border-edge py-5">
          <div>
            <p class="t-num text-[23px] font-semibold text-paper">{{ receipt.shot_count }}</p>
            <p class="mt-1 text-[11px] text-muted">{{ isSampleRecord ? 'Shot cards' : 'Shots read' }}</p>
          </div>
          <div>
            <p class="t-num text-[23px] font-semibold text-paper">{{ receipt.scene_count }}</p>
            <p class="mt-1 text-[11px] text-muted">{{ isSampleRecord ? 'Scene groups' : 'Scenes grouped' }}</p>
          </div>
          <div>
            <p class="t-num text-[23px] font-semibold text-paper">{{ settledRuns }}/{{ receipt.shot_count }}</p>
            <p class="mt-1 text-[11px] text-muted">{{ isSampleRecord ? 'Run layouts' : 'Accounted for' }}</p>
          </div>
        </div>

        <div class="mt-6 grid gap-3 sm:grid-cols-2">
          <article v-if="repeatedCopy.length" class="rounded-2xl border border-edge bg-panel-2/55 p-4">
            <p class="eyebrow">What stayed</p>
            <ul class="mt-3 space-y-2">
              <li v-for="item in repeatedCopy" :key="item" class="t-body text-neutral-200">{{ item }}</li>
            </ul>
          </article>
          <article v-if="variedCopy.length" class="rounded-2xl border border-edge bg-panel-2/55 p-4">
            <p class="eyebrow">What varied</p>
            <ul class="mt-3 space-y-2">
              <li v-for="item in variedCopy" :key="item" class="t-body text-neutral-200">{{ item }}</li>
            </ul>
          </article>
        </div>

        <div class="mt-5 rounded-2xl border border-edge px-4 py-4">
          <p class="eyebrow">{{ isSampleRecord ? 'What this sample represents' : 'Why Shoots stopped here' }}</p>
          <p class="mt-2 t-body text-neutral-300">{{ scoutCopy }}</p>
          <p class="mt-3 t-meta">
            {{ isSampleRecord
              ? 'No ingestion, Analysis, grouping, settlement, or Scout decision happened.'
              : 'After the Shots arrived, Shoots finished this record without requiring a Keeper mark or Experiment.' }}
          </p>
        </div>

        <button
          type="button"
          class="btn-quiet mt-5 w-full"
          :aria-expanded="auditOpen"
          @click="auditOpen = !auditOpen"
        >
          {{ auditOpen
            ? (isSampleRecord ? 'Hide sample workflow layout' : 'Hide how the job finished')
            : (isSampleRecord ? 'See sample workflow layout' : 'See how the job finished') }}
        </button>

        <div v-if="auditOpen" class="mt-5 space-y-5 border-t border-edge pt-5">
          <p v-if="isSampleRecord" class="t-body text-neutral-300">
            This page depicts four workflow stages. None of them ran for this fixture.
          </p>
          <ol v-else class="grid gap-3 sm:grid-cols-2">
            <li class="flex gap-3 rounded-xl bg-panel-2/55 p-4">
              <span class="text-accent">01</span>
              <span><strong class="block text-sm text-paper">Collected</strong><span class="mt-1 block t-meta">Accepted every Shot in the Shoot.</span></span>
            </li>
            <li class="flex gap-3 rounded-xl bg-panel-2/55 p-4">
              <span class="text-accent">02</span>
              <span><strong class="block text-sm text-paper">Read</strong><span class="mt-1 block t-meta">Stored Evidence for {{ receipt.readable_shot_count }} Shots.</span></span>
            </li>
            <li class="flex gap-3 rounded-xl bg-panel-2/55 p-4">
              <span class="text-accent">03</span>
              <span><strong class="block text-sm text-paper">Grouped</strong><span class="mt-1 block t-meta">Preserved {{ receipt.scene_count }} natural Scenes.</span></span>
            </li>
            <li class="flex gap-3 rounded-xl bg-panel-2/55 p-4">
              <span class="text-accent">04</span>
              <span><strong class="block text-sm text-paper">Settled</strong><span class="mt-1 block t-meta">Recorded every member outcome and Scout decision.</span></span>
            </li>
          </ol>
          <section v-if="blindSpotCopy.length">
            <p class="eyebrow">What this record cannot prove</p>
            <ul class="mt-2 space-y-2">
              <li v-for="item in blindSpotCopy" :key="item" class="t-meta">{{ item }}</li>
            </ul>
          </section>
          <p v-if="!isSampleRecord" class="t-meta">
            {{ settledLabel }} · revision {{ record.revision }} · Scout {{ scoutLabel.toLocaleLowerCase() }}
          </p>
        </div>
      </section>

      <details class="mt-6 rounded-2xl border border-edge bg-panel">
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

      <section class="mt-8">
        <p class="eyebrow">Shots from this Shoot</p>
        <h2 class="mt-2 text-[19px] font-semibold tracking-[-0.02em] text-paper">Open any Shot for a closer look.</h2>
        <p class="mt-2 text-[13px] leading-5 text-muted">
          {{ isSampleRecord ? 'Open a Shot to inspect the sample layout. Actions are disabled.' : 'Use the bookmark when one matters to you.' }}
        </p>

        <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          <template v-for="row in memberRows" :key="row.id">
            <article
              v-if="row.view"
              class="group relative overflow-hidden rounded-2xl border transition hover:border-edge-strong focus-within:border-edge-strong"
              :class="row.view.shot.kept_at ? 'border-accent' : 'border-edge'"
            >
              <RouterLink :to="shotTarget(row)" class="block text-left focus-visible:outline-none">
                <div class="aspect-[4/5] bg-panel-2">
                  <img
                    v-if="thumb(row.view)"
                    :src="thumb(row.view)"
                    :alt="row.view.shot.filename"
                    class="h-full w-full object-cover transition duration-500 group-hover:scale-[1.02]"
                  />
                  <div v-else class="flex h-full items-center justify-center t-meta">No preview</div>
                </div>
                <span class="block border-t border-edge bg-panel px-3 py-2.5">
                  <span class="block truncate text-[12px] font-medium text-paper">Shot {{ row.index + 1 }}</span>
                  <span class="mt-0.5 block text-[10px] text-muted">
                    {{ row.view.shot.kept_at ? 'Keeper · yours' : capturedLabel(row.view) }}
                  </span>
                </span>
              </RouterLink>
              <button
                v-if="!isSampleRecord"
                type="button"
                class="absolute right-2 top-2 flex h-11 w-11 items-center justify-center rounded-full border backdrop-blur"
                :class="row.view.shot.kept_at ? 'border-accent bg-accent text-ink' : 'border-white/20 bg-black/55 text-white'"
                :disabled="keepingIds.includes(row.id)"
                :aria-label="row.view.shot.kept_at ? `Remove ${row.view.shot.filename} from Keepers` : `Mark ${row.view.shot.filename} as Keeper`"
                :aria-pressed="Boolean(row.view.shot.kept_at)"
                @click="toggleKeeper(row)"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  class="h-4 w-4 stroke-current stroke-2"
                  :class="row.view.shot.kept_at ? 'fill-current' : 'fill-none'"
                >
                  <path d="M6 3h12v18l-6-4-6 4z" />
                </svg>
              </button>
            </article>

            <div v-else class="aspect-[4/5] animate-pulse rounded-2xl border border-edge bg-panel" aria-hidden="true" />
          </template>
        </div>
        <p v-if="loadingMembers" class="mt-3 t-meta" aria-live="polite">Loading every member Shot…</p>
      </section>
    </div>
  </div>
</template>
