<script>
import { mapActions, mapState } from 'pinia'

import { storyPageFilename } from '@/downloads'
import { useShootsStore } from '@/stores/shoots'

export default {
  name: 'ShotDeconstruction',
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
  <section id="shot-deconstruction" class="surface mt-5 min-w-0 border-accent/25 p-5" aria-labelledby="shot-story-title" :aria-busy="Boolean(phase)">
    <p class="eyebrow text-accent">Your visual story</p>
    <h2 id="shot-story-title" class="mt-2 text-xl font-medium tracking-tight text-paper">Turn this Shot into a story.</h2>
    <p class="mt-2 t-meta">A captioned opening, visual explanations, and your clean Shot at the end. No Keeper mark needed.</p>

    <template v-if="ready">
      <p class="mt-4 t-meta">Gemini-written draft from this Shot's stored reading. Review the words and images before sharing.</p>
      <div class="mt-4 flex snap-x snap-mandatory gap-3 overflow-x-auto pb-3">
        <figure v-for="(page, index) in draft.pages" :key="page.blob_path" class="w-[80%] shrink-0 snap-start">
          <a :href="`/api/blobs/${page.blob_path}`" target="_blank" rel="noreferrer" :aria-label="`Open story image ${index + 1}`">
            <img
              :src="`/api/blobs/${page.blob_path}`"
              :alt="page.kind === 'clean' ? 'Clean Shot, full image without text' : page.title"
              class="aspect-[4/5] w-full rounded-xl border border-edge bg-black object-contain"
            />
          </a>
          <figcaption class="mt-2 t-meta">{{ index + 1 }} / {{ draft.pages.length }} · {{ page.kind === 'clean' ? 'Clean Shot · no text or crop' : page.title }}</figcaption>
          <a
            data-story-page-download
            :href="`/api/blobs/${page.blob_path}`"
            :download="storyPageFilename(draft.id, index)"
            :aria-label="`Download story image ${index + 1}`"
            class="tap-target text-[13px] text-accent"
          >Download image</a>
        </figure>
      </div>
      <div v-if="draft.suggested_caption" class="mt-3 rounded-xl border border-edge bg-black/20 p-4">
        <p class="eyebrow">Caption for the story</p>
        <p class="mt-2 t-body">{{ draft.suggested_caption }}</p>
      </div>
      <button type="button" class="btn mt-4 w-full" :disabled="Boolean(phase) || busy === 'download-deconstruction'" @click="download">
        {{ busy === 'download-deconstruction' ? 'Preparing images…' : 'Download all images' }}
      </button>
      <p class="mt-3 t-meta">Your browser may ask you to allow multiple downloads. Each preview also has its own download link.</p>
      <p class="mt-2 t-meta">The last image keeps its original framing and size. Social apps may crop it; you can post it separately.</p>
    </template>

    <button
      type="button"
      :class="ready ? 'btn-quiet mt-4 w-full' : 'btn mt-4 w-full'"
      :disabled="Boolean(unavailableReason) || Boolean(phase) || busy === 'download-deconstruction'"
      @click="build"
    >
      {{ phase === 'writing' ? 'Preparing your story…' : phase === 'loading' ? 'Checking saved story…' : ready ? 'Rebuild story' : 'Build visual story' }}
    </button>
    <p v-if="phase === 'writing'" class="mt-3 t-meta" role="status">Writing from the stored reading and preparing your images. This may take about a minute. Your original stays unchanged.</p>
    <p v-if="unavailableReason" class="mt-3 t-meta">{{ unavailableReason }}</p>
    <p v-if="storyError" class="mt-3 text-sm text-amber-200" role="alert">{{ storyError }}</p>
    <p v-if="downloadError" class="mt-3 text-sm text-amber-200" role="alert">{{ downloadError }}</p>
    <p v-if="downloadNotice" class="mt-3 t-meta" role="status">{{ downloadNotice }}</p>
  </section>
</template>
