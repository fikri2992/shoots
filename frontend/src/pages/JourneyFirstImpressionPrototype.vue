<script>
// Three photo-first Journey openings, switchable via ?variant=, on the existing /journey route.
import { mapActions, mapState } from 'pinia'

import JourneyPrototypeSwitcher from '@/pages/JourneyPrototypeSwitcher.vue'
import JourneyPrototypeVariantA from '@/pages/JourneyPrototypeVariantA.vue'
import JourneyPrototypeVariantB from '@/pages/JourneyPrototypeVariantB.vue'
import JourneyPrototypeVariantC from '@/pages/JourneyPrototypeVariantC.vue'
import { useShootsStore } from '@/stores/shoots'

const VARIANTS = [
  {
    key: 'A',
    name: 'Photo essay',
    idea: 'Recognition first. One large Shot carries the personal result, with the autonomous receipt beside it.',
    risk: 'The Taskmaster chain is compact, so technical judges may open the Evidence sooner.',
  },
  {
    key: 'B',
    name: 'Task receipt',
    idea: 'The completed multi-step job is the hero, supported by a contact sheet of the real Shoot.',
    risk: 'The workflow is clearest here, but it feels more operational than intimate.',
  },
  {
    key: 'C',
    name: 'Visual story',
    idea: 'The finished visual story is the first reward, with the Shoot receipt kept close enough to prove it.',
    risk: 'This is the most shareable direction, but it depends on a prepared story and a Photographer-chosen opening Shot.',
  },
]

const SETTLED_RUNS = new Set(['completed', 'terminal'])

function clean(text) {
  return String(text || '').replace(/\s+/g, ' ').trim()
}

function sentence(text) {
  return clean(text).replace(/[.!?]+$/, '')
}

