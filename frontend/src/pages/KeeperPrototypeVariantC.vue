<script>
export default {
  name: 'KeeperPrototypeVariantC',
  props: {
    shots: { type: Array, required: true },
    keeperIds: { type: Array, required: true },
  },
  emits: ['toggle-keeper'],
  methods: {
    marked(id) {
      return this.keeperIds.includes(id)
    },
  },
}
</script>

<template>
  <article class="min-h-full bg-ink pb-28">
    <header class="border-b border-edge px-5 pb-5 pt-6">
      <div class="flex items-center gap-3">
        <button type="button" class="tap-target text-paper" aria-label="Back to Now">
          <svg aria-hidden="true" viewBox="0 0 24 24" class="h-6 w-6 fill-none stroke-current stroke-2">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>
        <div class="min-w-0 flex-1">
          <p class="eyebrow text-accent">Shoot record · settled</p>
          <h1 class="mt-2 text-[24px] leading-7 font-semibold tracking-[-0.03em] text-paper">Saturday market</h1>
        </div>
        <span class="flex h-10 w-10 items-center justify-center rounded-full border border-neutral-700 text-neutral-300">
          <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-2">
            <path d="m5 12 4 4L19 6" />
          </svg>
        </span>
      </div>
    </header>

    <div class="px-5 pt-6">
      <section class="rounded-[22px] border border-neutral-700 bg-[linear-gradient(145deg,rgba(255,255,255,0.055),rgba(255,255,255,0.015))] p-5">
        <p class="eyebrow">Autonomous job complete</p>
        <div class="mt-4 grid grid-cols-3 gap-3">
          <div>
            <p class="t-num text-[23px] font-semibold text-paper">4/4</p>
            <p class="mt-1 text-[11px] text-muted">Runs settled</p>
          </div>
          <div>
            <p class="t-num text-[23px] font-semibold text-paper">2</p>
            <p class="mt-1 text-[11px] text-muted">Scenes</p>
          </div>
          <div>
            <p class="t-num text-[23px] font-semibold text-paper">1</p>
            <p class="mt-1 text-[11px] text-muted">Scout outcome</p>
          </div>
        </div>
        <div class="mt-5 border-t border-edge pt-4">
          <p class="text-[14px] leading-6 text-neutral-300">The red accent repeated. Camera height varied. Scout explained the pattern without assigning homework.</p>
        </div>
        <button type="button" class="btn mt-5 w-full">Open the Shoot lesson</button>
      </section>

      <section class="mt-8">
        <p class="eyebrow">Optional · your signal</p>
        <h2 class="mt-2 text-[19px] font-semibold tracking-[-0.02em] text-paper">Mark any Shot you value.</h2>
        <p class="mt-2 text-[13px] leading-5 text-muted">The Shoot is already complete. These marks only tell Shoots what mattered to you.</p>

        <div class="mt-4 grid grid-cols-2 gap-3">
          <button
            v-for="shot in shots"
            :key="shot.id"
            type="button"
            class="group relative overflow-hidden rounded-2xl border text-left transition"
            :class="marked(shot.id) ? 'border-accent' : 'border-edge hover:border-edge-strong'"
            :aria-pressed="marked(shot.id)"
            @click="$emit('toggle-keeper', shot.id)"
          >
            <img :src="shot.image" :alt="shot.alt" class="aspect-[4/5] w-full object-cover" />
            <span
              class="absolute right-2 top-2 flex h-9 w-9 items-center justify-center rounded-full border backdrop-blur"
              :class="marked(shot.id) ? 'border-accent bg-accent text-ink' : 'border-white/20 bg-black/55 text-white'"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 stroke-current stroke-2" :class="marked(shot.id) ? 'fill-current' : 'fill-none'">
                <path d="M6 3h12v18l-6-4-6 4z" />
              </svg>
            </span>
            <span class="block border-t border-edge bg-panel px-3 py-2.5">
              <span class="block truncate text-[12px] font-medium text-paper">{{ shot.label }}</span>
              <span class="mt-0.5 block text-[10px] text-muted">{{ marked(shot.id) ? 'Keeper · yours' : 'Unknown' }}</span>
            </span>
          </button>
        </div>
      </section>

      <p v-if="keeperIds.length" class="mt-5 rounded-xl bg-accent/8 px-4 py-3 text-[12px] leading-5 text-accent">
        {{ keeperIds.length }} Keeper signal{{ keeperIds.length === 1 ? '' : 's' }} saved. A later Reproduce still needs corroborated Evidence.
      </p>
    </div>
  </article>
</template>
