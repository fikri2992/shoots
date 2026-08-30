<script>
import { mapState } from 'pinia'

import VerdictNote from '@/components/VerdictNote.vue'
import { scoutStory, shootSummary } from '@/domain/copy'
import { useShootsStore } from '@/stores/shoots'

/**
 * Nothing to shoot right now. Show the last thing the agent decided and when
 * the next one is due, so the screen still answers "what happened".
 */
export default {
  name: 'IdleStep',
  components: { VerdictNote },
  computed: {
    ...mapState(useShootsStore, ['lastVerdict', 'orderedShots', 'profile', 'mobile']),
    latestRecord() {
      return this.mobile?.latest_shoot_record || null
    },
    scoutCopy() {
      return scoutStory(this.latestRecord?.scout)
    },
    shootSummary() {
      return shootSummary(this.latestRecord?.receipt)
    },
    recordTarget() {
      if (!this.latestRecord) return { name: 'shots' }
      return {
        name: 'shoot-record',
        params: {
          shootId: this.latestRecord.shoot_id,
          revision: this.latestRecord.revision,
        },
      }
    },
    /**
     * One earlier Shot worth looking at again. A Keeper first, because that
     * is the photographer's own verdict; failing that the one the panel
     * corroborated hardest, which is a claim about the evidence. Never the
     * score: no number decides what "your best" means here.
     */
    best() {
      const rank = (v) => [
        v.shot.kept_at ? 1 : 0,
        Math.max(0, ...(v.analysis.techniques || []).map((t) => t.agreement || 0)),
      ]
      return (
        this.orderedShots
          .filter((v) => v.analysis)
          .sort((a, b) => {
            const [ak, ac] = rank(a)
            const [bk, bc] = rank(b)
            return bk - ak || bc - ac
          })[0] || null
      )
    },
    bestThumb() {
      const blobs = this.best?.shot.blobs || {}
      return blobs.thumb ? `/api/blobs/${blobs.thumb}` : ''
    },
  },
}
</script>

<template>
  <section class="page-shell pb-28 pt-8 md:py-12">
    <p class="eyebrow">Now · Quiet</p>
    <div class="mt-6 grid gap-5 lg:grid-cols-[1fr_380px]">
      <div class="surface p-6 sm:p-9">
        <p class="eyebrow text-accent">{{ latestRecord ? 'Your latest outing' : 'Shoots checked your work' }}</p>
        <h1 class="mt-4 max-w-2xl t-hero lg:text-[48px]">
          {{ latestRecord ? 'Your latest outing is ready.' : 'Nothing is asking for your attention.' }}
        </h1>
        <p v-if="latestRecord" class="mt-5 max-w-2xl text-[16px] leading-7 text-neutral-300">
          {{ shootSummary }} {{ scoutCopy }}
        </p>
        <p v-else-if="profile?.keepers" class="mt-5 max-w-2xl text-[16px] leading-7 text-neutral-300">
          Shoots checked your Keepers. No new question was clear enough to interrupt you with.
        </p>
        <p v-else class="mt-5 max-w-2xl text-[16px] leading-7 text-neutral-300">
          Mark a Keeper when a Shot matters to you. Until then, Shoots will not invent an assignment.
        </p>
        <RouterLink :to="recordTarget" class="btn-quiet mt-7 inline-flex">
          {{ latestRecord ? 'Open the outing' : profile?.keepers ? 'Review your Keeper Shots' : 'Mark a Shot you value' }}
        </RouterLink>
      </div>

      <div class="space-y-5">
        <div v-if="lastVerdict" class="surface p-5">
          <p class="eyebrow mb-3">Last Experiment result</p>
          <VerdictNote :verdict="lastVerdict.verdict" :title="lastVerdict.experiment.title" />
        </div>

        <RouterLink
          v-if="best"
          :to="{ name: 'shot', params: { shotId: best.shot.id } }"
          class="surface flex items-center gap-4 p-4 transition hover:border-edge-strong"
        >
          <img v-if="bestThumb" :src="bestThumb" alt="" class="h-20 w-20 rounded-xl object-cover" />
          <span class="min-w-0">
            <span class="eyebrow">{{ best.shot.kept_at ? 'One you kept' : 'One to revisit' }}</span>
            <span class="mt-2 line-clamp-2 block t-body">{{ best.analysis.critique }}</span>
          </span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
