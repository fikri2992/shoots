<script>
import { mapState } from 'pinia'

import StatusChip from '@/components/StatusChip.vue'
import { useShootsStore } from '@/stores/shoots'

/** The timeline: every shot, newest first, with the Analyst's one-line read. */
export default {
  name: 'ShotsPage',
  components: { StatusChip },
  computed: {
    ...mapState(useShootsStore, ['shots']),
    rows() {
      return this.shots.map((v) => ({
        id: v.shot.id,
        shot: v.shot,
        analysis: v.analysis,
        thumb: v.shot.blobs?.thumb ? `/api/blobs/${v.shot.blobs.thumb}` : '',
        when: new Date(v.shot.captured_at || v.shot.ingested_at).toLocaleDateString(),
        tags: (v.analysis?.techniques || []).slice(0, 3).map((t) => t.technique_id.replace(/_/g, ' ')),
      }))
    },
  },
}
</script>

<template>
  <div class="mx-auto max-w-3xl p-4 pb-24 md:pb-8">
    <h1 class="mb-3 text-sm font-semibold">Shots</h1>
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <RouterLink
        v-for="r in rows"
        :key="r.id"
        :to="{ name: 'shot', params: { shotId: r.id } }"
        class="group overflow-hidden rounded-xl border border-edge bg-panel"
      >
        <div class="relative aspect-square bg-black">
          <img v-if="r.thumb" :src="r.thumb" alt="" class="h-full w-full object-cover" loading="lazy" />
          <span
            v-if="r.analysis"
            class="absolute right-1.5 top-1.5 rounded-md bg-black/70 px-1.5 py-0.5 font-mono text-[11px] text-neutral-100"
          >
            {{ r.analysis.score }}/10
          </span>
          <span
            v-if="r.shot.kind === 'video'"
            class="absolute left-1.5 top-1.5 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] uppercase text-neutral-200"
          >
            video
          </span>
        </div>
        <div class="p-2">
          <div class="flex items-center justify-between gap-2">
            <span class="truncate text-[11px] text-neutral-400">{{ r.when }}</span>
            <StatusChip v-if="r.shot.status !== 'analyzed'" :status="r.shot.status" />
          </div>
          <p class="mt-1 truncate text-xs text-neutral-300">
            {{ r.tags.join(' · ') || (r.analysis ? 'no technique tagged' : '…') }}
          </p>
        </div>
      </RouterLink>
    </div>
    <p v-if="!rows.length" class="py-10 text-center text-sm text-neutral-500">No shots yet.</p>
  </div>
</template>
