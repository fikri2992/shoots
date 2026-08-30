<script>
import VisualLoopPrototypePhoto from '@/pages/VisualLoopPrototypePhoto.vue'

export default {
  name: 'VisualLoopPrototypeVariantD',
  components: { VisualLoopPrototypePhoto },
  props: {
    image: { type: String, required: true },
    resultImages: { type: Array, required: true },
    phase: { type: String, required: true },
  },
  emits: ['choose'],
  computed: {
    isLater() {
      return ['later', 'experiment', 'settling', 'free', 'result_deliberate', 'result_free'].includes(this.phase)
    },
    dateLabel() {
      return this.isLater ? 'Saturday · 6 days later' : 'Tonight · at home'
    },
    headerTitle() {
      return {
        home: 'You used leading lines here.',
        saved: 'Saved for another day',
        dismissed: 'Review complete',
        later: 'Your next Shoot',
        experiment: 'Experiment ready',
        settling: 'Shoots is checking',
        free: 'You kept shooting',
        result_deliberate: 'What Shoots can now say',
        result_free: 'What Shoots can actually say',
      }[this.phase]
    },
  },
}
</script>

<template>
  <div class="min-h-[844px] bg-ink pb-28">
    <header class="border-b border-edge px-5 pb-4 pt-6">
      <div class="flex items-center justify-between gap-4">
        <p class="eyebrow text-accent">{{ dateLabel }}</p>
        <span class="rounded-full border border-white/10 px-2.5 py-1 text-[9px] font-semibold text-muted">PROTOTYPE</span>
      </div>
      <h1 class="mt-2 text-[26px] leading-8 font-semibold tracking-[-0.035em]">{{ headerTitle }}</h1>
    </header>

    <section v-if="phase === 'home'" class="px-4 py-4">
      <div class="overflow-hidden rounded-[24px] border border-edge bg-panel">
        <VisualLoopPrototypePhoto :image="image" mark="paths" compact />
        <div class="p-5">
          <p class="eyebrow text-accent">What Shoots saw</p>
          <h2 class="mt-2 text-[24px] leading-7 font-semibold tracking-[-0.03em]">The aisle edges pull the eye toward the red umbrella.</h2>
          <p class="mt-3 text-[13px] leading-6 text-neutral-300">Shoots has seen this choice in 6 Shots across 3 Shoots. That tells us it repeats. It does not tell us whether you can use it on purpose.</p>

          <div class="mt-5 rounded-2xl border border-white/10 bg-white/[0.035] p-4">
            <p class="text-[10px] font-semibold tracking-[0.1em] text-muted uppercase">A test for another day</p>
            <p class="mt-2 text-[15px] leading-6 text-paper">Can you create the same visual pull somewhere else?</p>
          </div>

          <button type="button" class="btn mt-5 w-full" @click="$emit('choose', 'save')">Try another day</button>
          <button type="button" class="tap-target mt-2 w-full justify-center text-[13px] text-muted" @click="$emit('choose', 'dismiss')">Leave it</button>
        </div>
      </div>
    </section>

    <section v-else-if="phase === 'saved'" class="px-5 py-8">
      <div class="rounded-[24px] border border-accent/35 bg-accent/[0.05] p-5">
        <p class="eyebrow text-accent">Question saved</p>
        <h2 class="mt-3 text-[28px] leading-8 font-semibold tracking-[-0.04em]">Nothing has started yet.</h2>
        <p class="mt-3 text-[14px] leading-6 text-neutral-300">Shoots will only turn this into an Experiment when you choose to try it.</p>
      </div>

      <dl class="mt-5 divide-y divide-edge rounded-[20px] border border-edge bg-panel px-4">
        <div class="flex items-center justify-between py-4 text-[12px]"><dt class="text-muted">Experiment</dt><dd>None</dd></div>
        <div class="flex items-center justify-between py-4 text-[12px]"><dt class="text-muted">Criteria</dt><dd>Not fixed</dd></div>
        <div class="flex items-center justify-between py-4 text-[12px]"><dt class="text-muted">Capture Session</dt><dd>None</dd></div>
        <div class="flex items-center justify-between py-4 text-[12px]"><dt class="text-muted">Deadline</dt><dd>None</dd></div>
      </dl>

      <div class="my-7 flex items-center gap-3" aria-label="Six days pass">
        <span class="h-px flex-1 bg-edge" />
        <span class="text-[10px] font-semibold tracking-[0.1em] text-muted uppercase">6 days pass</span>
        <span class="h-px flex-1 bg-edge" />
      </div>

      <button type="button" class="btn w-full" @click="$emit('choose', 'next_shoot')">See the next Shoot</button>
      <button type="button" class="tap-target mt-2 w-full justify-center text-[13px] text-muted" @click="$emit('choose', 'dismiss')">Delete saved question</button>
    </section>

    <section v-else-if="phase === 'dismissed'" class="px-5 py-12">
      <div class="rounded-[24px] border border-edge bg-panel p-6">
        <p class="eyebrow">Finished</p>
        <h2 class="mt-3 text-[28px] leading-8 font-semibold tracking-[-0.04em]">No question saved.</h2>
        <p class="mt-3 text-[14px] leading-6 text-neutral-300">The Shot keeps its visual explanation. There is no Experiment or unfinished task waiting for you.</p>
        <button type="button" class="btn-quiet mt-6 w-full" @click="$emit('choose', 'reset')">Start over</button>
      </div>
    </section>

    <section v-else-if="phase === 'later'" class="px-5 py-6">
      <p class="eyebrow text-accent">Before opening the camera</p>
      <h2 class="mt-3 text-[29px] leading-8 font-semibold tracking-[-0.04em]">Does this question fit today?</h2>
      <p class="mt-3 text-[14px] leading-6 text-neutral-300">Try it, or shoot normally. Neither choice is a failure.</p>

      <div class="mt-6 overflow-hidden rounded-[22px] border border-edge bg-panel">
        <div class="grid grid-cols-[92px_1fr]">
          <img :src="image" alt="Market reference Shot" class="h-full min-h-32 w-full object-cover" />
          <div class="p-4">
            <p class="text-[10px] font-semibold tracking-[0.1em] text-muted uppercase">Saved question</p>
            <p class="mt-2 text-[14px] leading-5 text-paper">Can you create the same visual pull somewhere else?</p>
          </div>
        </div>
      </div>

      <button type="button" class="btn mt-6 w-full" @click="$emit('choose', 'practice')">Try it today</button>
      <button type="button" class="btn-quiet mt-3 w-full" @click="$emit('choose', 'free')">Shoot freely</button>
      <p class="mt-4 text-center text-[11px] leading-5 text-muted">Only “Try it today” creates an Experiment.</p>
    </section>

    <section v-else-if="phase === 'experiment'" class="px-5 py-6">
      <div class="rounded-[24px] border border-accent/45 bg-accent/[0.055] p-5">
        <div class="flex items-center justify-between gap-3">
          <p class="eyebrow text-accent">Reproduce Experiment</p>
          <span class="rounded-full bg-accent px-2.5 py-1 text-[9px] font-bold text-ink">READY</span>
        </div>
        <h2 class="mt-3 text-[25px] leading-7 font-semibold tracking-[-0.035em]">Make a new Scene guide the eye.</h2>
        <p class="mt-2 text-[13px] leading-5 text-neutral-300">Use any subject and any place. Judge checks the relationship below, not similarity to the market.</p>
      </div>

      <div class="mt-4 rounded-[20px] border border-edge bg-panel p-4">
        <p class="eyebrow">Criteria fixed now</p>
        <ol class="mt-3 space-y-3 text-[12px] leading-5 text-neutral-300">
          <li class="flex gap-3"><span class="text-accent">01</span><span>At least two separate visible paths.</span></li>
          <li class="flex gap-3"><span class="text-accent">02</span><span>The paths converge near today’s subject.</span></li>
          <li class="flex gap-3"><span class="text-accent">03</span><span>The Analyst panel corroborates Leading lines.</span></li>
        </ol>
      </div>

      <div class="mt-4 flex items-center justify-between rounded-[20px] border border-edge bg-panel p-4">
        <div>
          <p class="text-[13px] font-semibold">Capture Session reserved</p>
          <p class="mt-1 text-[11px] text-muted">The normal camera owns the shutter.</p>
        </div>
        <span class="h-3 w-3 rounded-full bg-accent" />
      </div>

      <button type="button" class="btn mt-5 w-full" @click="$emit('choose', 'commit')">Commit 3 new Shots</button>
    </section>

    <section v-else-if="phase === 'settling'" class="px-5 py-6">
      <p class="eyebrow text-accent">Working in the background</p>
      <h2 class="mt-3 text-[28px] leading-8 font-semibold tracking-[-0.04em]">Three exact result Shots are settling.</h2>
      <div class="mt-6 grid grid-cols-3 gap-2">
        <div v-for="(result, index) in resultImages" :key="result" class="overflow-hidden rounded-xl border border-edge bg-panel">
          <img :src="result" alt="" class="aspect-square w-full object-cover" />
          <p class="px-2 py-2 text-[9px] font-semibold text-muted">Run {{ index + 1 }} · settling</p>
        </div>
      </div>
      <p class="mt-5 text-[13px] leading-6 text-neutral-300">Shoots waits for all three Runs before recording one Experiment result.</p>
      <button type="button" class="btn mt-6 w-full" @click="$emit('choose', 'settle')">Finish processing</button>
    </section>

    <section v-else-if="phase === 'free'" class="px-5 py-6">
      <p class="eyebrow">Normal Camera Shoot</p>
      <h2 class="mt-3 text-[28px] leading-8 font-semibold tracking-[-0.04em]">No Experiment was started.</h2>
      <p class="mt-3 text-[14px] leading-6 text-neutral-300">No Criteria were fixed. No Capture Session assigned these Shots to an Experiment.</p>
      <div class="mt-6 grid grid-cols-3 gap-2">
        <img v-for="result in resultImages" :key="result" :src="result" alt="" class="aspect-square w-full rounded-xl border border-edge object-cover" />
      </div>
      <button type="button" class="btn mt-6 w-full" @click="$emit('choose', 'read_free')">See what Shoots noticed</button>
    </section>

    <section v-else-if="phase === 'result_deliberate'" class="px-4 py-4">
      <div class="overflow-hidden rounded-[24px] border border-accent/50 bg-panel">
        <VisualLoopPrototypePhoto :image="resultImages[1]" mark="result" scene="stairwell" compact />
        <div class="p-5">
          <p class="eyebrow text-accent">Experiment settled</p>
          <h2 class="mt-2 text-[26px] leading-7 font-semibold tracking-[-0.035em]">You used Leading lines on purpose in a new Scene.</h2>
          <p class="mt-3 text-[13px] leading-6 text-neutral-300">You chose the Experiment before shooting. The stairwell met the fixed Criteria.</p>
        </div>
      </div>
      <div class="mt-4 rounded-[20px] border border-edge bg-panel p-4 text-[12px] leading-5">
        <p><span class="text-muted">Shoots may say</span><br /><span class="text-paper">You reproduced Leading lines deliberately once.</span></p>
      </div>
      <button type="button" class="btn-quiet mt-5 w-full" @click="$emit('choose', 'reset')">Start over</button>
    </section>

    <section v-else class="px-4 py-4">
      <div class="overflow-hidden rounded-[24px] border border-edge bg-panel">
        <VisualLoopPrototypePhoto :image="resultImages[1]" mark="paths" scene="stairwell" compact />
        <div class="p-5">
          <p class="eyebrow">Free Shot read</p>
          <h2 class="mt-2 text-[26px] leading-7 font-semibold tracking-[-0.035em]">Leading lines appeared again.</h2>
          <p class="mt-3 text-[13px] leading-6 text-neutral-300">Shoots can see the Technique. Because you did not start an Experiment first, it cannot tell whether you meant to reproduce it.</p>
        </div>
      </div>
      <div class="mt-4 divide-y divide-edge rounded-[20px] border border-edge bg-panel px-4 text-[12px]">
        <div class="flex justify-between gap-3 py-4"><span class="text-muted">Recurrence</span><span class="text-right text-paper">Observed again</span></div>
        <div class="flex justify-between gap-3 py-4"><span class="text-muted">Intent</span><span class="text-right text-paper">Unknown</span></div>
        <div class="flex justify-between gap-3 py-4"><span class="text-muted">Verdict</span><span class="text-right text-paper">None</span></div>
        <div class="flex justify-between gap-3 py-4"><span class="text-muted">Deliberate repeatability</span><span class="text-right text-paper">Unchanged</span></div>
      </div>
      <button type="button" class="btn-quiet mt-5 w-full" @click="$emit('choose', 'reset')">Start over</button>
    </section>
  </div>
</template>
