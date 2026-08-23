<script>
import { mapActions, mapState } from 'pinia'

import AgentLog from '@/components/AgentLog.vue'
import DisclosureRow from '@/components/DisclosureRow.vue'
import SkillBars from '@/components/SkillBars.vue'
import { useAuthStore } from '@/stores/auth'
import { useShootsStore } from '@/stores/shoots'

/** Where the user has got to, and what the agents did to get them there. */
export default {
  name: 'JourneyPage',
  components: { AgentLog, DisclosureRow, SkillBars },
  computed: {
    ...mapState(useShootsStore, ['pastQuests', 'me', 'push', 'busy', 'connected']),
    quests() {
      return this.pastQuests.map((q) => ({
        id: q.id,
        title: q.title,
        status: q.status,
        best: (q.verdicts || []).filter((v) => v.passed).length ? 'passed' : q.status,
        shotId: (q.verdicts || [])[q.verdicts.length - 1]?.shot_id || '',
        when: new Date(q.issued_at).toLocaleDateString(),
      }))
    },
    driveUrl() {
      return this.me?.drive_folder_id ? `https://drive.google.com/drive/folders/${this.me.drive_folder_id}` : ''
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['sync', 'enablePush']),
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

    <div class="gutter mt-8"><SkillBars /></div>

    <section v-if="quests.length" class="gutter mt-12">
      <h2 class="t-title">Quests</h2>
      <ul class="mt-4 space-y-3">
        <li v-for="q in quests" :key="q.id" class="flex items-baseline gap-3">
          <span class="w-14 shrink-0 t-meta">{{ q.when }}</span>
          <RouterLink
            v-if="q.shotId"
            :to="{ name: 'frame', params: { shotId: q.shotId } }"
            class="min-w-0 flex-1 truncate t-body"
            :class="q.best === 'passed' ? 'text-neutral-100' : 'text-neutral-500'"
          >
            {{ q.title }}
          </RouterLink>
          <span v-else class="min-w-0 flex-1 truncate t-body" :class="q.best === 'passed' ? 'text-neutral-100' : 'text-neutral-500'">
            {{ q.title }}
          </span>
          <span class="t-meta" :class="q.best === 'passed' ? 'text-good' : ''">{{ q.best }}</span>
        </li>
      </ul>
    </section>

    <section class="gutter mt-12">
      <DisclosureRow label="What the agents did" count="log">
        <AgentLog :limit="60" />
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
