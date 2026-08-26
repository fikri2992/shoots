<script>
/**
 * Three tabs, no floating camera button. Shooting belongs to the experiment that
 * asked for it — a global shutter here would skip the pre-flight check, which
 * is the whole point of shooting inside an experiment.
 */
export const TABS = [
  { name: 'now', label: 'Now', icon: 'M12 4v8l5 3M12 21a9 9 0 110-18 9 9 0 010 18z' },
  { name: 'shots', label: 'Shots', icon: 'M4 5h16v14H4zM4 15l4-4 4 4 3-3 5 5' },
  { name: 'journey', label: 'Journey', icon: 'M4 18l5-6 4 3 7-9' },
]

export default {
  name: 'TabBar',
  data() {
    return { tabs: TABS }
  },
  computed: {
    current() {
      return this.$route.name === 'shot' ? 'shots' : this.$route.name
    },
  },
}
</script>

<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-30 border-t border-edge bg-ink/96 backdrop-blur-xl md:hidden"
    style="padding-bottom: env(safe-area-inset-bottom)"
  >
    <div class="mx-auto flex h-[68px] max-w-lg items-stretch px-2">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.name"
        :to="{ name: tab.name }"
        class="relative flex flex-1 flex-col items-center justify-center gap-1 text-[11px]"
        :class="current === tab.name ? 'text-accent' : 'text-muted'"
      >
        <span v-if="current === tab.name" class="absolute top-0 h-0.5 w-9 rounded-full bg-accent" />
        <svg viewBox="0 0 24 24" class="h-[22px] w-[22px]" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path :d="tab.icon" />
        </svg>
        {{ tab.label }}
      </RouterLink>
    </div>
  </nav>
</template>
