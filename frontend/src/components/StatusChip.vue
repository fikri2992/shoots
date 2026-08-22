<script>
const STYLES = {
  // quests
  open: 'bg-sky-900/50 text-sky-200 border-sky-800',
  passed: 'bg-emerald-900/50 text-emerald-200 border-emerald-800',
  skipped: 'bg-neutral-800 text-neutral-400 border-neutral-700',
  expired: 'bg-neutral-800 text-neutral-500 border-neutral-700',
  // skills
  unexplored: 'bg-transparent text-neutral-500 border-edge',
  attempted: 'bg-sky-900/40 text-sky-200 border-sky-800',
  practiced: 'bg-violet-900/40 text-violet-200 border-violet-800',
  solid: 'bg-emerald-900/50 text-emerald-200 border-emerald-800',
  rusty: 'bg-amber-900/40 text-amber-200 border-amber-800',
  // shots
  new: 'bg-neutral-800 text-neutral-400 border-neutral-700',
  ingested: 'bg-sky-900/40 text-sky-200 border-sky-800',
  analyzed: 'bg-emerald-900/50 text-emerald-200 border-emerald-800',
  failed: 'bg-red-900/40 text-red-200 border-red-800',
}

export default {
  name: 'StatusChip',
  props: { status: { type: String, required: true } },
  computed: {
    classes() {
      return STYLES[this.status] || STYLES.unexplored
    },
  },
}
</script>

<template>
  <span :class="['rounded-full border px-2 py-0.5 text-[11px] font-medium', classes]">
    {{ status }}
  </span>
</template>