export default {
  name: 'JourneyFirstImpressionPrototype',
  components: {
    JourneyPrototypeSwitcher,
    JourneyPrototypeVariantA,
    JourneyPrototypeVariantB,
    JourneyPrototypeVariantC,
  },
  props: {
    variant: { type: String, required: true },
    record: { type: Object, default: null },
    profile: { type: Object, default: null },
    shots: { type: Array, default: () => [] },
    latestSentences: { type: Array, default: () => [] },
    receiptItems: { type: Array, default: () => [] },
    deconstruction: { type: Object, default: null },
    experiment: { type: Object, default: null },
    reproduce: { type: Object, default: null },
  },
  data() {
    return {
      variants: VARIANTS,
      notice: '',
    }
  },
  computed: {
    ...mapState(useShootsStore, ['busy']),
    currentVariant() {
      return this.variants.find((item) => item.key === this.variant) || this.variants[0]
    },
    currentComponent() {
      return {
        A: JourneyPrototypeVariantA,
        B: JourneyPrototypeVariantB,
        C: JourneyPrototypeVariantC,
      }[this.currentVariant.key]
    },
    story() {
      const receipt = this.record?.receipt || {}
      const shotCount = receipt.shot_count || this.record?.shot_ids?.length || this.profile?.shots || 0
      const sceneCount = receipt.scene_count || this.profile?.scenes || 0
      const settledCount = Object.values(this.record?.run_outcomes || {}).filter((state) => SETTLED_RUNS.has(state)).length
      const readableCount = receipt.readable_shot_count || shotCount
      const memberIds = new Set(this.record?.shot_ids || [])
      const views = this.shots.filter((item) => !memberIds.size || memberIds.has(item.shot?.id))
      const sourceViews = views.length ? views : this.shots
      const normalizedShots = sourceViews.slice(0, 7).map((item) => this.normalizeShot(item)).filter(Boolean)
      const cover = normalizedShots.find((item) => item.keeper) || normalizedShots[0] || null
      const repeated = clean(receipt.repeated?.[0])
      const topTechnique = [...(receipt.techniques || [])]
        .sort((a, b) => (b.corroborated_shot_ids?.length || 0) - (a.corroborated_shot_ids?.length || 0))[0]
      const headline = topTechnique?.corroborated_shot_ids?.length
        ? `${sentence(topTechnique.name || topTechnique.technique_id?.replace(/_/g, ' '))} keeps appearing in this Shoot.`
        : sentence(repeated || this.latestSentences[0] || receipt.summary || 'Your latest Shoot is ready')
      const summary = clean(receipt.summary || this.latestSentences[1] || 'Shoots is building a checkable record from your Camera activity.')
      const resultSummary = this.receiptItems.find((item) => item.label === 'What happened')?.text ||
        'The result and its limits remain attached to the record.'
      const storyReady = this.deconstruction?.status === 'drafted'
      const pages = storyReady
        ? (this.deconstruction.pages || []).map((page, index) => ({
            id: page.blob_path || `page-${index}`,
            url: this.blobUrl(page.blob_path),
            alt: page.title || `Story page ${index + 1}`,
            title: page.title || `Page ${index + 1}`,
          }))
        : []
      const storyPages = pages.length
        ? pages
        : normalizedShots.slice(0, 3).map((shot, index) => ({ ...shot, title: index === 0 ? 'Cover preview' : `Evidence page ${index + 1}` }))
      const accounted = settledCount || shotCount
      const nextAction = this.experiment
        ? `${sentence(this.experiment.title || 'One Experiment')} is open. It is optional and unrelated Shots remain free.`
        : this.receiptItems.find((item) => item.label === 'What happens next')?.text ||
          'Keep shooting normally. Shoots waits for enough Evidence before offering another Experiment.'

      return {
        statusLabel: this.record ? 'Shoot complete' : this.profile?.shots ? 'Your record is growing' : 'Waiting for your Shots',
        dateLabel: this.dateLabel(this.record?.settled_at),
        shotCount,
        sceneCount,
        readableCount,
        settledCount: accounted,
        accountedLabel: `${accounted}/${shotCount || accounted}`,
        headline,
        summary,
        resultSummary,
        nextAction,
        cover,
        shots: normalizedShots,
        storyReady,
        downloading: this.busy === 'download-deconstruction',
        storyPages,
        artifactStatus: storyReady
          ? 'Visual story ready'
          : this.deconstruction?.status === 'needs_cover'
            ? 'Opening Shot needed'
            : 'Shoot Record ready',
        recordTarget: this.record
          ? { name: 'shoot-record', params: { shootId: this.record.shoot_id, revision: this.record.revision } }
          : null,
        workflow: [
          { label: 'Received', value: shotCount, detail: 'Camera Shots' },
          { label: 'Read', value: readableCount, detail: 'Evidence stored' },
          { label: 'Grouped', value: sceneCount, detail: 'natural Scenes' },
          { label: 'Accounted', value: `${accounted}/${shotCount || accounted}`, detail: 'Run outcomes' },
          { label: 'Prepared', value: storyReady ? 1 : '—', detail: storyReady ? 'visual story' : 'record only' },
        ],
      }
    },
    stateLine() {
      return [
        this.story.statusLabel,
        `${this.story.shotCount} Shots`,
        `${this.story.sceneCount} Scenes`,
        `${this.story.accountedLabel} accounted`,
        this.story.artifactStatus,
      ].join(' · ')
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['downloadDeconstructionPages']),
    blobUrl(path) {
      return path ? `/api/blobs/${path}` : ''
    },
    normalizeShot(item) {
      const shot = item?.shot || item
      const path = shot?.blobs?.thumb || shot?.blobs?.original
      if (!shot?.id || !path) return null
      return {
        id: shot.id,
        url: this.blobUrl(path),
        alt: shot.filename || 'Shot from the latest Shoot',
        keeper: Boolean(shot.kept_at),
      }
    },
    dateLabel(value) {
      const date = new Date(value || '')
      if (Number.isNaN(date.getTime())) return 'Latest record'
      return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
    },
    selectVariant(key) {
      this.notice = ''
      this.$router.replace({ query: { ...this.$route.query, variant: key } })
    },
    scrollTo(id) {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    },
    openStory() {
      this.scrollTo('journey-deconstruction')
    },
    openEvidence() {
      this.scrollTo('journey-evidence')
    },
    async download() {
      this.notice = ''
      if (this.story.storyReady && this.deconstruction?.id) {
        const count = await this.downloadDeconstructionPages(this.deconstruction)
        if (count) this.notice = `${count} image downloads requested. Check your browser's downloads.`
        return
      }
      this.notice = 'This Shoot does not have a finished visual story yet.'
    },
  },
}
</script>

<template>
  <div>
    <component
      :is="currentComponent"
      :story="story"
      @download="download"
      @open-story="openStory"
      @open-evidence="openEvidence"
    />

    <p v-if="notice" class="mt-4 rounded-xl border border-accent/35 bg-accent/10 px-4 py-3 text-[12px] leading-5 text-neutral-200" role="status">
      {{ notice }}
    </p>

    <aside class="mt-4 flex flex-col justify-between gap-3 border-t border-dashed border-edge-strong pt-4 sm:flex-row sm:items-start" aria-label="Prototype state">
      <div>
        <p class="eyebrow">Prototype state · {{ currentVariant.key }}</p>
        <p class="mt-1 text-[12px] leading-5 text-neutral-300">{{ stateLine }}</p>
      </div>
      <div class="max-w-xl sm:text-right">
        <p class="text-[12px] leading-5 text-neutral-300">{{ currentVariant.idea }}</p>
        <p class="mt-1 text-[11px] leading-4 text-muted">Risk: {{ currentVariant.risk }}</p>
      </div>
    </aside>

    <JourneyPrototypeSwitcher :variants="variants" :current="currentVariant.key" @select="selectVariant" />
  </div>
</template>
