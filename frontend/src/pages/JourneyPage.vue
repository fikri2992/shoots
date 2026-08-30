<script>
import { mapActions, mapState } from 'pinia'

import AgentLog from '@/components/AgentLog.vue'
import CompanionReceipt from '@/components/CompanionReceipt.vue'
import ConnectStep from '@/components/now/ConnectStep.vue'
import DisclosureRow from '@/components/DisclosureRow.vue'
import ExperimentRecord from '@/components/ExperimentRecord.vue'
import ReproduceProof from '@/components/ReproduceProof.vue'
import TechniqueMap from '@/components/TechniqueMap.vue'
import TendencyProfile from '@/components/TendencyProfile.vue'
import { humanizeLegacyText, repeatabilitySummary, resultSummary, scoutStory, shootSummary } from '@/domain/copy'
import JourneyFirstImpressionPrototype from '@/pages/JourneyFirstImpressionPrototype.vue'
import { useAuthStore } from '@/stores/auth'
import { useShootsStore } from '@/stores/shoots'

function displayLanguage(text) {
  return humanizeLegacyText(text)
    .replace(/\bhabits\b/gi, 'Tendencies')
    .replace(/\bhabit\b/gi, 'Tendency')
    .replace(/\bphotos\b/gi, 'Shots')
    .replace(/\bphoto\b/gi, 'Shot')
    .replace(/\bquests?\b/gi, 'Experiment')
}

function techniqueLabel(id) {
  if (!id) return 'the offered Technique'
  return id.replace(/_/g, ' ').replace(/^./, (letter) => letter.toLocaleUpperCase())
}

