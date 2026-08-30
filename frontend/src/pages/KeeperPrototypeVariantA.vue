<script>
export default {
  name: 'KeeperPrototypeVariantA',
  props: {
    image: { type: String, required: true },
    marked: { type: Boolean, required: true },
  },
  emits: ['toggle-keeper'],
}
</script>

<template>
  <article class="min-h-full bg-ink pb-28">
    <header class="flex min-h-16 items-center gap-3 border-b border-edge px-5">
      <button type="button" class="tap-target text-paper" aria-label="Back to Shots">
        <svg aria-hidden="true" viewBox="0 0 24 24" class="h-6 w-6 fill-none stroke-current stroke-2">
          <path d="m15 18-6-6 6-6" />
        </svg>
      </button>
      <div class="min-w-0 flex-1">
        <p class="truncate text-[15px] font-medium text-paper">Saturday market</p>
        <p class="mt-0.5 text-[11px] text-muted">Shot 3 of 4 · Shoot settled</p>
      </div>
      <button
        type="button"
        class="flex min-h-11 items-center gap-2 rounded-full border px-3 text-[12px] transition"
        :class="marked ? 'border-accent/60 bg-accent/10 text-accent' : 'border-edge-strong text-muted hover:text-paper'"
        :aria-pressed="marked"
        @click="$emit('toggle-keeper')"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 stroke-current stroke-2" :class="marked ? 'fill-current' : 'fill-none'">
          <path d="M6 3h12v18l-6-4-6 4z" />
        </svg>
        {{ marked ? 'Keeper' : 'Keep' }}
      </button>
    </header>

    <section class="relative bg-black">
      <img :src="image" alt="Prototype market Shot" class="aspect-[4/5] w-full object-cover" />
      <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent px-5 pb-5 pt-20">
        <div class="flex items-center justify-between">
          <span class="rounded-full border border-white/15 bg-black/55 px-3 py-1.5 text-[10px] font-semibold tracking-[0.12em] text-white/80 uppercase backdrop-blur">
            Visual story
          </span>
          <span class="text-[12px] text-white/70">1 of 4</span>
        </div>
      </div>
    </section>

    <div class="px-5 pt-6">
      <p class="eyebrow text-accent">What holds the frame</p>
      <h1 class="mt-3 text-[28px] leading-8 font-semibold tracking-[-0.03em] text-paper">One red shape cuts through the rain.</h1>
      <p class="mt-3 t-body">The umbrella stays distinct from the cooler market tarps and carries the eye down the aisle.</p>

      <div class="mt-6 flex items-center justify-between border-y border-edge py-2">
        <button type="button" class="tap-target t-meta text-muted">Previous</button>
        <div class="flex gap-1.5" aria-label="Story step 1 of 4">
          <span class="h-1.5 w-5 rounded-full bg-accent" />
          <span v-for="step in 3" :key="step" class="h-1.5 w-1.5 rounded-full bg-edge-strong" />
        </div>
        <button type="button" class="tap-target t-meta justify-end text-accent">Next</button>
      </div>

      <section class="surface-soft mt-6 p-4">
        <div class="flex items-center gap-3">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-neutral-800 text-neutral-300">
            <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-2">
              <path d="m5 12 4 4L19 6" />
            </svg>
          </span>
          <div>
            <p class="text-[14px] font-medium text-paper">The Shoot is already accounted for</p>
            <p class="mt-0.5 text-[12px] leading-5 text-muted">4 Runs settled · Scout explained one pattern</p>
          </div>
        </div>
        <button type="button" class="btn-quiet mt-4 w-full">Open Shoot Record</button>
      </section>

      <p v-if="marked" class="mt-4 text-[12px] leading-5 text-accent">
        Saved as your signal. It may support a later Reproduce after Shoots checks the Evidence.
      </p>
    </div>
  </article>
</template>
