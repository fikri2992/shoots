<script>
import { mapActions, mapState } from 'pinia'

import AgentLog from '@/components/AgentLog.vue'
import DisclosureRow from '@/components/DisclosureRow.vue'
import ExperimentRecord from '@/components/ExperimentRecord.vue'
import JourneyUpdate from '@/components/JourneyUpdate.vue'
import TechniqueMap from '@/components/TechniqueMap.vue'
import TendencyProfile from '@/components/TendencyProfile.vue'
import { useAuthStore } from '@/stores/auth'
import { useShootsStore } from '@/stores/shoots'

/** Where the user has got to, and what the agents did to get them there. */
export default {
  name: 'JourneyPage',
  components: {
    AgentLog,
    DisclosureRow,
    ExperimentRecord,
    JourneyUpdate,
    TechniqueMap,
    TendencyProfile,
  },
  computed: {
    ...mapState(useShootsStore, [
      'pastExperiments',
      'me',
      'push',
      'busy',
      'connected',
      'pairCode',
    ]),
    driveUrl() {
      return this.me?.drive_folder_id ? `https://drive.google.com/drive/folders/${this.me.drive_folder_id}` : ''
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['sync', 'enablePush', 'pairCamera']),
    ...mapActions(useAuthStore, ['logout']),
    async signOut() {
      await this.logout()
      this.$router.push({ name: 'login' })
    },
  },
}
</script>

<template>
  <div class="mx-auto w-full max-w-2xl pb-24 md:pb-10">
    <h1 class="gutter pt-8 t-hero">Journey</h1>

    <div class="gutter mt-8"><JourneyUpdate /></div>

    <div class="gutter mt-12"><TendencyProfile /></div>

    <div class="gutter mt-12"><TechniqueMap /></div>

    <!-- Each row opens into its own record: the reason, the baseline frozen
         before anything happened, the criteria, what came back, and whether
         comparable behaviour differs now. -->
    <section v-if="pastExperiments.length" class="gutter mt-12">
      <h2 class="t-title">Experiments</h2>
      <div class="mt-4">
        <ExperimentRecord v-for="q in pastExperiments" :key="q.id" :experiment="q" />
      </div>
    </section>

    <section class="gutter mt-12">
      <DisclosureRow label="What the agents did" count="log">
        <AgentLog :limit="60" />
      </DisclosureRow>

      <DisclosureRow label="Pair a camera">
        <div class="space-y-3">
          <p class="t-body text-neutral-400">
            The Shoots camera cannot sign in on its own. Ask for a code here and type it into the app once.
          </p>
          <p v-if="pairCode" class="font-mono text-3xl tracking-[0.3em] text-neutral-100">{{ pairCode.code }}</p>
          <p v-if="pairCode" class="t-meta text-neutral-500">
            Good for {{ Math.round(pairCode.expires_in_seconds / 60) }} minutes, and once.
          </p>
          <button
            type="button"
            class="block t-body text-neutral-300 hover:text-neutral-100"
            :disabled="busy === 'pair'"
            @click="pairCamera"
          >
            {{ busy === 'pair' ? 'Asking…' : pairCode ? 'Another code' : 'Show me a code' }}
          </button>
        </div>
      </DisclosureRow>

      <DisclosureRow label="Folder and notifications">
        <div class="space-y-3">
          <a v-if="driveUrl" :href="driveUrl" target="_blank" rel="noopener" class="block t-body text-neutral-300 hover:text-neutral-100">
            Open the Shoots folder in Drive ↗
          </a>
          <button
            v-if="push === 'off'"
            type="button"
            class="block t-body text-neutral-300 hover:text-neutral-100"
            :disabled="busy === 'push'"
            @click="enablePush"
          >
            {{ busy === 'push' ? 'Asking…' : 'Turn on notifications' }}
          </button>
          <p v-else-if="push === 'on'" class="t-body text-neutral-500">Notifications are on for this device.</p>
          <p v-else-if="push === 'denied'" class="t-body text-neutral-500">This browser is blocking notifications.</p>
          <button
            type="button"
            class="block t-body text-neutral-300 hover:text-neutral-100"
            :disabled="busy === 'sync' || !connected"
            @click="sync"
          >
            {{ busy === 'sync' ? 'Looking…' : 'Check the folder now' }}
          </button>
          <button type="button" class="block t-body text-neutral-500 hover:text-neutral-200 md:hidden" @click="signOut">
            Sign out
          </button>
        </div>
      </DisclosureRow>
    </section>
  </div>
</template>
