<script>
import { mapActions, mapState } from 'pinia'

import CoachSheet from '@/components/CoachSheet.vue'
import TabBar, { TABS } from '@/components/TabBar.vue'
import { useAuthStore } from '@/stores/auth'
import { useShootsStore } from '@/stores/shoots'

/**
 * The shell. On a phone there is no top chrome at all: every screen owns its
 * own first line, and navigation lives in the thumb zone. The desktop gets a
 * slim bar because a bottom bar on a 1280px window is silly.
 */
export default {
  name: 'App',
  components: { CoachSheet, TabBar },
  data() {
    return { nav: TABS }
  },
  computed: {
    ...mapState(useAuthStore, ['isAuthenticated', 'displayName']),
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
    ...mapActions(useShootsStore, ['fetchAll', 'startPolling', 'stopPolling']),
    async signOut() {
      await this.logout()
      this.$router.push({ name: 'login' })
    },
  },
}
</script>

<template>
  <div class="flex min-h-full flex-col">
    <header
      v-if="isAuthenticated"
      class="sticky top-0 z-20 hidden h-14 items-center justify-between border-b border-edge bg-ink/90 px-6 backdrop-blur md:flex"
    >
      <div class="flex items-center gap-6">
        <RouterLink :to="{ name: 'now' }" class="font-semibold tracking-tight">Shoots</RouterLink>
        <nav class="flex items-center gap-5 text-sm">
          <RouterLink
            v-for="item in nav"
            :key="item.name"
            :to="{ name: item.name }"
            class="text-neutral-500 hover:text-neutral-100"
            active-class="text-neutral-100"
          >
            {{ item.label }}
          </RouterLink>
        </nav>
      </div>
      <div class="flex items-center gap-4 t-meta">
        <span>{{ displayName }}</span>
        <button class="hover:text-neutral-200" @click="signOut">Sign out</button>
      </div>
    </header>

    <main class="flex-1">
      <RouterView />
    </main>

    <TabBar v-if="isAuthenticated" />
    <CoachSheet v-if="isAuthenticated" />
  </div>
</template>
