<script>
export default {
  name: 'JourneyPrototypeVariantA',
  props: {
    story: { type: Object, required: true },
  },
  emits: ['download', 'open-story', 'open-evidence'],
}
</script>

<template>
  <section class="overflow-hidden rounded-[28px] border border-edge bg-panel shadow-[0_28px_90px_rgba(0,0,0,0.32)]">
    <div class="grid lg:min-h-[620px] lg:grid-cols-[minmax(0,1.08fr)_minmax(390px,0.92fr)]">
      <div class="relative aspect-[4/3] overflow-hidden bg-panel-2 lg:aspect-auto">
        <img
          v-if="story.cover"
          :src="story.cover.url"
          :alt="story.cover.alt"
          class="h-full w-full object-cover"
        />
        <div v-else class="flex h-full items-center justify-center text-sm text-muted">Your latest Shot will appear here</div>
        <div class="absolute inset-0 bg-[linear-gradient(180deg,rgba(5,5,7,0.55),transparent_38%,rgba(5,5,7,0.78))]" />

        <div class="absolute inset-x-0 top-0 flex items-center justify-between gap-4 p-5 sm:p-6">
          <span class="rounded-full border border-white/25 bg-black/40 px-3 py-1.5 text-[10px] font-semibold tracking-[0.14em] text-white uppercase backdrop-blur">
            {{ story.statusLabel }}
          </span>
          <span class="text-[11px] text-white/75">{{ story.dateLabel }}</span>
        </div>

        <div class="absolute inset-x-0 bottom-0 flex items-end justify-between gap-4 p-5 sm:p-6">
          <div>
            <p class="text-[11px] tracking-[0.13em] text-white/70 uppercase">Latest completed work</p>
            <p class="mt-1 text-[15px] font-medium text-white">
              {{ story.shotCount }} Shots · {{ story.sceneCount }} {{ story.sceneCount === 1 ? 'Scene' : 'Scenes' }}
            </p>
          </div>
          <span v-if="story.cover?.keeper" class="rounded-full bg-accent px-3 py-1.5 text-[10px] font-bold tracking-[0.12em] text-ink uppercase">
            Your choice
          </span>
        </div>
      </div>

      <div class="flex flex-col p-5 sm:p-7 lg:p-10">
        <p class="eyebrow text-accent">Journey · your latest Shoot</p>
        <h1 class="mt-4 text-[34px] leading-[1.02] font-medium tracking-[-0.04em] text-paper sm:text-[42px] lg:text-[48px]" style="font-family: 'Iowan Old Style', 'Palatino Linotype', Georgia, serif">
          {{ story.headline }}
        </h1>
        <p class="mt-4 max-w-xl text-[15px] leading-6 text-neutral-300">
          {{ story.summary }}
        </p>

        <ol class="mt-6 grid grid-cols-4 gap-2 border-y border-edge py-4">
          <li v-for="step in story.workflow.slice(0, 4)" :key="step.label" class="min-w-0">
            <p class="t-num text-[17px] font-semibold text-paper sm:text-[20px]">{{ step.value }}</p>
            <p class="mt-1 text-[9px] leading-3 tracking-[0.08em] text-muted uppercase sm:text-[10px]">{{ step.label }}</p>
          </li>
        </ol>
        <p class="mt-3 text-[12px] leading-5 text-muted">No upload, sorting, or tagging was required.</p>

        <div class="mt-6 grid gap-3 sm:grid-cols-2">
          <button type="button" class="btn" @click="$emit('open-story')">
            <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-2">
              <path d="M4 5h16v14H4z" /><path d="m4 15 4-4 4 3 3-3 5 4" />
            </svg>
            Open visual story
          </button>
          <button type="button" class="btn-quiet" :disabled="!story.storyReady || story.downloading" @click="$emit('download')">
            <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-2">
              <path d="M12 3v12" /><path d="m7 10 5 5 5-5" /><path d="M5 21h14" />
            </svg>
            {{ story.downloading ? 'Preparing images…' : story.storyReady ? 'Download images' : 'Download unavailable' }}
          </button>
        </div>

        <div class="mt-3 flex flex-wrap items-center justify-between gap-3">
          <button type="button" class="tap-target text-[13px] text-muted hover:text-paper" @click="$emit('open-evidence')">
            See the Evidence
            <span aria-hidden="true" class="ml-2">↓</span>
          </button>
          <RouterLink v-if="story.recordTarget" :to="story.recordTarget" class="tap-target text-[13px] text-muted hover:text-paper">
            Open Shoot Record
            <span aria-hidden="true" class="ml-2">→</span>
          </RouterLink>
        </div>

        <div class="mt-auto border-t border-edge pt-5 lg:mt-8">
          <p class="eyebrow">Optional next Experiment</p>
          <p class="mt-2 text-[14px] leading-5 text-neutral-300">{{ story.nextAction }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
