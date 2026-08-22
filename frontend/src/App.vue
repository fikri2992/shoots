<script>
import { mapActions, mapState } from 'pinia'

import TabBar from '@/components/TabBar.vue'
import ShootButton from '@/components/ShootButton.vue'
import { useAuthStore } from '@/stores/auth'
import { useShootsStore } from '@/stores/shoots'

const NAV = [
  { name: 'dashboard', label: 'Quest' },
  { name: 'map', label: 'Map' },
  { name: 'shots', label: 'Shots' },
  { name: 'feed', label: 'Feed' },
]

export default {
  name: 'App',
  components: { ShootButton, TabBar },
  data() {
    return { nav: NAV }
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
      class="sticky top-0 z-10 flex h-12 items-center justify-between border-b border-edge bg-ink/95 px-4 backdrop-blur md:px-6"
    >
      <div class="flex items-center gap-5">
        <RouterLink to="/" class="font-semibold tracking-tight">Shoots</RouterLink>
        <nav class="hidden items-center gap-4 text-sm md:flex">
          <RouterLink
            v-for="item in nav"
            :key="item.name"
            :to="{ name: item.name }"
            class="text-neutral-400 hover:text-neutral-100"
            active-class="text-neutral-100"
          >
            {{ item.label }}
          </RouterLink>
        </nav>
      </div>
      <div class="flex items-center gap-3 text-sm">
        <div class="hidden md:block"><ShootButton /></div>
        <span class="hidden text-neutral-400 sm:inline">{{ displayName }}</span>
        <button class="text-neutral-400 hover:text-neutral-100" @click="signOut">Sign out</button>
      </div>
    </header>

    <main class="flex-1">
      <RouterView />
    </main>

    <TabBar v-if="isAuthenticated" />
  </div>
</template>
