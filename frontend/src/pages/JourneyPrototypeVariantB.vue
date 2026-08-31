<script>
export default {
  name: 'JourneyPrototypeVariantB',
  props: {
    story: { type: Object, required: true },
  },
  emits: ['download', 'open-story', 'open-evidence'],
}
</script>

<template>
  <section>
    <div class="grid gap-7 lg:grid-cols-[minmax(0,0.84fr)_minmax(0,1.16fr)] lg:items-end">
      <header>
        <div class="flex items-center gap-3">
          <span class="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-ink">
            <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-[2.4]">
              <path d="m5 12 4 4L19 6" />
            </svg>
          </span>
          <p class="eyebrow text-accent">{{ story.statusLabel }}</p>
        </div>
        <h1 class="mt-5 text-[38px] leading-[1.01] font-medium tracking-[-0.045em] text-paper sm:text-[48px] lg:text-[58px]" style="font-family: 'Iowan Old Style', 'Palatino Linotype', Georgia, serif">
          A whole Shoot, handled in the background.
        </h1>
        <p class="mt-5 max-w-xl text-[16px] leading-7 text-neutral-300">{{ story.summary }}</p>
      </header>

      <div class="grid h-[320px] grid-cols-6 grid-rows-2 gap-2 overflow-hidden rounded-[24px] bg-panel p-2 sm:h-[400px]">
        <figure
          v-for="(shot, index) in story.shots.slice(0, 5)"
          :key="shot.id"
          class="relative overflow-hidden rounded-[16px] bg-panel-2"
          :class="index === 0 ? 'col-span-4 row-span-2' : 'col-span-2'"
        >
          <img :src="shot.url" :alt="shot.alt" class="h-full w-full object-cover" />
          <span v-if="shot.keeper" class="absolute right-2 top-2 rounded-full bg-accent px-2 py-1 text-[9px] font-bold tracking-[0.1em] text-ink uppercase">Keeper</span>
        </figure>
        <div v-if="!story.shots.length" class="col-span-6 row-span-2 flex items-center justify-center t-meta">Shots will fill this Shoot receipt.</div>
      </div>
    </div>

    <div class="mt-8 overflow-hidden rounded-[24px] border border-edge bg-panel">
      <div class="flex items-center justify-between gap-4 border-b border-edge px-5 py-4 sm:px-6">
        <div>
          <p class="eyebrow">Autonomous work receipt</p>
          <p class="mt-1 text-[13px] text-neutral-300">The durable result, not a chat transcript.</p>
        </div>
        <span class="t-num text-[12px] text-muted">{{ story.accountedLabel }} accounted for</span>
      </div>

      <ol class="grid divide-y divide-edge md:grid-cols-5 md:divide-x md:divide-y-0">
        <li v-for="(step, index) in story.workflow" :key="step.label" class="relative px-5 py-4 md:px-4 md:py-5">
          <div class="flex items-baseline justify-between gap-3 md:block">
            <p class="t-num text-[23px] font-semibold text-paper">{{ step.value }}</p>
            <span class="text-[10px] text-muted md:absolute md:right-3 md:top-3">0{{ index + 1 }}</span>
          </div>
          <p class="mt-1 text-[11px] font-semibold tracking-[0.1em] text-neutral-300 uppercase">{{ step.label }}</p>
          <p class="mt-1 text-[11px] leading-4 text-muted">{{ step.detail }}</p>
        </li>
      </ol>

      <div class="grid gap-5 border-t border-edge p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div>
          <p class="eyebrow text-accent">What the Photographer receives</p>
          <p class="mt-2 text-[19px] font-medium leading-7 text-paper">{{ story.headline }}</p>
          <p class="mt-2 text-[13px] leading-5 text-muted">{{ story.resultSummary }}</p>
        </div>
        <div class="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
          <button type="button" class="btn" @click="$emit('open-story')">Open visual story</button>
          <button type="button" class="btn-quiet" :disabled="!story.storyReady || story.downloading" @click="$emit('download')">
            {{ story.downloading ? 'Preparing images…' : story.storyReady ? 'Download images' : 'Not ready' }}
          </button>
          <button type="button" class="btn-quiet" @click="$emit('open-evidence')">See Evidence</button>
        </div>
      </div>
    </div>

    <div class="mt-5 flex flex-col justify-between gap-3 rounded-[18px] border border-dashed border-edge-strong px-5 py-4 sm:flex-row sm:items-center">
      <div>
        <p class="eyebrow">Optional, never homework</p>
        <p class="mt-1 text-[13px] text-neutral-300">{{ story.nextAction }}</p>
      </div>
      <RouterLink v-if="story.recordTarget" :to="story.recordTarget" class="tap-target shrink-0 text-[13px] text-accent hover:text-paper">Inspect the settled record →</RouterLink>
    </div>
  </section>
</template>
