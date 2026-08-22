<script>
import { mapActions, mapState } from 'pinia'

import ActivityFeed from '@/components/ActivityFeed.vue'
import QuestCard from '@/components/QuestCard.vue'
import SkillMap from '@/components/SkillMap.vue'
import { useShootsStore } from '@/stores/shoots'

/**
 * The phone's home screen: today's quest, then what the agents are doing.
 * One column under 768px; quest left, map + feed right above that.
 */
export default {
  name: 'DashboardPage',
  components: { ActivityFeed, QuestCard, SkillMap },
  computed: {
    ...mapState(useShootsStore, ['quest', 'quests', 'connected', 'busy', 'error', 'loading', 'me', 'push']),
    recentClosed() {
      return this.quests.filter((q) => q.status !== 'open').slice(0, 3)
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['connect', 'sync', 'issueQuest', 'enablePush', 'checkPush']),
  },
  created() {
    this.checkPush()
  },
}
</script>

<template>
  <div class="mx-auto max-w-5xl p-4 pb-24 md:pb-8">
    <p v-if="error" class="mb-3 rounded-lg border border-red-900 bg-red-950/40 px-3 py-2 text-sm text-red-200">
      {{ error }}
    </p>

    <section v-if="!connected && !loading" class="mb-4 rounded-xl border border-dashed border-edge-strong p-5">
      <h2 class="text-lg font-semibold">Connect your Drive</h2>
      <p class="mt-1 text-sm text-neutral-400">
        Shoots creates a <span class="font-mono">Shoots</span> folder in your Google Drive and shares it with
        its reader. Anything you drop there gets analysed. That is the whole setup.
      </p>
      <button
        type="button"
        class="mt-3 rounded-lg bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 hover:bg-white disabled:opacity-50"
        :disabled="busy === 'connect'"
        @click="connect"
      >
        {{ busy === 'connect' ? 'Connecting…' : 'Connect Drive' }}
      </button>
    </section>

    <div class="grid gap-4 md:grid-cols-5">
      <div class="space-y-4 md:col-span-3">
        <QuestCard v-if="quest" :quest="quest" />
        <section v-else-if="connected" class="rounded-xl border border-edge bg-panel p-5">
          <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Today's quest</p>
          <p class="mt-2 text-sm text-neutral-300">
            No open quest. The Scout issues one every morning, or right now if you ask.
          </p>
          <button
            type="button"
            class="mt-3 rounded-lg border border-edge-strong px-3 py-2 text-sm hover:bg-edge disabled:opacity-50"
            :disabled="busy === 'issue'"
            @click="issueQuest()"
          >
            {{ busy === 'issue' ? 'Scouting…' : 'Issue a quest now' }}
          </button>
        </section>

        <div v-if="recentClosed.length" class="space-y-2">
          <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Recent</p>
          <QuestCard v-for="q in recentClosed" :key="q.id" :quest="q" compact />
        </div>
      </div>

      <div class="space-y-4 md:col-span-2">
        <div v-if="connected" class="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-edge bg-panel px-4 py-3 text-sm">
          <a :href="`https://drive.google.com/drive/folders/${me.drive_folder_id}`" target="_blank" rel="noopener" class="text-neutral-300 hover:text-neutral-100">
            Open Drive folder
          </a>
          <div class="flex items-center gap-3">
            <button
              v-if="push === 'off'"
              type="button"
              class="text-neutral-400 hover:text-neutral-100 disabled:opacity-50"
              :disabled="busy === 'push'"
              @click="enablePush"
            >
              {{ busy === 'push' ? 'Enabling…' : 'Enable notifications' }}
            </button>
            <span v-else-if="push === 'on'" class="text-[11px] text-emerald-400">notifications on</span>
            <span v-else-if="push === 'denied'" class="text-[11px] text-neutral-600">notifications blocked</span>
            <button type="button" class="text-neutral-400 hover:text-neutral-100 disabled:opacity-50" :disabled="busy === 'sync'" @click="sync">
              {{ busy === 'sync' ? 'Syncing…' : 'Sync now' }}
            </button>
          </div>
        </div>
        <RouterLink :to="{ name: 'map' }" class="block"><SkillMap summary /></RouterLink>
        <ActivityFeed :limit="12" />
      </div>
    </div>
  </div>
</template>
