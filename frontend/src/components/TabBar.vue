<script>
import ShootButton from '@/components/ShootButton.vue'

const TABS = [
  { name: 'dashboard', label: 'Quest', icon: 'M12 3l2.5 5 5.5.8-4 3.9.9 5.5L12 15.6 7.1 18.2l.9-5.5-4-3.9L9.5 8z' },
  { name: 'map', label: 'Map', icon: 'M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2zM9 4v14M15 6v14' },
  { name: 'shots', label: 'Shots', icon: 'M4 5h16v14H4zM4 15l4-4 4 4 3-3 5 5' },
  { name: 'feed', label: 'Feed', icon: 'M4 6h16M4 12h10M4 18h13' },
]

/** Phone-first navigation: fixed bottom bar with the Shoot button in the middle. */
export default {
  name: 'TabBar',
  components: { ShootButton },
  data() {
    return { tabs: TABS }
  },
  computed: {
    current() {
      return this.$route.name
    },
  },
}
</script>

<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-20 border-t border-edge bg-ink/95 backdrop-blur md:hidden"
    style="padding-bottom: env(safe-area-inset-bottom)"
  >
    <div class="relative mx-auto flex h-16 max-w-lg items-center justify-around">
      <RouterLink
        v-for="(tab, i) in tabs"
        :key="tab.name"
        :to="{ name: tab.name }"
        class="flex w-16 flex-col items-center gap-0.5 text-[11px]"
        :class="[current === tab.name ? 'text-neutral-100' : 'text-neutral-500', i === 2 ? 'ml-14' : '']"
      >
        <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
          <path :d="tab.icon" />
        </svg>
        {{ tab.label }}
      </RouterLink>
      <div class="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/3">
        <ShootButton floating />
      </div>
    </div>
  </nav>
</template>
