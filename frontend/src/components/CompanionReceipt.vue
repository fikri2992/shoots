<script>
export default {
  name: 'CompanionReceipt',
  props: {
    title: { type: String, default: 'Your Shoots loop' },
    items: { type: Array, required: true },
    compact: { type: Boolean, default: false },
  },
  computed: {
    visibleItems() {
      return this.items.filter((item) => item?.label && item?.text)
    },
  },
}
</script>

<template>
  <section
    class="overflow-hidden rounded-[22px] border border-edge bg-[linear-gradient(145deg,rgba(255,255,255,0.055),rgba(255,255,255,0.015))]"
    :aria-label="title"
  >
    <div class="border-b border-edge px-5 py-4 sm:px-6" :class="compact ? '' : 'sm:py-5'">
      <p class="eyebrow text-accent">Companion receipt</p>
      <h2 class="mt-2 font-medium tracking-[-0.02em] text-paper" :class="compact ? 'text-[17px]' : 'text-[20px]'">
        {{ title }}
      </h2>
    </div>

    <ol class="divide-y divide-edge px-5 sm:px-6">
      <li
        v-for="item in visibleItems"
        :key="`${item.label}:${item.text}`"
        class="flex gap-4 py-4"
        :aria-current="item.state === 'current' ? 'step' : undefined"
      >
        <span
          class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border"
          :class="item.state === 'done'
            ? 'border-accent bg-accent text-ink'
            : item.state === 'current'
              ? 'border-paper bg-paper text-ink'
              : item.state === 'limit'
                ? 'border-neutral-600 text-neutral-400'
                : 'border-edge-strong text-muted'"
          aria-hidden="true"
        >
          <svg v-if="item.state === 'done'" viewBox="0 0 24 24" class="h-3.5 w-3.5 fill-none stroke-current stroke-[2.6]">
            <path d="m5 12 4 4L19 6" />
          </svg>
          <span v-else class="h-1.5 w-1.5 rounded-full bg-current" />
        </span>
        <div class="min-w-0">
          <p class="eyebrow" :class="item.state === 'current' ? 'text-paper' : ''">{{ item.label }}</p>
          <p class="mt-1 text-[13px] leading-5" :class="item.state === 'limit' ? 'text-muted' : 'text-neutral-300'">
            {{ item.text }}
          </p>
        </div>
      </li>
    </ol>
  </section>
</template>
