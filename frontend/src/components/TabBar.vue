<script>
/**
 * Three tabs, no floating camera button. Shooting belongs to the experiment that
 * asked for it — a global shutter here would skip the pre-flight check, which
 * is the whole point of shooting inside a experiment.
 */
export const TABS = [
  { name: 'now', label: 'Now', icon: 'M12 4v8l5 3M12 21a9 9 0 110-18 9 9 0 010 18z' },
  { name: 'frames', label: 'Frames', icon: 'M4 5h16v14H4zM4 15l4-4 4 4 3-3 5 5' },
  { name: 'journey', label: 'Journey', icon: 'M4 18l5-6 4 3 7-9' },
]

export default {
  name: 'TabBar',
  data() {
    return { tabs: TABS }
  },
  computed: {
    current() {
      return this.$route.name === 'frame' ? 'frames' : this.$route.name
    },
  },
}
</script>

<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-20 border-t border-edge bg-ink/95 backdrop-blur md:hidden"
    style="padding-bottom: env(safe-area-inset-bottom)"
  >
    <div class="mx-auto flex h-16 max-w-lg items-stretch">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.name"
        :to="{ name: tab.name }"
        class="flex flex-1 flex-col items-center justify-center gap-1 text-[11px]"
        :class="current === tab.name ? 'text-neutral-100' : 'text-neutral-500'"
      >
        <svg viewBox="0 0 24 24" class="h-[22px] w-[22px]" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path :d="tab.icon" />
        </svg>
        {{ tab.label }}
      </RouterLink>
    </div>
  </nav>
</template>
