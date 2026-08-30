<script>
import { mapActions, mapState } from 'pinia'

import DriveImportPanel from '@/components/DriveImportPanel.vue'
import { useShootsStore } from '@/stores/shoots'

function ago(iso) {
  const minutes = Math.round((Date.now() - new Date(iso)) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  return days < 8 ? `${days} d ago` : new Date(iso).toLocaleDateString()
}

function dayKey(iso) {
  if (!iso) return 'unknown'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'unknown'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function dayLabel(key) {
  if (key === 'unknown') return 'Date unavailable'
  const date = new Date(`${key}T12:00:00`)
  const today = new Date()
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const delta = Math.round((start - new Date(date.getFullYear(), date.getMonth(), date.getDate())) / 86400000)
  if (delta === 0) return 'Today'
  if (delta === 1) return 'Yesterday'
  return date.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: date.getFullYear() === today.getFullYear() ? undefined : 'numeric' })
}

/** Everything the agent has read, newest first. The image is the row. */
export default {
  name: 'ShotsPage',
  components: { DriveImportPanel },
  computed: {
    ...mapState(useShootsStore, ['orderedShots', 'inspirations', 'seeding', 'me', 'mobile']),
    isSampleRecord() {
      return this.me?.record_mode === 'sample'
    },
    rows() {
      return this.orderedShots.map((v) => ({
        id: v.shot.id,
        name: v.shot.filename,
        kept: Boolean(v.shot.kept_at),
        video: v.shot.kind === 'video',
        pending: !v.analysis && v.shot.status !== 'failed',
        failed: v.shot.status === 'failed',
        readable: Boolean(v.analysis),
        at: v.shot.captured_at || v.shot.ingested_at,
        when: ago(v.shot.captured_at || v.shot.ingested_at),
        thumb: v.shot.blobs?.thumb ? `/api/blobs/${v.shot.blobs.thumb}` : '',
      }))
    },
    groups() {
      const latestShoot = this.mobile?.latest_shoot
      const latestIds = new Set(latestShoot?.ordered_shot_ids || [])
      const byId = new Map(this.rows.map((row) => [row.id, row]))
      const latestItems = (latestShoot?.ordered_shot_ids || []).map((id) => byId.get(id)).filter(Boolean)
      const buckets = new Map()
      const rows = this.rows
        .filter((row) => !latestIds.has(row.id))
        .sort((a, b) => (b.at || '').localeCompare(a.at || ''))
      for (const row of rows) {
        const key = dayKey(row.at)
        if (!buckets.has(key)) buckets.set(key, [])
        buckets.get(key).push(row)
      }
      const earlier = [...buckets].map(([key, items]) => ({
        key: `date-${key}`,
        kind: 'date',
        label: dayLabel(key),
        items,
      }))
      if (!latestItems.length) return earlier
      const record = this.mobile?.latest_shoot_record
      const recordReady = latestShoot.status === 'settled' &&
        record?.shoot_id === latestShoot.id &&
        Number(record.revision) === Number(latestShoot.current_record_revision)
      const status = recordReady
        ? 'Ready'
        : latestShoot.status === 'open'
          ? 'Keeping together'
          : latestShoot.status === 'closing'
            ? 'Finishing'
            : 'Preparing record'
      return [{
        key: `shoot-${latestShoot.id}`,
        kind: 'shoot',
        label: dayLabel(dayKey(latestShoot.started_at || latestItems[0]?.at)),
        status,
        items: latestItems,
        recordTarget: recordReady
          ? { name: 'shoot-record', params: { shootId: record.shoot_id, revision: record.revision } }
          : null,
      }, ...earlier]
    },
    summary() {
      return {
        total: this.rows.length,
        read: this.rows.filter((row) => row.readable).length,
        kept: this.rows.filter((row) => row.kept).length,
      }
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['seed', 'restoreInspiration']),
    onPick(event, sourceRole) {
      const files = [...(event.target.files || [])]
      event.target.value = ''
      if (files.length) this.seed(files, sourceRole)
    },
    inspirationThumb(item) {
      if (item.blobs?.thumb) return `/api/blobs/${item.blobs.thumb}`
      return item.blobs?.original ? `/api/blobs/${item.blobs.original}` : ''
    },
  },
}
</script>

