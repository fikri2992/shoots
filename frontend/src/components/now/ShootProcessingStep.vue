<script>
export default {
  name: 'ShootProcessingStep',
  props: {
    shoot: { type: Object, required: true },
    members: { type: Array, default: () => [] },
  },
  computed: {
    shotCount() {
      return this.shoot.ordered_shot_ids?.length || this.members.length
    },
    sceneCount() {
      return this.shoot.ordered_scene_ids?.length || 0
    },
    readCount() {
      return this.members.filter((view) => view.analysis).length
    },
    failedCount() {
      return this.members.filter((view) => view.shot?.status === 'failed').length
    },
    waitingCount() {
      return Math.max(0, this.shotCount - this.readCount - this.failedCount)
    },
    progressPercent() {
      if (!this.shotCount) return 0
      return Math.min(100, Math.round(((this.readCount + this.failedCount) / this.shotCount) * 100))
    },
    title() {
      if (this.shoot.status === 'open') return 'Shoots is keeping this Shoot together.'
      if (this.shoot.status === 'closing') return 'Finishing this Shoot.'
      return 'Preparing this Shoot Record.'
    },
    explanation() {
      if (this.shoot.status === 'open') {
        return 'Shoots keeps this Shoot open for 30 minutes after the latest Shot so Camera Shots from the same outing stay together.'
      }
      if (this.shoot.status === 'closing') {
        return 'Every member Run must settle or end as unreadable before Shoots creates the record.'
      }
      return 'The Shoot is settled, but its matching record is not available yet. Shoots will not substitute an older result.'
    },
  },
}
</script>

<template>
  <section class="page-shell py-8 md:py-12">
    <div class="surface-active p-6 sm:p-8">
      <p class="eyebrow text-accent">Current Shoot</p>
      <h1 class="mt-4 t-hero">{{ title }}</h1>
      <p class="mt-4 max-w-2xl t-body text-neutral-300">{{ explanation }}</p>

      <div class="mt-7 max-w-xl">
        <div class="flex items-center justify-between gap-4 t-meta">
          <span>{{ readCount }} read<span v-if="failedCount"> · {{ failedCount }} unreadable</span></span>
          <span>{{ waitingCount }} still working</span>
        </div>
        <div
          class="mt-2 h-2 overflow-hidden rounded-full bg-neutral-800"
          role="progressbar"
          :aria-valuenow="progressPercent"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`${readCount} of ${shotCount} Shots read`"
        >
          <div class="h-full rounded-full bg-accent transition-all" :style="{ width: `${progressPercent}%` }" />
        </div>
      </div>

      <div class="mt-7 grid grid-cols-3 gap-3 border-y border-edge py-5 sm:max-w-xl">
        <div>
          <p class="t-num text-[22px] font-semibold text-paper">{{ shotCount }}</p>
          <p class="mt-1 text-[11px] text-muted">Shots here</p>
        </div>
        <div>
          <p class="t-num text-[22px] font-semibold text-paper">{{ readCount }}</p>
          <p class="mt-1 text-[11px] text-muted">Shots read</p>
        </div>
        <div>
          <p class="t-num text-[22px] font-semibold text-paper">{{ waitingCount }}</p>
          <p class="mt-1 text-[11px] text-muted">Still working</p>
        </div>
      </div>

      <p class="mt-5 t-meta">
        {{ sceneCount }} {{ sceneCount === 1 ? 'Scene' : 'Scenes' }} so far. You can leave. Shoots will put the finished Shoot here and will never substitute an older result.
      </p>
    </div>
  </section>
</template>
