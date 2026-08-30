<script>
import { mapActions, mapState } from 'pinia'

import IdleStep from '@/components/now/IdleStep.vue'
import ExperimentHero from '@/components/now/ExperimentHero.vue'
import ReadingStep from '@/components/now/ReadingStep.vue'
import RunReceipt from '@/components/now/RunReceipt.vue'
import SavedDirectionStep from '@/components/now/SavedDirectionStep.vue'
import ScoutRecommendationStep from '@/components/now/ScoutRecommendationStep.vue'
import SeedStep from '@/components/now/SeedStep.vue'
import ShootCompleteStep from '@/components/now/ShootCompleteStep.vue'
import ShootProcessingStep from '@/components/now/ShootProcessingStep.vue'
import { useShootsStore } from '@/stores/shoots'

/**
 * One screen, one state, one decision. Which state shows is decided by where
 * the user actually is in the loop — never a dashboard of everything at once.
 */
export default {
  name: 'NowPage',
  components: {
    IdleStep,
    ExperimentHero,
    ReadingStep,
    RunReceipt,
    SavedDirectionStep,
    ScoutRecommendationStep,
    SeedStep,
    ShootCompleteStep,
    ShootProcessingStep,
  },
  computed: {
    ...mapState(useShootsStore, ['experiment', 'shots', 'accountReady', 'loading', 'push', 'busy', 'working', 'seeding', 'mobile']),
    scoutRecommendationRecord() {
      const record = this.latestRecord
      if (!record || !['recommend', 'ask'].includes(record.scout?.route)) return null
      const questionId = record.scout.question?.id
      const answered = (this.mobile?.recent_scout_answers || []).some(
        (answer) => questionId && answer.question_id === questionId,
      )
      const intervention = (this.mobile?.recent_interventions || []).find(
        (item) => item.shoot_id === record.shoot_id && Number(item.shoot_revision) === Number(record.revision),
      )
      const resolved = intervention?.experiment_id || ['accepted', 'entered', 'left', 'completed'].includes(intervention?.attempt_state)
      return answered || resolved ? null : record
    },
    latestRecord() {
      const record = this.mobile?.latest_shoot_record
      const shoot = this.currentShoot
      if (!record) return null
      if (!shoot) return record
      return shoot.status === 'settled' &&
        record.shoot_id === shoot.id &&
        Number(record.revision) === Number(shoot.current_record_revision)
        ? record
        : null
    },
    currentShoot() {
      return this.mobile?.latest_shoot || null
    },
    currentShootMembers() {
      const ids = new Set(this.currentShoot?.ordered_shot_ids || [])
      return this.shots.filter((view) => ids.has(view.shot.id))
    },
    currentShootNeedsAttention() {
      if (!this.currentShoot) return false
      return this.currentShoot.status !== 'settled' || !this.latestRecord
    },
    savedDirection() {
      if (this.experiment) return null
      return (this.mobile?.experiment_directions || []).find(
        (direction) => direction.state === 'saved',
      ) || null
    },
    experimentFocused() {
      return this.$route.query.focus === 'experiment'
    },
    step() {
      if (this.loading && !this.shots.length && !this.accountReady) return 'loading'
      if (!this.accountReady) return 'loading'
      if (this.seeding || (!this.shots.length && !this.experiment)) return 'seed'
      if (this.currentShootNeedsAttention) return 'shoot-processing'
      if (this.working.length) return 'reading'
      if (this.experimentFocused && this.experiment) return 'experiment'
      if (this.latestRecord) return 'complete'
      if (this.scoutRecommendationRecord) return 'recommendation'
      if (this.savedDirection) return 'direction'
      if (this.experiment) return 'experiment'
      return 'idle'
    },
  },
  created() {
    this.checkPush()
  },
  methods: {
    ...mapActions(useShootsStore, ['checkPush', 'enablePush']),
  },
}
</script>

<template>
  <div class="pb-24 md:pb-10">
    <SeedStep v-if="step === 'seed'" />
    <ShootProcessingStep
      v-else-if="step === 'shoot-processing'"
      :shoot="currentShoot"
      :members="currentShootMembers"
    />
    <ReadingStep v-else-if="step === 'reading'" :shots="working" />
    <SavedDirectionStep v-else-if="step === 'direction'" :direction="savedDirection" />
    <template v-else-if="step === 'complete'">
      <ShootCompleteStep
        :record="latestRecord"
        :experiment="experiment"
        :has-recommendation="Boolean(scoutRecommendationRecord)"
      />
      <ScoutRecommendationStep
        v-if="scoutRecommendationRecord"
        :record="scoutRecommendationRecord"
        :members="currentShootMembers"
        :busy="busy"
      />
      <SavedDirectionStep v-else-if="savedDirection" :direction="savedDirection" />
    </template>
    <ExperimentHero v-else-if="step === 'experiment'" :experiment="experiment" />
    <ScoutRecommendationStep
      v-else-if="step === 'recommendation'"
      :record="scoutRecommendationRecord"
      :members="currentShootMembers"
      :busy="busy"
    />
    <IdleStep v-else-if="step === 'idle'" />
    <p v-else class="page-shell pt-12 t-meta">Loading your Journey…</p>

    <RunReceipt v-if="shots.length && step !== 'complete'" />

    <div v-if="push === 'off' && experiment" class="page-shell mt-5">
      <button
        type="button"
        class="flex w-full items-center gap-3 rounded-2xl border border-edge bg-panel px-4 py-3 text-left lg:max-w-md"
        :disabled="busy === 'push'"
        @click="enablePush"
      >
        <span class="h-2 w-2 rounded-full bg-accent" />
        <span class="t-body text-neutral-300">
          {{ busy === 'push' ? 'Asking your browser…' : 'Let it buzz your phone when the light is right' }}
        </span>
        <span class="ml-auto t-meta text-accent">Turn on</span>
      </button>
    </div>
  </div>
</template>
