<script>
export default {
  name: 'KeeperPrototypeVariantD',
  props: {
    shots: { type: Array, required: true },
    selectedShot: { type: Object, default: null },
    keeperIds: { type: Array, required: true },
  },
  emits: ['open-shot', 'close-shot', 'toggle-keeper'],
  computed: {
    selectedMarked() {
      return this.selectedShot ? this.keeperIds.includes(this.selectedShot.id) : false
    },
    selectedIndex() {
      return this.selectedShot ? this.shots.findIndex((shot) => shot.id === this.selectedShot.id) : -1
    },
  },
  methods: {
    marked(id) {
      return this.keeperIds.includes(id)
    },
  },
}
</script>

<template>
  <article class="min-h-full bg-ink pb-28">
    <template v-if="!selectedShot">
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
          <p class="mt-5 border-t border-edge pt-4 text-[14px] leading-6 text-neutral-300">
            The red accent repeated. Camera height varied. Scout explained the pattern without assigning homework.
          </p>
          <button type="button" class="btn mt-5 w-full">Open the Shoot lesson</button>
        </section>

        <section class="mt-8">
          <p class="eyebrow">Shots from this Shoot</p>
          <h2 class="mt-2 text-[19px] font-semibold tracking-[-0.02em] text-paper">Open one for the full read.</h2>
          <p class="mt-2 text-[13px] leading-5 text-muted">Keeper stays inside Shot detail as a quiet Photographer choice.</p>

          <div class="mt-4 grid grid-cols-2 gap-3">
            <button
              v-for="shot in shots"
              :key="shot.id"
              type="button"
              class="group relative overflow-hidden rounded-2xl border border-edge text-left transition hover:border-edge-strong"
              @click="$emit('open-shot', shot.id)"
            >
              <img :src="shot.image" :alt="shot.alt" class="aspect-[4/5] w-full object-cover" />
              <span
                class="absolute right-2 top-2 flex h-9 w-9 items-center justify-center rounded-full border backdrop-blur"
                :class="marked(shot.id) ? 'border-accent bg-accent text-ink' : 'border-white/20 bg-black/55 text-white'"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  class="h-4 w-4 stroke-current stroke-2"
                  :class="marked(shot.id) ? 'fill-current' : 'fill-none'"
                >
                  <path d="M6 3h12v18l-6-4-6 4z" />
                </svg>
              </span>
              <span class="block border-t border-edge bg-panel px-3 py-2.5">
                <span class="block truncate text-[12px] font-medium text-paper">{{ shot.label }}</span>
                <span class="mt-0.5 block text-[10px] text-muted">{{ marked(shot.id) ? 'Keeper · yours' : 'Open Shot' }}</span>
              </span>
            </button>
          </div>
        </section>
      </div>
    </template>

    <template v-else>
      <header class="flex min-h-16 items-center gap-3 border-b border-edge px-5">
        <button type="button" class="tap-target text-paper" aria-label="Back to Shoot Record" @click="$emit('close-shot')">
          <svg aria-hidden="true" viewBox="0 0 24 24" class="h-6 w-6 fill-none stroke-current stroke-2">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>
        <div class="min-w-0 flex-1">
          <p class="truncate text-[15px] font-medium text-paper">{{ selectedShot.label }}</p>
          <p class="mt-0.5 text-[11px] text-muted">Shot {{ selectedIndex + 1 }} of 4 · Shoot settled</p>
        </div>
        <button
          type="button"
          class="flex min-h-11 items-center gap-2 rounded-full border px-3 text-[12px] transition"
          :class="selectedMarked ? 'border-accent/60 bg-accent/10 text-accent' : 'border-edge-strong text-muted hover:text-paper'"
          :aria-pressed="selectedMarked"
          @click="$emit('toggle-keeper', selectedShot.id)"
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 stroke-current stroke-2" :class="selectedMarked ? 'fill-current' : 'fill-none'">
            <path d="M6 3h12v18l-6-4-6 4z" />
          </svg>
          {{ selectedMarked ? 'Keeper' : 'Keep' }}
        </button>
      </header>

      <section class="relative bg-black">
        <img :src="selectedShot.image" :alt="selectedShot.alt" class="aspect-[4/5] w-full object-cover" />
        <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent px-5 pb-5 pt-20">
          <div class="flex items-center justify-between">
            <span class="rounded-full border border-white/15 bg-black/55 px-3 py-1.5 text-[10px] font-semibold tracking-[0.12em] text-white/80 uppercase backdrop-blur">Visual story</span>
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
              <p class="text-[14px] font-medium text-paper">The Shoot remains settled</p>
              <p class="mt-0.5 text-[12px] leading-5 text-muted">Keeper changes your signal, not the autonomous result.</p>
            </div>
          </div>
          <button type="button" class="btn-quiet mt-4 w-full" @click="$emit('close-shot')">Return to Shoot Record</button>
        </section>

        <p v-if="selectedMarked" class="mt-4 text-[12px] leading-5 text-accent">
          Saved as your signal. A later Reproduce still needs corroborated Evidence.
        </p>
      </div>
    </template>
  </article>
</template>
