<script>
export default {
  name: 'KeeperPrototypeVariantB',
  props: {
    image: { type: String, required: true },
    marked: { type: Boolean, required: true },
  },
  emits: ['toggle-keeper'],
}
</script>

<template>
  <article class="min-h-full bg-ink pb-28">
    <header class="flex min-h-16 items-center gap-3 px-5">
      <button type="button" class="tap-target text-paper" aria-label="Back to the Shoot">
        <svg aria-hidden="true" viewBox="0 0 24 24" class="h-6 w-6 fill-none stroke-current stroke-2">
          <path d="m15 18-6-6 6-6" />
        </svg>
      </button>
      <div class="min-w-0 flex-1">
        <p class="eyebrow text-accent">Shoot complete</p>
        <p class="mt-1 truncate text-[14px] text-paper">Saturday market · 4 Shots</p>
      </div>
      <span class="rounded-full border border-edge px-2.5 py-1 text-[10px] font-semibold tracking-[0.1em] text-neutral-400 uppercase">4/4</span>
    </header>

    <div class="px-5 pb-7">
      <section class="overflow-hidden rounded-[24px] border border-edge bg-panel">
        <img :src="image" alt="Prototype market Shot" class="aspect-[4/5] w-full object-cover" />
        <div class="p-5">
          <div class="flex items-center justify-between">
            <p class="eyebrow text-accent">Keep · 1 of 4</p>
            <button type="button" class="text-[11px] text-muted">Clean image</button>
          </div>
          <h1 class="mt-3 text-[25px] leading-8 font-semibold tracking-[-0.025em] text-paper">The red umbrella gives the scene its centre.</h1>
          <p class="mt-3 t-body">Its colour separates from the market tarps, while the aisle keeps the eye moving toward it.</p>
          <div class="mt-5 grid grid-cols-3 items-center border-t border-edge pt-2">
            <button type="button" class="tap-target justify-start t-meta text-muted">Previous</button>
            <div class="flex justify-center gap-1.5" aria-label="Story step 1 of 4">
              <span class="h-1.5 w-5 rounded-full bg-accent" />
              <span v-for="step in 3" :key="step" class="h-1.5 w-1.5 rounded-full bg-edge-strong" />
            </div>
            <button type="button" class="tap-target justify-end t-meta text-accent">Next</button>
          </div>
        </div>
      </section>

      <button type="button" class="btn mt-5 w-full">Return to the Shoot Record</button>

      <section class="mt-5 border-t border-edge pt-5">
        <template v-if="!marked">
          <p class="text-[15px] font-medium text-paper">Did this Shot matter to you?</p>
          <p class="mt-2 text-[13px] leading-5 text-muted">
            Optional. A Keeper tells Shoots what you value. Leaving it alone stays unknown, never rejected.
          </p>
          <button
            type="button"
            class="mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl border border-edge-strong px-3.5 text-[13px] text-neutral-300 transition hover:text-paper"
            @click="$emit('toggle-keeper')"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-2">
              <path d="M6 3h12v18l-6-4-6 4z" />
            </svg>
            Mark as Keeper
          </button>
        </template>
        <template v-else>
          <div class="flex items-start gap-3">
            <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent/12 text-accent">
              <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-current stroke-current stroke-2">
                <path d="M6 3h12v18l-6-4-6 4z" />
              </svg>
            </span>
            <div class="min-w-0 flex-1">
              <p class="text-[15px] font-medium text-paper">Keeper · yours</p>
              <p class="mt-1 text-[13px] leading-5 text-muted">Shoots can use this as a Photographer-owned reference later.</p>
            </div>
            <button type="button" class="tap-target justify-end text-[12px] text-muted" @click="$emit('toggle-keeper')">Undo</button>
          </div>
        </template>
      </section>
    </div>
  </article>
</template>
