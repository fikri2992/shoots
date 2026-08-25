<script>
import { mapActions, mapState } from 'pinia'

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

/** Everything the agent has read, newest first. The image is the row. */
export default {
  name: 'FramesPage',
  computed: {
    ...mapState(useShootsStore, ['frames', 'seeding']),
    rows() {
      return this.frames.map((v) => ({
        id: v.shot.id,
        kept: Boolean(v.shot.kept_at),
        video: v.shot.kind === 'video',
        pending: !v.analysis && v.shot.status !== 'failed',
        failed: v.shot.status === 'failed',
        when: ago(v.shot.ingested_at),
        thumb: v.shot.blobs?.thumb ? `/api/blobs/${v.shot.blobs.thumb}` : '',
      }))
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['seed']),
    onPick(event) {
      const files = [...(event.target.files || [])]
      event.target.value = ''
      if (files.length) this.seed(files)
    },
  },
}
</script>

<template>
  <div class="mx-auto w-full max-w-4xl pb-24 md:pb-10">
    <header class="gutter flex items-baseline justify-between pt-8">
      <h1 class="t-hero">Frames</h1>
      <label class="cursor-pointer t-meta hover:text-neutral-200">
        {{ seeding ? `Uploading ${seeding.done + 1}/${seeding.total}…` : 'Add frames ▸' }}
        <input type="file" accept="image/*,video/*" multiple class="hidden" :disabled="Boolean(seeding)" @change="onPick" />
      </label>
    </header>

    <div class="mt-6 grid grid-cols-2 gap-1 sm:grid-cols-3 md:gap-2">
      <RouterLink
        v-for="r in rows"
        :key="r.id"
        :to="{ name: 'frame', params: { shotId: r.id } }"
        class="relative aspect-square overflow-hidden bg-panel md:rounded-lg"
      >
        <img v-if="r.thumb" :src="r.thumb" alt="" class="h-full w-full object-cover" loading="lazy" />
        <span
          v-if="r.kept"
          class="absolute right-2 top-2 rounded-md bg-black/70 px-1.5 py-0.5 t-num text-[11px] text-accent"
          title="One you kept"
        >
          kept
        </span>
        <span v-if="r.video" class="absolute left-2 top-2 rounded-md bg-black/70 px-1.5 py-0.5 t-num text-[10px] text-neutral-300">
          video
        </span>
        <span
          v-if="r.pending || r.failed"
          class="absolute inset-x-0 bottom-0 bg-black/70 px-2 py-1 t-meta"
          :class="r.failed ? 'text-bad' : 'text-accent'"
        >
          {{ r.failed ? 'could not read it' : 'reading…' }}
        </span>
        <span v-else class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent px-2 pb-1 pt-6 t-meta">
          {{ r.when }}
        </span>
      </RouterLink>
    </div>

    <p v-if="!rows.length" class="gutter pt-16 t-body text-neutral-500">
      Nothing here yet. Add a few photos and the agent will read them.
    </p>
  </div>
</template>
