<script>
import { mapActions } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

export default {
  name: 'ScoutRecommendationStep',
  props: {
    record: { type: Object, required: true },
    members: { type: Array, default: () => [] },
    busy: { type: String, default: '' },
  },
  data() {
    return {
      optionIndex: 0,
      tuneOpen: false,
    }
  },
  computed: {
    options() {
      const stored = this.record.scout?.recommendation?.options || []
      if (stored.length) return stored
      return (this.record.scout?.question?.options || [])
        .filter((option) => option.technique_id)
        .map((option) => {
          const warrant = (this.record.scout.warrant || []).find(
            (item) => item.technique_id === option.technique_id,
          )
          const count = new Set(warrant?.shot_ids || []).size
          return {
            id: `explore_${option.technique_id}`,
            technique_id: option.technique_id,
            technique_name: option.label,
            experiment_type: 'explore',
            title: `Try ${option.label} on purpose`,
            why_now: `${count} ${count === 1 ? 'Shot' : 'Shots'} in this Shoot showed ${option.label}. Try using that choice on purpose in a different Scene.`,
            warrant_shot_ids: warrant?.shot_ids || [],
            reference_shot_id: warrant?.reference_shot_id || '',
          }
        })
        .sort((a, b) => b.warrant_shot_ids.length - a.warrant_shot_ids.length || a.technique_id.localeCompare(b.technique_id))
    },
    option() {
      return this.options[this.optionIndex] || null
    },
    evidence() {
      const ids = [this.option?.reference_shot_id, ...(this.option?.warrant_shot_ids || [])].filter(Boolean)
      return [...new Set(ids)]
        .map((id) => this.members.find((member) => member.shot.id === id))
        .filter((member) => this.thumb(member))
        .slice(0, 3)
    },
    evidenceCount() {
      return new Set(this.option?.warrant_shot_ids || []).size
    },
    typeLabel() {
      return this.option?.experiment_type === 'reproduce' ? 'Reproduce' : 'Explore'
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['respondToScoutRecommendation']),
    thumb(view) {
      const blobs = view?.shot?.blobs || {}
      const path = blobs.thumb || blobs.original || ''
      return path ? `/api/blobs/${path}` : ''
    },
    shotTarget(view) {
      return {
        name: 'shot',
        params: { shotId: view.shot.id },
        query: { from: 'now' },
      }
    },
    another() {
      this.optionIndex = (this.optionIndex + 1) % this.options.length
      this.tuneOpen = false
    },
    async respond(action) {
      const result = await this.respondToScoutRecommendation(
        this.record.shoot_id,
        this.record.revision,
        action,
        action === 'accept' ? this.option.id : '',
      )
      if (result?.experiment) {
        await this.$router.replace({ name: 'now', query: { focus: 'experiment' } })
      }
    },
  },
}
</script>

<template>
  <section v-if="option" class="page-shell pt-8 md:pt-12">
    <div class="overflow-hidden rounded-[28px] border border-edge bg-panel shadow-2xl shadow-black/20">
      <div class="grid lg:grid-cols-[1.08fr_0.92fr]">
        <div class="relative min-h-[330px] bg-ink sm:min-h-[460px] lg:min-h-[640px]">
          <RouterLink
            v-if="evidence[0]"
            :to="shotTarget(evidence[0])"
            class="group absolute inset-0 block"
            :aria-label="`Open supporting Shot for ${option.technique_name}`"
          >
            <img
              :src="thumb(evidence[0])"
              :alt="`A supporting Shot where ${option.technique_name} appeared`"
              class="h-full w-full object-cover transition duration-300 group-hover:scale-[1.01]"
            />
            <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent px-5 pb-5 pt-20 sm:px-7 sm:pb-7">
              <p class="text-sm text-white/90">
                Open supporting Shot
                <span class="ml-2 text-white/60">1 of {{ evidenceCount }}</span>
              </p>
            </div>
          </RouterLink>
          <div v-else class="absolute inset-0 flex items-center justify-center px-8 text-center t-meta">
            Supporting Shot unavailable
          </div>

          <div v-if="evidence.length > 1" class="absolute left-4 top-4 flex gap-2 sm:left-6 sm:top-6">
            <RouterLink
              v-for="view in evidence.slice(1)"
              :key="view.shot.id"
              :to="shotTarget(view)"
              class="h-16 w-16 overflow-hidden rounded-xl border border-white/30 bg-black/50 shadow-lg sm:h-20 sm:w-20"
            >
              <img :src="thumb(view)" alt="Another supporting Shot" class="h-full w-full object-cover" />
            </RouterLink>
          </div>
        </div>

        <div class="flex flex-col justify-between p-6 sm:p-9 lg:p-11">
          <div>
            <div class="flex flex-wrap items-center justify-between gap-3">
              <p class="eyebrow text-accent">One idea for your next outing</p>
              <span class="rounded-full border border-edge px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-neutral-400">
                {{ typeLabel }} · optional
              </span>
            </div>
            <h1 class="mt-6 font-serif text-[38px] leading-[1.02] text-paper sm:text-[50px] lg:text-[52px]">
              {{ option.title }}
            </h1>
            <p class="mt-6 text-[17px] leading-7 text-neutral-200">{{ option.why_now }}</p>

            <div class="mt-8 rounded-[18px] border border-edge bg-panel-2/70 p-5">
              <p class="eyebrow">Why Shoots chose this</p>
              <p class="mt-3 text-[15px] leading-6 text-neutral-300">
                It appeared clearly in {{ evidenceCount }} {{ evidenceCount === 1 ? 'Shot' : 'Shots' }}.
                This is a recommendation, not a claim about what you intended.
              </p>
            </div>
          </div>

          <div class="mt-10 border-t border-edge pt-7">
            <button
              type="button"
              class="btn w-full justify-center"
              :disabled="busy === 'scout-recommendation'"
              data-recommendation-action="accept"
              @click="respond('accept')"
            >
              {{ busy === 'scout-recommendation' ? 'Preparing…' : 'Try this Experiment' }}
            </button>
            <button
              v-if="options.length > 1"
              type="button"
              class="btn-quiet mt-3 w-full justify-center"
              data-recommendation-action="another"
              @click="another"
            >
              Show another idea
            </button>
            <button
              type="button"
              class="mt-4 w-full py-2 text-sm text-neutral-400 hover:text-paper"
              :disabled="busy === 'scout-recommendation'"
              data-recommendation-action="not-today"
              @click="respond('not_today')"
            >
              Not today
            </button>

            <div class="mt-5 border-t border-edge pt-5">
              <button type="button" class="text-sm text-neutral-400 hover:text-paper" @click="tuneOpen = !tuneOpen">
                {{ tuneOpen ? 'Close' : 'Help Shoots understand' }}
              </button>
              <div v-if="tuneOpen" class="mt-4 rounded-[16px] bg-panel-2/70 p-4">
                <p class="text-sm leading-6 text-neutral-300">Only answer if it helps. You do not need to classify your Shoot.</p>
                <button
                  type="button"
                  class="btn-quiet mt-3 w-full justify-center"
                  :disabled="busy === 'scout-recommendation'"
                  data-recommendation-action="just-shooting"
                  @click="respond('just_shooting')"
                >
                  I was just shooting
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
