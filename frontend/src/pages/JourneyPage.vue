<script>
import { mapActions, mapState } from 'pinia'

import AgentLog from '@/components/AgentLog.vue'
import DisclosureRow from '@/components/DisclosureRow.vue'
import ExperimentRecord from '@/components/ExperimentRecord.vue'
import ReproduceProof from '@/components/ReproduceProof.vue'
import TechniqueMap from '@/components/TechniqueMap.vue'
import TendencyProfile from '@/components/TendencyProfile.vue'
import { useAuthStore } from '@/stores/auth'
import { useShootsStore } from '@/stores/shoots'

function displayLanguage(text) {
  return (text || '')
    .replace(/\bhabits\b/gi, 'Tendencies')
    .replace(/\bhabit\b/gi, 'Tendency')
    .replace(/\bphotos\b/gi, 'Shots')
    .replace(/\bphoto\b/gi, 'Shot')
    .replace(/\bquests?\b/gi, 'Experiment')
}

/** The longitudinal answer first; distributions and execution logs second. */
export default {
  name: 'JourneyPage',
  components: { AgentLog, DisclosureRow, ExperimentRecord, ReproduceProof, TechniqueMap, TendencyProfile },
  data() {
    return { selectedCover: '' }
  },
  computed: {
    ...mapState(useShootsStore, [
      'pastExperiments',
      'me',
      'push',
      'busy',
      'connected',
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
    latestSentences() {
      const body = displayLanguage(this.latest?.body)
      return body.match(/[^.!?]+[.!?]+|[^.!?]+$/g)?.map((sentence) => sentence.trim()).filter(Boolean) || []
    },
    latestEvidence() {
      return (this.latest?.evidence || []).map(displayLanguage)
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
        .filter((dimension) => dimension.readable && total(dimension) > 0 && dimension.dominant)
        .sort((a, b) => Number(b.narrow) - Number(a.narrow) || a.exploration - b.exploration)
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
    latestChange() {
      return [...this.pastExperiments]
        .filter((experiment) => experiment.change)
        .sort((a, b) => (b.closed_at || b.issued_at || '').localeCompare(a.closed_at || a.issued_at || ''))[0] || null
    },
    latestIntervention() {
      return this.mobile?.recent_interventions?.[0] || null
    },
    latestReproduce() {
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
      return kept.slice(0, 5)
    },
    driveUrl() {
      return this.me?.drive_folder_id ? `https://drive.google.com/drive/folders/${this.me.drive_folder_id}` : ''
    },
    latestShootRecord() {
      return this.mobile?.latest_shoot_record || null
    },
    deconstruction() {
      const draft = this.mobile?.latest_deconstruction
      if (!draft || draft.source_type !== 'shoot' || !this.latestShootRecord) return null
      return draft.source_id === this.latestShootRecord.shoot_id &&
        draft.source_revision === this.latestShootRecord.revision ? draft : null
    },
    deconstructionKeepers() {
      const ids = this.latestShootRecord?.receipt?.keeper_shot_ids || []
      return ids.map((id) => this.orderedShots.find((item) => item.shot.id === id)?.shot).filter(Boolean)
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['sync', 'enablePush', 'pairCamera', 'prepareDeconstruction']),
    ...mapActions(useAuthStore, ['logout']),
    async signOut() {
      await this.logout()
      this.$router.push({ name: 'login' })
    },
    blobUrl(path) {
      return path ? `/api/blobs/${path}` : ''
    },
    createDeconstruction() {
      const cover = this.selectedCover || this.deconstructionKeepers[0]?.id
      if (!cover || !this.latestShootRecord) return
      return this.prepareDeconstruction(
        'shoot',
        this.latestShootRecord.shoot_id,
        this.latestShootRecord.revision,
        cover,
      )
    },
    repeatabilityEvidence(technique) {
      if (!technique.reproduce_sessions) {
        return 'Recurring does not prove deliberate control. No settled Reproduce session yet.'
      }
      return `${technique.reproduce_sessions} settled session${technique.reproduce_sessions === 1 ? '' : 's'} · ` +
        `${technique.evaluable_reproduce_sessions || 0} evaluable · ` +
        `${technique.criteria_met_sessions || 0} met Criteria`
    },
  },
}
</script>

<template>
  <div class="page-shell pb-24 pt-8 md:pb-12 md:pt-10">
    <header class="max-w-3xl">
      <p class="eyebrow">Journey</p>
      <h1 class="mt-3 t-hero lg:text-[50px]">What I can say about your eye, and why.</h1>
      <p class="mt-5 max-w-2xl text-[16px] leading-7 text-neutral-300">
        This is memory across your Shots—not a style label, score, or curriculum. Claims stay beside the Evidence that permits them.
      </p>
    </header>

    <div v-if="profile?.shots" class="mt-7 flex flex-wrap gap-x-6 gap-y-2 border-y border-edge py-4 t-meta">
      <span><strong class="mr-1 text-paper">{{ profile.shots }}</strong> readable Shots</span>
      <span><strong class="mr-1 text-paper">{{ profile.keepers }}</strong> Keeper signals</span>
      <span><strong class="mr-1 text-paper">{{ recurring.length }}</strong> recurring Techniques</span>
      <span v-if="profile.scenes"><strong class="mr-1 text-paper">{{ profile.scenes }}</strong> grouped Scenes</span>
    </div>

    <div class="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(330px,0.8fr)] lg:items-start">
      <div class="space-y-6">
        <ReproduceProof
          v-if="latestReproduce"
          :experiment="latestReproduce"
          :shots="orderedShots"
        />

        <section class="surface p-5 sm:p-7">
          <div class="flex items-center justify-between gap-4">
            <p class="eyebrow">Latest Journey Update</p>
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
            <p v-else class="mt-5 t-body">The counts moved, but the writer did not return a usable update.</p>
            <p class="mt-4 t-meta">Written from {{ latest.shots }} Shots</p>

            <DisclosureRow class="mt-4" label="Evidence behind this update" :count="latestEvidence.length">
              <ul class="space-y-2">
                <li v-for="line in latestEvidence" :key="line" class="flex gap-3 t-body text-neutral-300">
                  <span class="mt-2 h-1 w-1 shrink-0 rounded-full bg-neutral-500" />
                  <span>{{ line }}</span>
                </li>
              </ul>
              <p v-if="latest.provenance?.sample_size" class="mt-5 t-meta">
                {{ latest.provenance.calc_version }} · {{ latest.provenance.sample_size }}-Shot sample
                <template v-if="latest.provenance.model"> · wording by {{ latest.provenance.model }}</template>
              </p>
            </DisclosureRow>
          </template>

          <div v-else class="mt-5">
            <p class="text-xl font-medium text-paper">Not enough has changed to write one yet.</p>
            <p class="mt-3 t-body">Shoots waits for the record to move instead of publishing a fresh summary on a schedule.</p>
          </div>
        </section>

        <section v-if="latestChange" class="surface p-5 sm:p-7">
          <p class="eyebrow">Latest measured Change</p>
          <div class="mt-4 flex flex-wrap items-baseline justify-between gap-3">
            <h2 class="text-xl font-semibold text-paper">{{ latestChange.title }}</h2>
            <span class="t-meta">{{ latestChange.change.state }}</span>
          </div>
          <p class="mt-3 t-body text-neutral-200">{{ latestChange.change.outcome }}</p>
          <p class="mt-4 t-meta">Comparable counts before and after. This does not claim the Experiment caused the Change or that the Shots improved.</p>
        </section>

        <section v-if="latestIntervention" class="surface p-5 sm:p-7">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="eyebrow">What happened to the last suggestion</p>
            <span class="t-meta">{{ latestIntervention.route }} · {{ latestIntervention.attempt_state }}</span>
          </div>
          <p class="mt-4 text-[17px] leading-7 text-paper">
            {{ latestIntervention.outcome_reason || 'No observable outcome is available yet.' }}
          </p>
          <p v-if="latestIntervention.result_shot_ids?.length" class="mt-4 t-meta">
            {{ latestIntervention.result_shot_ids.length }} explicit results ·
            {{ latestIntervention.criteria_met_results }} Criteria met ·
            {{ latestIntervention.abstentions }} abstentions
          </p>
          <p class="mt-3 t-meta">Attempt state and observable Change stay separate. No attempt is treated as failed advice.</p>
        </section>

        <section v-if="latestShootRecord" class="surface p-5 sm:p-7">
          <p class="eyebrow">Deconstruction</p>
          <h2 class="mt-2 t-title">Share how you worked the Shoot</h2>
          <p class="mt-3 t-body">One visual claim per page, built from the settled record. You choose the Keeper cover.</p>

          <template v-if="deconstruction?.status === 'drafted'">
            <div class="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <figure v-for="page in deconstruction.pages" :key="page.blob_path">
                <img :src="blobUrl(page.blob_path)" :alt="page.title" class="aspect-[4/5] w-full rounded-xl object-cover" />
                <figcaption class="mt-2 t-meta">{{ page.title }}</figcaption>
              </figure>
            </div>
            <p class="mt-4 t-meta">The Android app shares these exact pages as one carousel. Shoots never posts automatically.</p>
          </template>

          <template v-else-if="deconstructionKeepers.length">
            <p class="mt-5 eyebrow">Choose your cover</p>
            <div class="mt-3 flex gap-3 overflow-x-auto pb-2">
              <button
                v-for="shot in deconstructionKeepers"
                :key="shot.id"
                type="button"
                class="shrink-0 rounded-xl border p-1"
                :class="(selectedCover || deconstructionKeepers[0]?.id) === shot.id ? 'border-accent' : 'border-edge'"
                @click="selectedCover = shot.id"
              >
                <img :src="blobUrl(shot.blobs.thumb || shot.blobs.original)" alt="Keeper cover" class="h-24 w-24 rounded-lg object-cover" />
              </button>
            </div>
            <button type="button" class="btn-primary mt-4" :disabled="busy === 'deconstruction'" @click="createDeconstruction">
              {{ busy === 'deconstruction' ? 'Rendering…' : 'Create Deconstruction' }}
            </button>
          </template>
          <p v-else class="mt-4 t-body">Mark one Shot from this Shoot as a Keeper before choosing a cover.</p>
        </section>

        <section v-if="tendencies.length" class="surface p-5 sm:p-7">
          <div class="flex items-end justify-between gap-4">
            <div>
              <p class="eyebrow">What keeps appearing</p>
              <h2 class="mt-2 t-title">Your strongest readable Tendencies</h2>
            </div>
            <span class="t-meta">counts, not grades</span>
          </div>
          <div class="mt-5 divide-y divide-edge">
            <div v-for="tendency in tendencies" :key="tendency.id" class="py-4 first:pt-0 last:pb-0">
              <p class="eyebrow">{{ tendency.label }}</p>
              <div class="mt-2 flex items-baseline justify-between gap-4">
                <p class="text-[20px] font-medium text-paper">{{ tendency.dominant }}</p>
                <p class="t-num text-sm text-neutral-300">{{ tendency.count }}/{{ tendency.total }}</p>
              </div>
              <p class="mt-2 t-meta">
                {{ tendency.source }}
                <template v-if="tendency.keepers"> · {{ tendency.keepers }}/{{ tendency.readableKeepers }} marked Keepers</template>
              </p>
            </div>
          </div>
        </section>
      </div>

      <aside class="space-y-6 lg:sticky lg:top-7">
        <section class="surface p-5 sm:p-6">
          <p class="eyebrow">What keeps recurring</p>
          <div v-if="recurring.length" class="mt-4 divide-y divide-edge">
            <div v-for="technique in recurring" :key="technique.technique_id" class="py-4 first:pt-0 last:pb-0">
              <p class="text-[17px] font-medium text-paper">{{ technique.name }}</p>
              <p class="mt-1 t-meta">
                {{ technique.corroborated_shots }} corroborated Shots across
                {{ technique.distinct_shoots }} Shoot{{ technique.distinct_shoots === 1 ? '' : 's' }}
              </p>
              <p class="mt-2 t-meta text-neutral-300">{{ repeatabilityEvidence(technique) }}</p>
            </div>
          </div>
          <p v-else class="mt-4 t-body">No Technique has reached recurring Evidence yet.</p>
        </section>

        <section class="rounded-[20px] border border-dashed border-edge-strong p-5 sm:p-6">
          <p class="eyebrow">What Shoots refuses to guess</p>
          <template v-if="unknowns.length">
            <p class="mt-3 t-body">The current record cannot support claims about:</p>
            <ul class="mt-4 space-y-2">
              <li v-for="unknown in unknowns" :key="unknown" class="flex gap-3 t-body text-neutral-300">
                <span class="text-muted">—</span><span>{{ unknown }}</span>
              </li>
            </ul>
          </template>
          <p v-else class="mt-3 t-body">No declared blind spot is present in the current Profile. Model-read claims are still opinions with provenance.</p>
        </section>
      </aside>
    </div>

    <section class="mt-10 border-t border-edge pt-4">
      <DisclosureRow label="Evidence and Experiment records" :count="pastExperiments.length">
        <div class="space-y-10 py-3">
          <TendencyProfile />
          <TechniqueMap />
          <section v-if="pastExperiments.length">
            <h2 class="t-title">Experiment Records</h2>
            <div class="mt-4">
              <ExperimentRecord v-for="experiment in pastExperiments" :key="experiment.id" :experiment="experiment" />
            </div>
          </section>
        </div>
      </DisclosureRow>

      <DisclosureRow label="Phone Source, Drive, and notifications">
        <div class="grid gap-7 py-2 sm:grid-cols-2">
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
            <a v-if="driveUrl" :href="driveUrl" target="_blank" rel="noopener" class="block t-body text-neutral-300 hover:text-paper">
              Open the Shoots Drive folder ↗
            </a>
            <button v-if="push === 'off'" type="button" class="block t-body text-neutral-300 hover:text-paper" :disabled="busy === 'push'" @click="enablePush">
              {{ busy === 'push' ? 'Asking…' : 'Turn on notifications' }}
            </button>
            <p v-else-if="push === 'on'" class="t-body text-muted">Notifications are on for this device.</p>
            <p v-else-if="push === 'denied'" class="t-body text-muted">This browser blocks notifications.</p>
            <button type="button" class="block t-body text-neutral-300 hover:text-paper" :disabled="busy === 'sync' || !connected" @click="sync">
              {{ busy === 'sync' ? 'Checking…' : 'Check the Drive folder now' }}
            </button>
            <button type="button" class="block t-body text-muted hover:text-paper md:hidden" @click="signOut">Sign out</button>
          </div>
        </div>
      </DisclosureRow>

      <DisclosureRow label="Agent activity" count="audit">
        <AgentLog :limit="60" />
      </DisclosureRow>
    </section>
  </div>
</template>
