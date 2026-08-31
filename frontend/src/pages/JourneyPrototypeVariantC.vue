<script>
export default {
  name: 'JourneyPrototypeVariantC',
  props: {
    story: { type: Object, required: true },
  },
  emits: ['download', 'open-story', 'open-evidence'],
  methods: {
    pageClass(index) {
      return [
        '-translate-x-[16%] rotate-[-7deg] opacity-75',
        'translate-x-[16%] rotate-[7deg] opacity-80',
        'z-10 translate-y-2',
      ][index] || 'hidden'
    },
  },
}
</script>

<template>
  <section class="relative overflow-hidden rounded-[30px] border border-edge bg-[radial-gradient(circle_at_75%_20%,rgba(240,180,41,0.11),transparent_34%),linear-gradient(150deg,#17171c,#0d0d10_62%)] p-5 sm:p-8 lg:p-12">
    <div class="grid gap-10 lg:min-h-[570px] lg:grid-cols-[minmax(360px,0.86fr)_minmax(0,1.14fr)] lg:items-center">
      <div class="relative z-20">
        <p class="eyebrow text-accent">Journey · {{ story.artifactStatus }}</p>
        <h1 class="mt-4 text-[39px] leading-[1.01] font-medium tracking-[-0.045em] text-paper sm:text-[50px] lg:text-[58px]" style="font-family: 'Iowan Old Style', 'Palatino Linotype', Georgia, serif">
          Your work came back as a story you can keep.
        </h1>
        <p class="mt-5 max-w-lg text-[15px] leading-7 text-neutral-300">{{ story.summary }}</p>

        <div class="mt-6 flex flex-wrap gap-2">
          <span class="rounded-full border border-edge-strong bg-black/20 px-3 py-2 text-[11px] text-neutral-300">
            <strong class="t-num mr-1 text-paper">{{ story.shotCount }}</strong> Shots
          </span>
          <span class="rounded-full border border-edge-strong bg-black/20 px-3 py-2 text-[11px] text-neutral-300">
            <strong class="t-num mr-1 text-paper">{{ story.sceneCount }}</strong> Scenes
          </span>
          <span class="rounded-full border border-edge-strong bg-black/20 px-3 py-2 text-[11px] text-neutral-300">
            <strong class="t-num mr-1 text-paper">{{ story.accountedLabel }}</strong> accounted
          </span>
        </div>

        <div class="mt-7 grid gap-3 sm:grid-cols-2">
          <button type="button" class="btn" @click="$emit('open-story')">Open visual story</button>
          <button type="button" class="btn-quiet" :disabled="!story.storyReady || story.downloading" @click="$emit('download')">
            {{ story.downloading ? 'Preparing images…' : story.storyReady ? 'Download images' : 'Choose an opening Shot' }}
          </button>
        </div>
        <button type="button" class="tap-target mt-2 text-[13px] text-muted hover:text-paper" @click="$emit('open-evidence')">
          Read the Evidence and limits ↓
        </button>
      </div>

      <div class="relative mx-auto h-[390px] w-full max-w-[520px] sm:h-[500px]">
        <div class="absolute inset-x-[12%] bottom-3 top-3 rounded-[28px] border border-white/10 bg-black/35 shadow-[0_35px_90px_rgba(0,0,0,0.65)]" />
        <figure
          v-for="(page, index) in story.storyPages.slice(0, 3)"
          :key="page.id"
          class="absolute left-[18%] top-[4%] h-[88%] w-[64%] overflow-hidden rounded-[22px] border border-white/15 bg-panel shadow-[0_26px_70px_rgba(0,0,0,0.55)] transition-transform"
          :class="pageClass(index)"
        >
          <img :src="page.url" :alt="page.alt" class="h-full w-full object-cover" />
          <figcaption class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/55 to-transparent px-4 pb-4 pt-14 text-[12px] font-medium text-white">
            {{ page.title }}
          </figcaption>
        </figure>
        <div v-if="!story.storyPages.length" class="absolute inset-[15%] flex items-center justify-center rounded-[24px] border border-dashed border-edge-strong text-center t-meta">
          Your story preview will appear after you choose the opening Shot.
        </div>
        <span class="absolute bottom-0 right-[8%] z-20 rounded-full bg-paper px-4 py-2 text-[10px] font-bold tracking-[0.13em] text-ink uppercase shadow-xl">
          {{ story.storyPages.length }} page preview
        </span>
      </div>
    </div>

    <div class="mt-8 grid gap-4 border-t border-edge pt-6 sm:grid-cols-[1fr_auto] sm:items-center">
      <div>
        <p class="eyebrow">One optional next question</p>
        <p class="mt-2 text-[13px] leading-5 text-neutral-300">{{ story.nextAction }}</p>
      </div>
      <RouterLink v-if="story.recordTarget" :to="story.recordTarget" class="btn-quiet">Open Shoot Record</RouterLink>
    </div>
  </section>
</template>
