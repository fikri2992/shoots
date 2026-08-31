<script>
import { mapActions, mapState } from 'pinia'

import DisclosureRow from '@/components/DisclosureRow.vue'
import { storyPageFilename } from '@/downloads'
import { useShootsStore } from '@/stores/shoots'

export default {
  name: 'ShotDeconstruction',
  components: { DisclosureRow },
  props: {
    shot: { type: Object, required: true },
    analysis: { type: Object, default: null },
    readOnly: { type: Boolean, default: false },
  },
  data() {
    return { downloadNotice: '', downloadError: '' }
  },
  computed: {
    ...mapState(useShootsStore, ['shotDeconstructions', 'shotStoryBusy', 'shotStoryErrors', 'busy', 'error']),
    draft() {
      return this.shotDeconstructions[this.shot.id] || null
    },
    phase() {
      return this.shotStoryBusy[this.shot.id] || ''
    },
    storyError() {
      return this.shotStoryErrors[this.shot.id] || this.draft?.error || ''
    },
    ready() {
      return this.draft?.status === 'drafted' && this.draft.pages?.length > 0
    },
    unavailableReason() {
      if (this.readOnly) return 'Sample layout only. No visual story can be created here.'
      if (this.shot.kind === 'video') return 'Visual stories currently support still Shots only.'
      if (!this.analysis || this.analysis.abstained) return 'Available once this Shot has a usable visual reading.'
      if (!this.shot.blobs?.original) return 'The original Shot is needed to build a visual story.'
      return ''
    },
    loadKey() {
      return !this.readOnly && this.shot.kind === 'photo' ? this.shot.id : ''
    },
  },
  watch: {
    loadKey: {
      immediate: true,
      handler(id) {
        this.downloadNotice = ''
        this.downloadError = ''
        if (id) this.fetchShotDeconstruction(id)
      },
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['fetchShotDeconstruction', 'prepareShotDeconstruction', 'downloadDeconstructionPages']),
    storyPageFilename,
    build() {
      if (this.unavailableReason || this.phase) return
      this.downloadNotice = ''
      this.downloadError = ''
      return this.prepareShotDeconstruction(this.shot.id)
    },
    async download() {
      const shotId = this.shot.id
      this.downloadNotice = ''
      this.downloadError = ''
      const count = await this.downloadDeconstructionPages(this.draft)
      if (this.shot.id !== shotId) return
      if (count) this.downloadNotice = `Requested ${count} image downloads. Check your browser downloads.`
      else this.downloadError = this.error || 'The images could not be downloaded. Please try again.'
    },
  },
}
</script>

<template>
  <DisclosureRow
    id="shot-deconstruction"
    :key="shot.id"
    class="mt-3 min-w-0 border-t border-edge"
    :label="phase === 'writing' ? 'Preparing visual story…' : ready ? 'Visual story' : 'Create visual story'"
    :count="storyError ? 'Needs attention' : ready ? `${draft.pages.length} images` : ''"
  >
    <p class="t-meta">
      {{ ready ? 'Gemini-written draft. Review before sharing; tap any preview to see it full size.' : 'Captioned pages and a clean ending from this Shot. No Keeper needed.' }}
    </p>

    <template v-if="ready">
      <div class="mt-3 flex snap-x snap-mandatory gap-2 overflow-x-auto pb-2">
        <figure v-for="(page, index) in draft.pages" :key="page.blob_path" class="w-32 shrink-0 snap-start">
          <a :href="`/api/blobs/${page.blob_path}`" target="_blank" rel="noreferrer" :aria-label="`Open story image ${index + 1}`">
            <img
              :src="`/api/blobs/${page.blob_path}`"
              :alt="page.kind === 'clean' ? 'Clean Shot, full image without text' : page.title"
              class="aspect-[4/5] w-full rounded-lg border border-edge bg-black object-contain"
            />
          </a>
          <figcaption class="flex items-center gap-1 text-[11px] text-muted">
            <span class="min-w-0 flex-1 truncate" :title="page.kind === 'clean' ? 'Clean Shot · no text or crop' : page.title">
              {{ index + 1 }} · {{ page.kind === 'clean' ? 'Clean Shot' : page.title }}
            </span>
            <a
              data-story-page-download
              :href="`/api/blobs/${page.blob_path}`"
              :download="storyPageFilename(draft.id, index)"
              :aria-label="`Download story image ${index + 1}`"
              class="tap-target shrink-0 justify-center text-accent hover:text-paper"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-2">
                <path d="M12 3v12m-5-5 5 5 5-5M5 17v4h14v-4" />
              </svg>
            </a>
          </figcaption>
        </figure>
      </div>
      <details v-if="draft.suggested_caption" class="border-y border-edge">
        <summary class="min-h-11 cursor-pointer py-3 text-[12px] text-muted hover:text-paper">Caption</summary>
        <p class="pb-3 text-[13px] leading-5 text-neutral-300">{{ draft.suggested_caption }}</p>
      </details>
    </template>

    <div class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
      <button v-if="ready" type="button" class="btn-quiet min-h-11 rounded-lg px-3 py-2 text-[12px]" :disabled="Boolean(phase) || busy === 'download-deconstruction'" @click="download">
        {{ busy === 'download-deconstruction' ? 'Preparing images…' : 'Download all images' }}
      </button>
      <button
        type="button"
        :class="ready ? 'tap-target text-[12px] text-muted hover:text-paper disabled:opacity-40' : 'btn min-h-11 rounded-lg px-3 py-2 text-[12px]'"
        :disabled="Boolean(unavailableReason) || Boolean(phase) || busy === 'download-deconstruction'"
        @click="build"
      >
        {{ phase === 'writing' ? 'Preparing your story…' : phase === 'loading' ? 'Checking saved story…' : ready ? 'Rebuild story' : 'Build visual story' }}
      </button>
    </div>
    <details v-if="ready" class="mt-1">
      <summary class="min-h-11 cursor-pointer py-3 text-[11px] text-muted hover:text-paper">Download help</summary>
      <p class="t-meta">Allow multiple downloads if asked, or use the download icon below each preview. The clean ending keeps its original size and framing; social apps may crop it.</p>
    </details>
    <p v-if="phase === 'writing'" class="mt-2 t-meta" role="status">Preparing your images. This may take about a minute. Your original stays unchanged.</p>
    <p v-if="unavailableReason" class="mt-3 t-meta">{{ unavailableReason }}</p>
    <p v-if="storyError" class="mt-3 text-sm text-amber-200" role="alert">{{ storyError }}</p>
    <p v-if="downloadError" class="mt-3 text-sm text-amber-200" role="alert">{{ downloadError }}</p>
    <p v-if="downloadNotice" class="mt-3 t-meta" role="status">{{ downloadNotice }}</p>
  </DisclosureRow>
</template>
