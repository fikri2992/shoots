<script>
import { mapActions, mapState } from 'pinia'

import TabBar, { TABS } from '@/components/TabBar.vue'
import { useAuthStore } from '@/stores/auth'
import { useShootsStore } from '@/stores/shoots'

/**
 * Phone navigation stays in the thumb zone. Desktop gets a deliberate rail,
 * leaving the content enough width for image evidence and prose to sit beside
 * each other instead of stretching a phone column across an empty window.
 */
export default {
  name: 'App',
  components: { TabBar },
  data() {
    return { nav: TABS }
  },
  computed: {
    ...mapState(useAuthStore, ['isAuthenticated', 'displayName']),
    ...mapState(useShootsStore, ['error', 'me']),
    isSampleRecord() {
      return this.me?.record_mode === 'sample'
    },
  },
  watch: {
    isAuthenticated: {
      immediate: true,
      async handler(signedIn) {
        if (signedIn) {
          await this.fetchAll()
          this.startPolling()
        } else {
          this.stopPolling()
        }
      },
    },
  },
  mounted() {
    if ('serviceWorker' in navigator && import.meta.env.PROD) {
      navigator.serviceWorker.register('/sw.js').catch(() => {})
    }
  },
  methods: {
    ...mapActions(useAuthStore, ['logout']),
    ...mapActions(useShootsStore, ['clearError', 'fetchAll', 'startPolling', 'stopPolling']),
    async signOut() {
      await this.logout()
      this.$router.push({ name: 'login' })
    },
  },
}
</script>

<template>
  <div class="min-h-full">
    <aside
      v-if="isAuthenticated"
      class="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-edge bg-ink/94 px-5 py-7 backdrop-blur md:flex"
    >
      <RouterLink :to="{ name: 'now' }" class="block">
        <span class="eyebrow text-accent">Shoots</span>
        <span class="mt-2 block text-[20px] font-semibold tracking-[-0.03em] text-paper">Learn to see like yourself.</span>
      </RouterLink>

      <nav class="mt-10 space-y-1.5">
          <RouterLink
            v-for="item in nav"
            :key="item.name"
            :to="{ name: item.name }"
            class="flex items-center gap-3 rounded-xl border px-3 py-3 text-sm transition hover:bg-panel hover:text-paper"
            :class="$route.name === item.name || ($route.name === 'shot' && item.name === 'shots') || ($route.name === 'shoot-record' && item.name === 'now') ? 'border-edge bg-panel text-paper' : 'border-transparent text-muted'"
          >
            <span
              class="h-1.5 w-1.5 rounded-full"
              :class="$route.name === item.name || ($route.name === 'shot' && item.name === 'shots') || ($route.name === 'shoot-record' && item.name === 'now') ? 'bg-accent' : 'bg-edge-strong'"
            />
            {{ item.label }}
          </RouterLink>
      </nav>

      <p class="mt-8 border-l border-edge pl-3 t-meta">
        {{ isSampleRecord
          ? 'This fixture shows the interface only. It does not contain agent work.'
          : 'Shoots remembers what you make and points out what keeps returning.' }}
      </p>

      <div class="mt-auto border-t border-edge pt-4">
        <p class="truncate text-sm text-neutral-300">{{ isSampleRecord ? 'Sample Record' : displayName }}</p>
        <button class="mt-1 t-meta hover:text-paper" @click="signOut">Sign out</button>
      </div>
    </aside>

    <main :class="isAuthenticated ? 'min-h-screen md:pl-60' : 'min-h-screen'">
      <div v-if="isAuthenticated && isSampleRecord" class="border-b border-accent/55 bg-accent/12 px-5 py-3 text-center">
        <p class="text-[13px] leading-5 text-paper">
          <strong>Sample Record.</strong> This is a hand-authored, read-only interface fixture. No agents ran, and it is not proof of a Shoots workflow.
        </p>
      </div>
      <div v-if="isAuthenticated && error" class="page-shell pt-4" role="alert" aria-live="polite">
        <div class="flex items-center gap-3 rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 t-body text-bad">
          <span class="min-w-0 flex-1">{{ error }}</span>
          <button type="button" class="tap-target shrink-0 px-2 text-paper" aria-label="Dismiss error" @click="clearError">
            Close
          </button>
        </div>
      </div>
      <RouterView />
    </main>

    <TabBar v-if="isAuthenticated" />
  </div>
</template>