/** The longitudinal answer first; distributions and execution logs second. */
export default {
  name: 'JourneyPage',
  components: { AgentLog, CompanionReceipt, ConnectStep, DisclosureRow, ExperimentRecord, JourneyFirstImpressionPrototype, ReproduceProof, TechniqueMap, TendencyProfile },
  data() {
    return { selectedCover: '' }
  },
  computed: {
    ...mapState(useShootsStore, [
      'pastExperiments',
      'experiment',
      'me',
      'push',
      'busy',
      'driveConnected',
      'events',
      'pairCode',
      'journey',
      'orderedShots',
      'profile',
      'techniques',
      'mobile',
    ]),
    latest() {
      return this.journey[0] || null
    },
    isSampleRecord() {
      return this.me?.record_mode === 'sample'
    },
    journeyPrototypeVariant() {
      if (!import.meta.env.DEV) return ''
      const requested = String(this.$route?.query?.variant || '').toUpperCase()
      return ['A', 'B', 'C'].includes(requested) ? requested : ''
    },
    latestSentences() {
      if (this.isSampleRecord && this.latest) {
        return [
          'This hand-authored example uses one visual thread across 10 sample Shot cards.',
          'It shows where a real Journey Update would explain what stayed and what varied.',
          'It is not evidence about a Photographer.',
        ]
      }
      const body = displayLanguage(this.latest?.body)
      return body.match(/[^.!?]+[.!?]+|[^.!?]+$/g)?.map((sentence) => sentence.trim()).filter(Boolean) || []
    },
    latestEvidence() {
      return (this.latest?.evidence || [])
        .map(displayLanguage)
        .filter((line) => !/do not speak about taste/i.test(line))
    },
    recurring() {
      return [...this.techniques]
        .filter((technique) => technique.status === 'recurring')
        .sort((a, b) => b.corroborated - a.corroborated || b.attempts - a.attempts)
        .slice(0, 4)
    },
    tendencies() {
      const total = (dimension) => dimension.buckets.reduce((sum, bucket) => sum + bucket.count, 0)
      return [...(this.profile?.dimensions || [])]
        .filter((dimension) => dimension.readable && dimension.narrow && total(dimension) > 0 && dimension.dominant)
        .sort((a, b) => a.exploration - b.exploration)
        .slice(0, 3)
        .map((dimension) => {
          const bucket = dimension.buckets.find((item) => item.bucket === dimension.dominant)
          return {
            id: dimension.id,
            label: dimension.label,
            dominant: dimension.dominant,
            count: bucket?.count || 0,
            keepers: bucket?.keepers || 0,
            total: total(dimension),
            readableKeepers: dimension.readable_keepers,
            source: dimension.source,
          }
        })
    },
    keeperSignals() {
      if (!this.profile?.taste_is_known) return []
      return [...(this.profile.dimensions || [])]
        .filter((dimension) => dimension.readable_keepers >= this.tasteThreshold)
        .map((dimension) => {
          const bucket = [...dimension.buckets]
            .filter((item) => item.keepers > 0)
            .sort((a, b) => b.keepers - a.keepers)[0]
          if (!bucket) return null
          return {
            id: dimension.id,
            label: dimension.label,
            dominant: bucket.bucket,
            keepers: bucket.keepers,
            readableKeepers: dimension.readable_keepers,
          }
        })
        .filter(Boolean)
        .sort((a, b) =>
          b.keepers / b.readableKeepers - a.keepers / a.readableKeepers ||
          b.readableKeepers - a.readableKeepers ||
          a.label.localeCompare(b.label),
        )
        .slice(0, 3)
    },
    tasteThreshold() {
      return this.profile?.taste_threshold || 5
    },
    keepersNeeded() {
      return Math.max(0, this.tasteThreshold - (this.profile?.keepers || 0))
    },
    knownFacts() {
      if (!this.profile?.shots) return []
      const facts = [`${this.profile.shots} readable Shot${this.profile.shots === 1 ? '' : 's'} are in the record.`]
      if (this.profile.keepers) {
        facts.push(
          `${this.profile.keepers} marked Keeper${this.profile.keepers === 1 ? '' : 's'} are direct positive signals from you.`,
        )
      }
      if (this.profile.scenes) {
        facts.push(
          `${this.profile.scenes} grouped Scene${this.profile.scenes === 1 ? '' : 's'} preserve how those Shots happened together.`,
        )
      }
      const tendency = this.tendencies[0]
      if (tendency) {
        facts.push(
          `${tendency.count} of ${tendency.total} readable Shots share ${tendency.dominant} in ${tendency.label.toLocaleLowerCase()}.`,
        )
      }
      return facts.slice(0, 3)
    },
    nextEvidenceAction() {
      if (!this.profile?.taste_is_known) {
        return 'Keep shooting. If a Shot matters to you, mark it as a Keeper. Leaving it unmarked says nothing.'
      }
      return 'Keep shooting. Shoots will add a Journey Update when something changes enough to be worth saying.'
    },
    latestChange() {
      return [...this.pastExperiments]
        .filter((experiment) => experiment.change)
        .sort((a, b) => (b.closed_at || b.issued_at || '').localeCompare(a.closed_at || a.issued_at || ''))[0] || null
    },
    latestIntervention() {
      return this.mobile?.recent_interventions?.[0] || null
    },
    latestDirection() {
      return [...(this.mobile?.experiment_directions || [])]
        .sort((a, b) => (b.updated_at || b.created_at || '').localeCompare(a.updated_at || a.created_at || ''))[0] || null
    },
    latestScoutAnswer() {
      return [...(this.mobile?.recent_scout_answers || [])]
        .sort((a, b) => (b.answered_at || '').localeCompare(a.answered_at || ''))[0] || null
    },
    photographerAction() {
      const candidates = []
      if (this.latestScoutAnswer) {
        const technique = techniqueLabel(this.latestScoutAnswer.technique_id)
        candidates.push({
          at: this.latestScoutAnswer.answered_at || '',
          text: this.latestScoutAnswer.technique_id
            ? `You said ${technique} was the choice you were exploring.`
            : 'You said you were just shooting, so Shoots left the meaning open.',
        })
      }
      if (this.latestDirection) {
        const text = {
          saved: `You saved "${this.latestDirection.question}" for later.`,
          started: `You turned your saved ${this.latestDirection.technique_name || techniqueLabel(this.latestDirection.technique_id)} question into an Experiment.`,
          left: `You left the saved ${this.latestDirection.technique_name || techniqueLabel(this.latestDirection.technique_id)} question.`,
        }[this.latestDirection.state]
        if (text) candidates.push({ at: this.latestDirection.updated_at || this.latestDirection.created_at || '', text })
      }
      if (
        this.latestIntervention &&
        ['accepted', 'entered', 'completed', 'left'].includes(this.latestIntervention.attempt_state)
      ) {
        const action = {
          accepted: 'You accepted the optional Experiment. The Camera has not started yet.',
          entered: 'You chose to try the optional Experiment.',
          completed: this.latestIntervention.result_shot_ids?.length
            ? `You completed an Experiment with ${this.latestIntervention.result_shot_ids.length} result ${this.latestIntervention.result_shot_ids.length === 1 ? 'Shot' : 'Shots'}.`
            : 'You completed the offered action.',
          left: 'You left the optional Experiment. Shoots made no claim about why.',
        }[this.latestIntervention.attempt_state]
        candidates.push({ at: this.latestIntervention.updated_at || '', text: action })
      }
      const latest = candidates.sort((a, b) => b.at.localeCompare(a.at))[0]
      if (latest) return { text: latest.text, state: 'done' }
      if (this.profile?.keepers) {
        return {
          text: `${this.profile.keepers} Keeper ${this.profile.keepers === 1 ? 'mark tells' : 'marks tell'} Shoots which Shots matter to you.`,
          state: 'done',
        }
      }
      return { text: 'No Keeper mark or Experiment choice was required.', state: 'waiting' }
    },
    resultReceipt() {
      const intervention = this.latestIntervention
      if (intervention?.result_shot_ids?.length) {
        const results = intervention.result_shot_ids.length
        const bits = [`${results} result ${results === 1 ? 'Shot' : 'Shots'}`]
        bits.push(`${intervention.criteria_met_results || 0} matched every check`)
        if (intervention.abstentions) bits.push(`${intervention.abstentions} could not be checked`)
        const change = intervention.change_state === 'insufficient evidence'
          ? 'There are not enough comparable Shots to say what changed.'
          : intervention.change_state
            ? `The newer Shots are ${intervention.change_state}.`
            : 'It is too early to compare the newer Shots.'
        return { text: `${bits.join(' · ')}. ${change}`, state: 'done' }
      }
      if (intervention?.attempt_state === 'completed') {
        return {
          text: intervention.outcome_reason || 'The action completed, but no comparable Change is available.',
          state: intervention.observable_outcome === 'insufficient_evidence' ? 'limit' : 'done',
        }
      }
      if (this.latestReproduce?.result_shot_ids?.length) {
        return {
          text: `${this.latestReproduce.result_shot_ids.length} result ${this.latestReproduce.result_shot_ids.length === 1 ? 'Shot is' : 'Shots are'} here. One try is too early to call a lasting Change.`,
          state: 'done',
        }
      }
      return { text: 'No Experiment result yet.', state: 'waiting' }
    },
    memoryEffect() {
      const rejected = (this.latestShootRecord?.scout?.rejected_routes || []).find(
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
        .map(([techniqueId, count]) => `${count} comparable ${techniqueLabel(techniqueId)} outcomes stayed unchanged`)
      return evidence.length
        ? `${evidence.join('; ')}. Scout did not offer that Technique automatically in this Shoot.`
        : rejected.reason
    },
    journeyReceiptItems() {
      const record = this.latestShootRecord
      if (this.isSampleRecord) {
        const shots = record?.receipt?.shot_count || record?.shot_ids?.length || this.profile?.shots || 0
        const scenes = record?.receipt?.scene_count || this.profile?.scenes || 0
        return [
          { label: 'Fixture data', text: `${shots} Shot cards and ${scenes} Scene groups were hand-authored for this layout.`, state: 'done' },
          { label: 'Agents', text: 'No agents ran. The reads, patterns, and story text are fixture copy.', state: 'waiting' },
          { label: 'Actions', text: 'Keeper marks, Experiments, story building, and connection changes are disabled.', state: 'waiting' },
          { label: 'Use', text: 'Judge the Journey layout only, not a completed photography workflow.', state: 'current' },
        ]
      }
      const sceneCount = record?.receipt?.scene_count || 0
      const handled = record
        ? `Shoots read ${record.receipt?.shot_count || record.shot_ids?.length || 0} Shots and grouped them into ${sceneCount} ${sceneCount === 1 ? 'Scene' : 'Scenes'}.`
        : this.profile?.shots
          ? `Shoots has ${this.profile.shots} readable Shots and is waiting for an outing to finish.`
          : 'Shoots is waiting for your first Shots.'
      let next = this.nextEvidenceAction
      if (this.experiment) {
        const type = { reproduce: 'Reproduce', explore: 'Explore', compare: 'Compare' }[
          this.experiment.type
        ] || ''
        next = `An optional ${type ? `${type} ` : ''}Experiment is ready. Try it only if it fits today.`
      } else if (this.latestDirection?.state === 'saved') {
        next = 'Your saved question can wait, or you can try it today.'
      } else if (['recommend', 'ask'].includes(record?.scout?.route)) {
        const intervention = (this.mobile?.recent_interventions || []).find(
          (item) => item.shoot_id === record.shoot_id && Number(item.shoot_revision) === Number(record.revision),
        )
        const answered = this.mobile?.recent_scout_answers?.some(
          (answer) => answer.question_id === record.scout.question?.id,
        )
        next = intervention?.attempt_state === 'left'
          ? 'You left that recommendation. Shoots did not guess why.'
          : answered
            ? 'Shoots will use your answer for this Shoot only.'
            : scoutStory(record.scout)
      } else if (record?.scout?.reason) {
        next = scoutStory(record.scout)
      }
      const items = [
        { label: 'Shoots handled', text: handled, state: record ? 'done' : 'waiting' },
        { label: 'You decided', text: this.photographerAction.text, state: this.photographerAction.state },
        { label: 'The result', text: this.resultReceipt.text, state: this.resultReceipt.state },
        { label: 'Next', text: next, state: 'current' },
      ]
      if (this.memoryEffect) {
        items.push({ label: 'What Shoots remembered', text: this.memoryEffect, state: 'done' })
      }
      return items
    },
    latestChangeLabel() {
      if (!this.latestChange?.change) return ''
      return this.latestChange.change.state === 'insufficient evidence'
        ? 'not enough to say'
        : this.latestChange.change.state
    },
    latestReproduce() {
      if (
        this.experiment?.type === 'reproduce' &&
        this.experiment.reference_shot_id &&
        this.experiment.result_shot_ids?.length
      ) {
        return this.experiment
      }
      return [...this.pastExperiments]
        .filter((experiment) =>
          experiment.type === 'reproduce' &&
          experiment.reference_shot_id &&
          experiment.result_shot_ids?.length,
        )
        .sort((a, b) => (b.closed_at || b.issued_at || '').localeCompare(a.closed_at || a.issued_at || ''))[0] || null
    },
    unknowns() {
      const missing = [
        ...(this.profile?.blind_spots || []),
        ...(this.profile?.dimensions || [])
          .filter((dimension) => dimension.buckets.every((bucket) => bucket.count === 0))
          .map((dimension) => dimension.label),
      ]
      const kept = []
      for (const item of [...new Set(missing)].sort((a, b) => b.length - a.length)) {
        const key = item.toLocaleLowerCase()
        if (kept.some((existing) => existing.toLocaleLowerCase().includes(key) || key.includes(existing.toLocaleLowerCase()))) continue
        kept.push(item)
      }
      return kept.slice(0, this.latest ? 5 : 2)
    },
    driveUrl() {
      return this.me?.drive_folder_id ? `https://drive.google.com/drive/folders/${this.me.drive_folder_id}` : ''
    },
    latestShootRecord() {
      return this.mobile?.latest_shoot_record || null
    },
    latestShootSummary() {
      if (this.isSampleRecord && this.latestShootRecord) {
        return `${this.latestShootRecord.receipt?.shot_count || this.latestShootRecord.shot_ids?.length || 0} Shot cards across ${this.latestShootRecord.receipt?.scene_count || 0} sample Scene groups.`
      }
      return shootSummary(this.latestShootRecord?.receipt)
    },
    latestInterventionSummary() {
      const intervention = this.latestIntervention
      if (!intervention?.result_shot_ids?.length) return ''
      return resultSummary(
        intervention.result_shot_ids.length,
        intervention.criteria_met_results,
        intervention.abstentions,
      )
    },
    latestInterventionReason() {
      return displayLanguage(this.latestIntervention?.outcome_reason) || 'There is no result to compare yet.'
    },
    latestDraft() {
      return this.mobile?.latest_deconstruction || null
    },
    deconstructionSource() {
      if (this.latestDraft?.source_type === 'experiment') {
        const experiment = this.pastExperiments.find((item) => item.id === this.latestDraft.source_id)
        if (experiment) {
          return {
            type: 'experiment',
            id: experiment.id,
            revision: this.latestDraft.source_revision,
            label: 'Experiment',
            memberIds: [experiment.reference_shot_id, ...(experiment.result_shot_ids || [])].filter(Boolean),
          }
        }
      }
      if (!this.latestShootRecord) return null
      return {
        type: 'shoot',
        id: this.latestShootRecord.shoot_id,
        revision: this.latestShootRecord.revision,
        label: 'Shoot',
        memberIds: this.latestShootRecord.shot_ids || [],
      }
    },
    deconstruction() {
      const draft = this.latestDraft
      const source = this.deconstructionSource
      if (!draft || !source) return null
      return draft.source_type === source.type && draft.source_id === source.id &&
        draft.source_revision === source.revision ? draft : null
    },
    deconstructionKeepers() {
      const source = this.deconstructionSource
      if (!source) return []
      const allowed = new Set(source.memberIds)
      return this.orderedShots
        .map((item) => item.shot)
        .filter((shot) => allowed.has(shot.id) && shot.kept_at)
    },
    deconstructionDownloadUrl() {
      return this.deconstruction?.id
        ? `/api/deconstructions/${encodeURIComponent(this.deconstruction.id)}/download`
        : ''
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['connect', 'sync', 'enablePush', 'pairCamera', 'prepareDeconstruction']),
    ...mapActions(useAuthStore, ['logout']),
    async signOut() {
      await this.logout()
      this.$router.push({ name: 'login' })
    },
    blobUrl(path) {
      return path ? `/api/blobs/${path}` : ''
    },
    createDeconstruction() {
      const cover = this.selectedCover || this.deconstruction?.cover_shot_id || this.deconstructionKeepers[0]?.id
      const source = this.deconstructionSource
      if (!cover || !source) return
      return this.prepareDeconstruction(
        source.type,
        source.id,
        source.revision,
        cover,
      )
    },
    repeatabilityEvidence(technique) {
      return repeatabilitySummary(technique)
    },
  },
}
</script>

<template>
  <div class="page-shell pb-24 pt-8 md:pb-12 md:pt-10">
    <JourneyFirstImpressionPrototype
      v-if="journeyPrototypeVariant && !isSampleRecord"
      :variant="journeyPrototypeVariant"
      :record="latestShootRecord"
      :profile="profile"
      :shots="orderedShots"
      :latest-sentences="latestSentences"
      :receipt-items="journeyReceiptItems"
      :deconstruction="deconstruction"
      :experiment="experiment"
      :reproduce="latestReproduce"
    />

    <template v-else>
      <header class="max-w-3xl">
        <p class="eyebrow">Journey</p>
        <h1 class="mt-3 t-hero lg:text-[50px]">
          {{ isSampleRecord ? 'Inspect a hand-authored Journey layout.' : 'Your photography, over time.' }}
        </h1>
        <p class="mt-5 max-w-2xl text-[16px] leading-7 text-neutral-300">
          {{ isSampleRecord
            ? 'These values show how a Journey could be presented. They are not observations about a Photographer.'
            : 'See what Shoots handled, what keeps returning, and what changed when you tried something on purpose.' }}
        </p>
      </header>

    </template>

    <div class="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(330px,0.8fr)] lg:items-start" :class="journeyPrototypeVariant ? 'mt-12' : 'mt-8'">
      <div class="min-w-0 space-y-6">
        <section v-if="latestShootRecord" class="surface p-5 sm:p-7">
          <div class="flex items-start gap-4">
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-ink" aria-hidden="true">
              <svg viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-[2.4]">
                <path d="m5 12 4 4L19 6" />
              </svg>
            </span>
            <div>
              <p class="eyebrow text-accent">{{ isSampleRecord ? 'Sample Shoot layout' : 'Your latest Shoot' }}</p>
              <h2 class="mt-2 t-title">{{ latestShootSummary }}</h2>
            </div>
          </div>
          <p class="mt-4 t-body">
            <template v-if="isSampleRecord">
              {{ latestShootRecord.receipt?.shot_count }} Shot cards and
              {{ latestShootRecord.receipt?.scene_count }} Scene groups were hand-authored. No ingestion, Analysis, or grouping ran.
            </template>
            <template v-else>
              Shoots read {{ latestShootRecord.receipt?.shot_count }} Shots and grouped them into
              {{ latestShootRecord.receipt?.scene_count }}
              {{ latestShootRecord.receipt?.scene_count === 1 ? 'Scene' : 'Scenes' }}.
            </template>
          </p>
          <RouterLink
            :to="{ name: 'shoot-record', params: { shootId: latestShootRecord.shoot_id, revision: latestShootRecord.revision } }"
            class="btn mt-5 w-full sm:w-auto"
          >
            {{ isSampleRecord ? 'Inspect the sample Shoot layout' : 'Open Shoot Record' }}
          </RouterLink>
        </section>

        <template v-if="!journeyPrototypeVariant">
          <details class="rounded-2xl border border-edge bg-panel">
            <summary class="flex min-h-14 cursor-pointer list-none items-center gap-3 px-5 py-4 t-body text-neutral-200">
              <span>{{ isSampleRecord ? 'What this fixture represents' : 'What Shoots changed for you' }}</span>
              <span class="ml-auto text-muted" aria-hidden="true">+</span>
            </summary>
            <CompanionReceipt
              class="border-x-0 border-b-0"
              :title="isSampleRecord ? 'Sample Journey' : 'Your photography loop'"
              :items="journeyReceiptItems"
            />
          </details>

          <section v-if="profile?.shots" class="surface-soft p-5 sm:p-6">
            <p class="eyebrow">Across your archive</p>
            <div class="mt-4 flex flex-wrap gap-x-6 gap-y-3 t-meta">
              <span><strong class="mr-1 text-paper">{{ profile.shots }}</strong> {{ isSampleRecord ? 'sample Shot cards' : 'readable Shots' }}</span>
              <span><strong class="mr-1 text-paper">{{ profile.keepers }}</strong> {{ isSampleRecord ? 'sample Keeper marks' : 'Keeper signals' }}</span>
              <span v-if="recurring.length"><strong class="mr-1 text-paper">{{ recurring.length }}</strong> {{ isSampleRecord ? 'sample Technique labels' : 'recurring Techniques' }}</span>
              <span v-if="profile.scenes"><strong class="mr-1 text-paper">{{ profile.scenes }}</strong> {{ isSampleRecord ? 'sample Scene groups' : 'grouped Scenes' }}</span>
            </div>
          </section>
        </template>

        <section id="journey-evidence" class="surface scroll-mt-6 p-5 sm:p-7">
          <div class="flex items-center justify-between gap-4">
            <p class="eyebrow">{{ isSampleRecord ? 'Sample Journey Update' : latest ? 'The latest pattern' : 'What Shoots knows so far' }}</p>
            <p v-if="latest" class="t-meta">{{ new Date(latest.created_at).toLocaleDateString() }}</p>
          </div>

          <template v-if="latest">
            <div v-if="latestSentences.length" class="mt-5 divide-y divide-edge">
              <p
                v-for="(sentence, index) in latestSentences"
                :key="sentence"
                class="py-3 text-[16px] leading-7 text-neutral-300 first:pt-0 last:pb-0"
                :class="index === 0 ? 'text-[19px] font-medium leading-7 text-paper' : ''"
              >
                {{ sentence }}
              </p>
            </div>
            <p v-else class="mt-5 t-body">The numbers changed, but Shoots could not turn them into a clear note.</p>
            <p class="mt-4 t-meta">Based on {{ latest.shots }} {{ isSampleRecord ? 'hand-authored Shot cards' : 'Shots' }}</p>

            <DisclosureRow class="mt-4" :label="isSampleRecord ? 'Hand-authored support lines' : 'Evidence behind this update'" :count="latestEvidence.length">
              <ul class="space-y-2">
                <li v-for="line in latestEvidence" :key="line" class="flex gap-3 t-body text-neutral-300">
                  <span class="mt-2 h-1 w-1 shrink-0 rounded-full bg-neutral-500" />
                  <span>{{ line }}</span>
                </li>
              </ul>
              <p v-if="latest.provenance?.sample_size" class="mt-5 t-meta">
                <template v-if="isSampleRecord">Fixture provenance · {{ latest.provenance.sample_size }} sample Shot cards</template>
                <template v-else>
                  {{ latest.provenance.calc_version }} · {{ latest.provenance.sample_size }}-Shot sample
                  <template v-if="latest.provenance.model"> · wording by {{ latest.provenance.model }}</template>
                </template>
              </p>
            </DisclosureRow>
          </template>

          <div v-else class="mt-5">
            <p class="eyebrow text-accent">Known so far</p>
            <h2 class="mt-2 text-xl font-medium text-paper">Your record has started.</h2>
            <ul class="mt-4 space-y-2">
              <li v-for="fact in knownFacts" :key="fact" class="flex gap-3 t-body text-neutral-300">
                <span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                <span>{{ fact }}</span>
              </li>
            </ul>
            <p class="mt-5 eyebrow">Next useful signal</p>
            <p class="mt-2 t-body">{{ nextEvidenceAction }}</p>
            <RouterLink :to="{ name: 'shots' }" class="btn-quiet mt-4 w-full sm:w-auto">Review your Shots</RouterLink>
          </div>
        </section>

        <section v-if="experiment && !isSampleRecord" id="journey-experiment" class="surface scroll-mt-6 border-accent/40 p-5 sm:p-7">
          <p class="eyebrow text-accent">Optional next Experiment</p>
          <h2 class="mt-2 t-title">{{ experiment.title }}</h2>
          <p class="mt-3 t-body">{{ experiment.why_now }}</p>
          <RouterLink :to="{ name: 'now', query: { focus: 'experiment' } }" class="btn-quiet mt-5 w-full sm:w-auto">
            Open Experiment
          </RouterLink>
        </section>

        <ReproduceProof
          v-if="latestReproduce && !isSampleRecord"
          :experiment="latestReproduce"
          :shots="orderedShots"
        />

        <section v-if="keeperSignals.length && !isSampleRecord" class="surface p-5 sm:p-7">
          <p class="eyebrow text-accent">Direct signals from you</p>
          <h2 class="mt-2 t-title">What your Keeper marks show</h2>
          <div class="mt-5 divide-y divide-edge">
            <div v-for="signal in keeperSignals" :key="signal.id" class="py-4 first:pt-0 last:pb-0">
              <p class="eyebrow">{{ signal.label }}</p>
              <div class="mt-2 flex items-baseline justify-between gap-4">
                <p class="text-[20px] font-medium text-paper">{{ signal.dominant }}</p>
                <p class="t-num text-sm text-neutral-300">
                  {{ signal.keepers }} of {{ signal.readableKeepers }} readable Keepers
                </p>
              </div>
            </div>
          </div>
          <p class="mt-5 t-meta">Only your marks count here. An unmarked Shot says nothing about your taste.</p>
        </section>

        <section v-if="profile?.shots && !profile.taste_is_known && !isSampleRecord" class="rounded-[20px] border border-dashed border-edge-strong p-5 sm:p-7">
          <p class="eyebrow">Optional taste signal</p>
          <h2 class="mt-2 t-title">Mark a Keeper only when a Shot matters to you</h2>
          <p class="mt-3 t-body">
            {{ profile.keepers }} of {{ tasteThreshold }} marked. After {{ keepersNeeded }} more
            {{ keepersNeeded === 1 ? 'Shot' : 'Shots' }}, Shoots can describe where your own choices gather.
          </p>
          <RouterLink :to="{ name: 'shots' }" class="btn-quiet mt-5 w-full sm:w-auto">Review your Shots</RouterLink>
          <p class="mt-4 t-meta">This is optional. An unmarked Shot says nothing about your taste.</p>
        </section>

        <section v-if="latestChange && !isSampleRecord" class="surface p-5 sm:p-7">
          <p class="eyebrow">What changed afterward</p>
          <div class="mt-4 flex flex-wrap items-baseline justify-between gap-3">
            <h2 class="text-xl font-semibold text-paper">{{ latestChange.title }}</h2>
            <span class="t-meta">{{ latestChangeLabel }}</span>
          </div>
          <p class="mt-3 t-body text-neutral-200">{{ latestChange.change.outcome }}</p>
          <p class="mt-4 t-meta">This compares like with like. It does not claim the Experiment caused the difference.</p>
        </section>

        <section v-if="latestIntervention && !isSampleRecord" class="surface p-5 sm:p-7">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="eyebrow">What happened to the last suggestion</p>
            <span class="t-meta">{{ latestIntervention.route }} · {{ latestIntervention.attempt_state }}</span>
          </div>
          <p class="mt-4 text-[17px] leading-7 text-paper">
            {{ latestInterventionReason }}
          </p>
          <p v-if="latestIntervention.result_shot_ids?.length" class="mt-4 t-meta">
            {{ latestInterventionSummary }}
          </p>
          <p class="mt-3 t-meta">Trying the idea and changing your later Shots are two different facts.</p>
        </section>

        <section v-if="deconstructionSource" id="journey-deconstruction" class="surface relative scroll-mt-6 overflow-hidden p-5 sm:p-7">
          <div class="pointer-events-none absolute -right-24 -top-28 h-72 w-72 rounded-full bg-accent/10 blur-3xl" />
          <div class="relative max-w-2xl">
            <p class="eyebrow text-accent">{{ isSampleRecord ? 'Sample visual story layout' : 'Your visual story' }}</p>
            <h2 class="mt-2 text-[27px] leading-8 font-medium tracking-[-0.025em] text-paper sm:text-[34px] sm:leading-10" style="font-family: 'Iowan Old Style', 'Palatino Linotype', Georgia, serif">
              {{ isSampleRecord
                ? `This sample ${deconstructionSource.label} shows where an opening, a turn, and an ending would appear.`
                : `This ${deconstructionSource.label} has an opening, a turn, and an ending.` }}
            </h2>
            <p class="mt-3 t-body">
              {{ isSampleRecord
                ? 'No story was built and no visual thread was found by an agent. Story-building actions are disabled.'
                : 'Shoots follows the sequence and finds the visual thread. You decide which marked Shot opens the story.' }}
            </p>
          </div>

          <template v-if="deconstruction?.status === 'drafted'">
            <div class="relative mt-6 flex snap-x snap-mandatory gap-4 overflow-x-auto pb-4">
              <figure
                v-for="(page, index) in deconstruction.pages"
                :key="page.blob_path"
                class="min-w-[76%] snap-center sm:min-w-[42%] lg:min-w-[38%]"
              >
                <a
                  :href="blobUrl(page.blob_path)"
                  target="_blank"
                  rel="noreferrer"
                  class="group block overflow-hidden rounded-2xl border border-edge bg-black shadow-[0_18px_55px_rgba(0,0,0,0.28)]"
                  :aria-label="`Open story page: ${page.title}`"
                >
                  <img
                    :src="blobUrl(page.blob_path)"
                    :alt="page.title"
                    class="aspect-[4/5] w-full object-cover transition duration-300 group-hover:scale-[1.015]"
                  />
                </a>
                <figcaption class="mt-2 flex items-center justify-between gap-3 text-[12px] text-muted">
                  <span>{{ page.title }}</span>
                  <span class="t-num">{{ index + 1 }} of {{ deconstruction.pages.length }}</span>
                </figcaption>
              </figure>
            </div>

            <div v-if="deconstruction.suggested_caption" class="mt-4 rounded-2xl border border-edge bg-black/20 p-4">
              <p class="eyebrow">Caption for the story</p>
              <p class="mt-2 text-[14px] leading-6 text-neutral-200">{{ deconstruction.suggested_caption }}</p>
            </div>

            <div class="mt-5 flex flex-wrap gap-3">
              <a :href="deconstructionDownloadUrl" download class="btn">
                <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-2">
                  <path d="M12 3v12" /><path d="m7 10 5 5 5-5" /><path d="M5 21h14" />
                </svg>
                Download story
              </a>
              <button v-if="!isSampleRecord" type="button" class="btn-quiet" :disabled="busy === 'deconstruction'" @click="createDeconstruction">
                {{ busy === 'deconstruction' ? 'Building…' : 'Rebuild story' }}
              </button>
            </div>
            <p class="mt-3 t-meta">The download includes every page and the caption. Shoots never posts for you.</p>
          </template>

          <template v-else-if="deconstructionKeepers.length && !isSampleRecord">
            <p class="mt-6 eyebrow">Choose the opening Shot</p>
            <p class="mt-2 text-[14px] leading-6 text-neutral-300">Use one Shot you already marked. The first page stays your choice.</p>
            <div class="mt-3 flex gap-3 overflow-x-auto pb-2">
              <button
                v-for="shot in deconstructionKeepers"
                :key="shot.id"
                type="button"
                class="shrink-0 rounded-xl border p-1"
                :class="(selectedCover || deconstructionKeepers[0]?.id) === shot.id ? 'border-accent' : 'border-edge'"
                @click="selectedCover = shot.id"
              >
                <img :src="blobUrl(shot.blobs.thumb || shot.blobs.original)" alt="Possible story cover" class="h-28 w-28 rounded-lg object-cover" />
              </button>
            </div>
            <button type="button" class="btn mt-4" :disabled="busy === 'deconstruction'" @click="createDeconstruction">
              {{ busy === 'deconstruction' ? 'Building…' : 'Build my story' }}
            </button>
          </template>
          <div v-else class="mt-6 rounded-2xl border border-dashed border-edge-strong bg-black/15 p-4">
            <template v-if="isSampleRecord">
              <p class="text-[15px] font-medium text-paper">Sample only · no story was built.</p>
              <p class="mt-2 t-body">A real Photographer would choose a Keeper cover before Shoots drafts downloadable story pages.</p>
            </template>
            <template v-else>
              <p class="text-[15px] font-medium text-paper">Choose one Shot you care about first.</p>
              <p class="mt-2 t-body">Mark it with the bookmark on this {{ deconstructionSource.label }}, then return here to use it as the opening.</p>
            </template>
          </div>
        </section>

        <section v-if="tendencies.length" class="surface p-5 sm:p-7">
          <div class="flex items-end justify-between gap-4">
            <div>
              <p class="eyebrow">{{ isSampleRecord ? 'Sample pattern values' : 'What keeps appearing' }}</p>
              <h2 class="mt-2 t-title">{{ isSampleRecord ? 'How recurring choices could be presented' : 'The choices you return to' }}</h2>
            </div>
            <span class="t-meta">{{ isSampleRecord ? 'hand-authored fixture' : 'from your own Shots' }}</span>
          </div>
          <div class="mt-5 divide-y divide-edge">
            <div v-for="tendency in tendencies" :key="tendency.id" class="py-4 first:pt-0 last:pb-0">
              <p class="eyebrow">{{ tendency.label }}</p>
              <div class="mt-2 flex items-baseline justify-between gap-4">
                <p class="text-[20px] font-medium text-paper">{{ tendency.dominant }}</p>
                <p class="t-num text-sm text-neutral-300">{{ tendency.count }}/{{ tendency.total }}</p>
              </div>
              <p class="mt-2 t-meta">
                {{ isSampleRecord ? 'fixture value' : tendency.source }}
                <template v-if="tendency.keepers"> · {{ tendency.keepers }}/{{ tendency.readableKeepers }} marked Keepers</template>
              </p>
            </div>
          </div>
        </section>
      </div>

      <aside class="min-w-0 space-y-6 lg:sticky lg:top-7">
        <section class="surface p-5 sm:p-6">
          <p class="eyebrow">{{ isSampleRecord ? 'Sample recurring Technique labels' : 'What keeps recurring' }}</p>
          <div v-if="recurring.length" class="mt-4 divide-y divide-edge">
            <div v-for="technique in recurring" :key="technique.technique_id" class="py-4 first:pt-0 last:pb-0">
              <p class="text-[17px] font-medium text-paper">{{ technique.name }}</p>
              <p class="mt-1 t-meta">
                {{ isSampleRecord ? 'Hand-authored as clear' : 'Clear' }} in {{ technique.corroborated_shots }} Shots across
                {{ technique.distinct_shoots }} Shoot{{ technique.distinct_shoots === 1 ? '' : 's' }}
              </p>
              <p class="mt-2 t-meta text-neutral-300">
                {{ isSampleRecord ? 'Sample value: no Reproduce session.' : repeatabilityEvidence(technique) }}
              </p>
            </div>
          </div>
          <p v-else class="mt-4 t-body">A Technique becomes recurring after Shoots sees it clearly in three Shots. Nothing has reached that point yet.</p>
        </section>

        <section v-if="events.length && !isSampleRecord" class="surface p-5 sm:p-6">
          <p class="eyebrow">Recent agent activity</p>
          <div class="mt-4">
            <AgentLog :limit="4" />
          </div>
        </section>

        <section class="rounded-[20px] border border-dashed border-edge-strong p-5 sm:p-6">
          <p class="eyebrow">{{ isSampleRecord ? 'Sample limits' : 'What Shoots still cannot see' }}</p>
          <template v-if="unknowns.length">
            <p class="mt-3 t-body">{{ isSampleRecord ? 'The fixture marks these values as unavailable:' : 'Some files do not carry enough information for these:' }}</p>
            <ul class="mt-4 space-y-2">
              <li v-for="unknown in unknowns" :key="unknown" class="flex gap-3 t-body text-neutral-300">
                <span class="text-muted">—</span><span>{{ unknown }}</span>
              </li>
            </ul>
          </template>
          <p v-else class="mt-3 t-body">Shoots has enough information for the patterns shown here. Visual reads are still opinions, and their sources remain below.</p>
        </section>
      </aside>
    </div>

    <section class="mt-10 border-t border-edge pt-4">
      <DisclosureRow
        :label="isSampleRecord ? 'Fixture profile and map values' : 'How Shoots reached this'"
        :count="isSampleRecord ? 'hand-authored' : pastExperiments.length ? `${pastExperiments.length} Experiments` : 'profile + map'"
      >
        <p v-if="isSampleRecord" class="py-3 t-body">
          These profile and Technique Map values were written into the fixture. They were not calculated by Shoots.
        </p>
        <div v-else class="space-y-10 py-3">
          <TendencyProfile />
          <TechniqueMap />
          <section v-if="pastExperiments.length">
            <h2 class="t-title">Past Experiments</h2>
            <div class="mt-4">
              <ExperimentRecord v-for="experiment in pastExperiments" :key="experiment.id" :experiment="experiment" />
            </div>
          </section>
        </div>
      </DisclosureRow>

      <DisclosureRow :label="isSampleRecord ? 'Connections · disabled in sample' : 'Phone Source, Drive, and notifications'">
        <p v-if="isSampleRecord" class="py-2 t-body">
          Phone Source, Drive, notification, and pairing controls are unavailable in this read-only fixture.
        </p>
        <div v-else class="grid gap-7 py-2 sm:grid-cols-2">
          <ConnectStep v-if="!driveConnected" class="sm:col-span-2" />
          <div>
            <p class="eyebrow">Pair Android Phone Source</p>
            <p class="mt-3 t-body">Create a one-use code, then enter it in the Android app. Keep using your normal camera.</p>
            <p v-if="pairCode" class="mt-4 font-mono text-3xl tracking-[0.25em] text-paper">{{ pairCode.code }}</p>
            <p v-if="pairCode" class="mt-2 t-meta">Expires in {{ Math.round(pairCode.expires_in_seconds / 60) }} minutes.</p>
            <button type="button" class="btn-quiet mt-4" :disabled="busy === 'pair'" @click="pairCamera">
              {{ busy === 'pair' ? 'Creating…' : pairCode ? 'Create another code' : 'Create pairing code' }}
            </button>
          </div>

          <div class="space-y-3">
            <p class="eyebrow">Connections</p>
            <a v-if="driveUrl" :href="driveUrl" target="_blank" rel="noopener" class="tap-target t-body text-neutral-300 hover:text-paper">
              Open the Shoots Drive folder ↗
            </a>
            <button v-if="push === 'off'" type="button" class="tap-target t-body text-neutral-300 hover:text-paper" :disabled="busy === 'push'" @click="enablePush">
              {{ busy === 'push' ? 'Asking…' : 'Turn on notifications' }}
            </button>
            <p v-else-if="push === 'on'" class="t-body text-muted">Notifications are on for this device.</p>
            <p v-else-if="push === 'denied'" class="t-body text-muted">This browser blocks notifications.</p>
            <button v-if="driveConnected" type="button" class="tap-target t-body text-neutral-300 hover:text-paper" :disabled="busy === 'sync'" @click="sync">
              {{ busy === 'sync' ? 'Checking…' : 'Check the Drive folder now' }}
            </button>
            <button type="button" class="tap-target t-body text-muted hover:text-paper md:hidden" @click="signOut">Sign out</button>
          </div>
        </div>
      </DisclosureRow>

      <DisclosureRow label="Agent activity" :count="isSampleRecord ? 'none' : 'audit'">
        <p v-if="isSampleRecord" class="t-body">No agents ran for this Sample Record.</p>
        <AgentLog v-else :limit="60" />
      </DisclosureRow>
    </section>
  </div>
</template>