<template>
  <div class="page-shell pb-24 pt-8 md:pb-12 md:pt-10">
    <header class="flex flex-wrap items-end justify-between gap-5">
      <div>
        <p class="eyebrow">Archive</p>
        <h1 class="mt-2 t-hero">Shots</h1>
        <p v-if="rows.length" class="mt-3 t-meta">
          {{ isSampleRecord
            ? `${summary.total} sample Shot cards · ${summary.read} hand-authored reads`
            : `${summary.total} made · ${summary.read} readable · ${summary.kept} marked Keeper` }}
        </p>
      </div>
      <div v-if="!isSampleRecord" class="flex gap-2">
        <label class="btn-quiet cursor-pointer px-4">
          {{ seeding ? `Adding ${seeding.done + 1}/${seeding.total}…` : 'Add my Shots' }}
          <input type="file" accept="image/*,video/*" multiple class="hidden" :disabled="Boolean(seeding)" @change="onPick($event, 'mine')" />
        </label>
        <label class="btn-quiet cursor-pointer px-4">
          Add Inspiration
          <input type="file" accept="image/*,video/*" multiple class="hidden" :disabled="Boolean(seeding)" @change="onPick($event, 'inspiration')" />
        </label>
      </div>
      <span v-else class="rounded-full border border-edge px-3 py-2 text-[11px] text-muted">Sample · actions disabled</span>
    </header>

    <DriveImportPanel v-if="!groups.length && !isSampleRecord" />

    <div v-if="groups.length" class="mt-9 space-y-10">
      <section
        v-for="group in groups"
        :key="group.key"
        :class="group.kind === 'shoot' ? 'rounded-[22px] border border-edge bg-panel p-4 sm:p-5' : ''"
      >
        <div class="mb-4 flex items-end justify-between gap-4 border-b border-edge pb-3">
          <div>
            <p v-if="group.kind === 'shoot'" class="eyebrow text-accent">Latest Shoot · {{ group.status }}</p>
            <h2 :class="group.kind === 'shoot' ? 'mt-2 t-title' : 't-title'">{{ group.label }}</h2>
          </div>
          <div class="shrink-0 text-right">
            <span class="block t-meta">{{ group.items.length }} Shot{{ group.items.length === 1 ? '' : 's' }}</span>
            <RouterLink v-if="group.recordTarget" :to="group.recordTarget" class="mt-2 inline-flex text-[12px] font-medium text-accent hover:text-paper">
              Open Shoot Record
            </RouterLink>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 lg:gap-3">
          <RouterLink
            v-for="r in group.items"
            :key="r.id"
            :to="{ name: 'shot', params: { shotId: r.id } }"
            class="group relative aspect-[4/5] overflow-hidden rounded-xl border bg-panel transition hover:-translate-y-0.5 hover:border-edge-strong"
            :class="r.kept ? 'border-accent/65' : 'border-edge'"
          >
            <img v-if="r.thumb" :src="r.thumb" :alt="r.name" class="h-full w-full object-cover transition duration-500 group-hover:scale-[1.02]" loading="lazy" />
            <div v-else class="flex h-full items-center justify-center t-meta">No preview</div>

            <span v-if="r.video" class="absolute left-2 top-2 rounded-lg bg-black/72 px-2 py-1 text-[10px] text-paper">VIDEO</span>
            <span v-if="r.kept" class="absolute right-2 top-2 rounded-lg bg-ink/85 px-2 py-1 text-[10px] font-semibold tracking-wide text-accent">
              KEEPER
            </span>

            <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/45 to-transparent px-3 pb-3 pt-10">
              <p v-if="r.failed" class="text-[11px] text-bad">Could not read this Shot</p>
              <p v-else-if="r.pending" class="text-[11px] text-accent">Reading now…</p>
              <p v-else class="text-[11px] text-neutral-300">{{ r.when }}</p>
            </div>
          </RouterLink>
        </div>
      </section>
    </div>

    <section v-if="inspirations.length" class="mt-12 border-t border-edge pt-7">
      <p class="eyebrow text-accent">Inspiration</p>
      <h2 class="mt-2 t-title">References, not your record</h2>
      <p class="mt-2 t-meta">Shoots may help you study these, but never counts them as your work.</p>
      <div class="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 lg:gap-3">
        <article v-for="item in inspirations" :key="item.id" class="overflow-hidden rounded-xl border border-edge bg-panel">
          <div class="aspect-[4/5] bg-panel-2">
            <img v-if="inspirationThumb(item)" :src="inspirationThumb(item)" :alt="item.filename" class="h-full w-full object-cover" />
          </div>
          <div class="p-3">
            <p class="truncate t-meta">{{ item.filename }}</p>
            <button v-if="!isSampleRecord" type="button" class="mt-2 text-[11px] font-medium text-accent" @click="restoreInspiration(item.id)">
              This is my Shot
            </button>
          </div>
        </article>
      </div>
    </section>

    <DriveImportPanel v-if="groups.length && !isSampleRecord" class="mt-12" />

    <section v-if="!groups.length && !inspirations.length" class="surface mt-10 p-7 text-center sm:p-10">
      <p class="eyebrow text-accent">No archive yet</p>
      <h2 class="mt-3 text-2xl font-semibold text-paper">Your first pattern needs more than a prompt.</h2>
      <p class="mx-auto mt-3 max-w-md t-body">Add a few Shots. Shoots will preserve what it can read and say nothing about what it cannot.</p>
    </section>
  </div>
</template>
