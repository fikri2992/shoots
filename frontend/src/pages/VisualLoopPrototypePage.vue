<script>
// Three variants of the Shot-to-Experiment loop, switchable via ?variant=, on the dev-only /prototype/visual-loop route.
import marketImage from '../../../docs/test-corpus/generated-intent/13-intent-color-market.png'
import hallwayImage from '../../../docs/test-corpus/generated-intent/14-transfer-hallway-not-yet.png'
import stairwellImage from '../../../docs/test-corpus/generated-intent/15-transfer-stairwell-met.png'
import tableImage from '../../../docs/test-corpus/generated-intent/16-transfer-table-not-yet.png'

import VisualLoopPrototypeSwitcher from '@/pages/VisualLoopPrototypeSwitcher.vue'
import VisualLoopPrototypeVariantA from '@/pages/VisualLoopPrototypeVariantA.vue'
import VisualLoopPrototypeVariantB from '@/pages/VisualLoopPrototypeVariantB.vue'
import VisualLoopPrototypeVariantC from '@/pages/VisualLoopPrototypeVariantC.vue'
import VisualLoopPrototypeVariantD from '@/pages/VisualLoopPrototypeVariantD.vue'

const VARIANTS = [
  {
    key: 'A',
    name: 'Guided lesson',
    idea: 'One image and one decision at a time. The Photographer cannot miss the next action.',
    risk: 'The complete agent lifecycle stays hidden until the Photographer advances.',
  },
  {
    key: 'B',
    name: 'Agent receipt',
    idea: 'The entire read, plan, act, check, and adapt chain stays visible as one managed job.',
    risk: 'It proves Taskmaster work clearly, but carries more information on one screen.',
  },
  {
    key: 'C',
    name: 'Technique notebook',
    idea: 'Learn, Test, and Proof have separate homes while keeping one Technique as the thread.',
    risk: 'The tab model is easy to navigate but makes the loop feel less automatic.',
  },
  {
    key: 'D',
    name: 'Across days',
    idea: 'Separate at-home learning from a later Shoot, then show the different claims for free shooting and deliberate practice.',
    risk: 'It is the most honest flow, but it asks the Photographer to make one explicit choice before deliberate practice can be measured.',
  },
]

const STEPS = [
  {
    label: 'What holds the frame',
    title: 'The aisle leads to the red umbrella',
    body: 'Both walkway edges narrow toward the person. The two cyan paths show the exact structure Shoots named.',
    detail: 'Leading lines appears in 6 Shots across 3 Shoots, including 2 Keepers.',
    mark: 'paths',
  },
  {
    label: 'What interrupts it',
    title: 'The left foreground swallows one path',
    body: 'The large tarp fills the lower-left frame, so the left path starts later and carries more visual weight.',
    detail: 'Model observation. The marked region shows what the sentence refers to.',
    mark: 'notice',
  },
  {
    label: 'Try one change',
    title: 'Carry the two-path idea forward',
    body: 'In any later Scene, look for two edges, rails, shadows, or walls that guide attention toward one subject. Do not copy the market.',
    detail: 'The dashed paths show the relationship to remember, not a fictional camera arrow.',
    mark: 'try',
  },
  {
    label: 'Check the next Shot',
    title: 'Check the relationship, not the objects',
    body: 'A later Shot should contain two visible paths that converge near its own subject. The place, subject, light, and time may all change.',
    detail: 'The market remains the reference, not a template to recreate.',
    mark: 'check',
  },
  {
    label: 'Saved for your next Shoot',
    title: 'Can you use this idea elsewhere?',
    body: 'Scout created one Reproduce Experiment from this Keeper-backed Technique. It can wait until tomorrow or next week.',
    detail: 'The Criteria were fixed now, before any later result exists.',
    mark: 'check',
  },
  {
    label: 'Capture Session reserved',
    title: 'Another day, you decide to try it',
    body: 'You start the saved Experiment, then open the normal camera. Only the exact new Shots you commit belong to it.',
    detail: 'The normal camera owns the shutter. Free Shots stay free.',
    mark: 'clean',
  },
  {
    label: 'Working in the background',
    title: 'Three later Scenes are settling',
    body: 'Ingest, Analyst, Cartographer, Judge, and Scribe continue without asking you to upload or repeat the request.',
    detail: 'The Experiment waits until every member Run reaches a completed or terminal state.',
    mark: 'clean',
  },
  {
    label: 'Experiment settled',
    title: 'The stairwell carried the idea',
    body: 'The hallway, stairwell, and table Shots were checked. The stairwell is the earliest result where two new paths converged near a new subject.',
    detail: 'This is Technique transfer across Scenes, not a similarity score.',
    mark: 'result',
  },
  {
    label: 'The next route changed',
    title: 'Shoots recorded that the idea transferred',
    body: 'Leading lines now has one evaluable Reproduce session across a different Scene, with Criteria met. Scout can move to warm against cool.',
    detail: 'The later result changed future work. That is the visible memory effect.',
    mark: 'result',
  },
]

const ACTIONS = [
  'Next',
  'Next',
  'Next',
  'Save for next Shoot',
  'Start when ready',
  'Commit 3 later Shots',
  'Settle the Runs',
  'See what changed',
  'Start over',
]

export default {
  name: 'VisualLoopPrototypePage',
  components: {
    VisualLoopPrototypeSwitcher,
    VisualLoopPrototypeVariantA,
    VisualLoopPrototypeVariantB,
    VisualLoopPrototypeVariantC,
    VisualLoopPrototypeVariantD,
  },
  data() {
    return {
      variants: VARIANTS,
      image: marketImage,
      resultImages: [hallwayImage, stairwellImage, tableImage],
      step: 0,
      delayedPhase: 'home',
    }
  },
  computed: {
    currentKey() {
      const requested = String(this.$route.query.variant || 'B').toUpperCase()
      return this.variants.some((variant) => variant.key === requested) ? requested : 'B'
    },
    currentVariant() {
      return this.variants.find((variant) => variant.key === this.currentKey)
    },
    content() {
      return STEPS[this.step]
    },
    actionLabel() {
      return ACTIONS[this.step]
    },
    prototypeState() {
      if (this.currentKey === 'D') {
        const saved = !['home', 'dismissed'].includes(this.delayedPhase)
        const deliberate = ['experiment', 'settling', 'result_deliberate'].includes(this.delayedPhase)
        const free = ['free', 'result_free'].includes(this.delayedPhase)
        return {
          time: this.delayedPhase === 'home' || this.delayedPhase === 'saved' || this.delayedPhase === 'dismissed'
            ? 'tonight_at_home'
            : 'six_days_later',
          experiment_direction: saved
            ? { technique_id: 'leading_lines', status: 'saved', deadline: null }
            : null,
          experiment: deliberate
            ? {
                type: 'reproduce',
                status: this.delayedPhase === 'result_deliberate' ? 'completed' : 'open',
                criteria_frozen_before_results: true,
              }
            : null,
          capture_session: deliberate
            ? { status: this.delayedPhase === 'experiment' ? 'reserved' : this.delayedPhase === 'settling' ? 'processing' : 'settled' }
            : null,
          free_shots: free ? ['later_01', 'later_02', 'later_03'] : [],
          allowed_claim: this.delayedPhase === 'result_deliberate'
            ? 'deliberate_cross_scene_reproduction'
            : this.delayedPhase === 'result_free'
              ? 'technique_recurred_intent_unknown'
              : null,
        }
      }
      return {
        story: {
          technique_id: 'leading_lines',
          current_step: this.step < 4 ? ['keep', 'notice', 'try', 'check'][this.step] : 'complete',
          primary_steps: 4,
          other_reads: ['warm_against_cool', 'layering'],
        },
        experiment: this.step < 4
          ? null
          : {
              type: 'reproduce',
              status: this.step >= 7 ? 'completed' : 'open',
              criteria_frozen_before_results: true,
              source_technique: 'leading_lines',
              same_scene_required: false,
            },
        capture_session: this.step < 5
          ? null
          : {
              status: this.step === 5 ? 'reserved' : this.step === 6 ? 'processing' : 'settled',
              ordered_members: this.step >= 6 ? ['result_01', 'result_02', 'result_03'] : [],
            },
        result: this.step < 7
          ? null
          : {
              representative_shot_id: 'result_02',
              outcomes: ['not_yet', 'criteria_met', 'not_yet'],
              distinct_scene_from_reference: true,
            },
        memory: this.step < 8
          ? 'unchanged'
          : {
              technique_id: 'leading_lines',
              evaluable_reproduce_sessions: 1,
              criteria_met_sessions: 1,
              distinct_scene_transfer: true,
              next_scout_route: 'explore:warm_against_cool',
            },
      }
    },
    stateText() {
      return JSON.stringify(this.prototypeState, null, 2)
    },
  },
  methods: {
    selectVariant(key) {
      this.$router.replace({ query: { ...this.$route.query, variant: key } })
      this.resetScroll()
    },
    advance() {
      this.step = this.step >= STEPS.length - 1 ? 0 : this.step + 1
      this.resetScroll()
    },
    back() {
      this.step = Math.max(0, this.step - 1)
      this.resetScroll()
    },
    jump(step) {
      this.step = Math.max(0, Math.min(STEPS.length - 1, Number(step)))
      this.resetScroll()
    },
    chooseDelayed(action) {
      const transitions = {
        save: 'saved',
        dismiss: 'dismissed',
        next_shoot: 'later',
        practice: 'experiment',
        free: 'free',
        commit: 'settling',
        settle: 'result_deliberate',
        read_free: 'result_free',
        reset: 'home',
      }
      this.delayedPhase = transitions[action] || this.delayedPhase
      this.resetScroll()
    },
    reset() {
      this.step = 0
      this.delayedPhase = 'home'
      this.resetScroll()
    },
    resetScroll() {
      this.$nextTick(() => {
        if (this.$refs.prototypeShell) this.$refs.prototypeShell.scrollTop = 0
      })
    },
  },
}
</script>

<template>
  <div ref="prototypeShell" class="fixed inset-0 z-[60] overflow-y-auto bg-[#060607] text-paper">
    <div class="mx-auto grid min-h-screen max-w-[1120px] items-start justify-center lg:grid-cols-[250px_390px_270px] lg:gap-7 lg:px-5 lg:py-7">
      <aside class="sticky top-7 hidden pt-6 lg:block">
        <p class="eyebrow text-accent">Throwaway prototype</p>
        <h1 class="mt-4 text-[24px] leading-7 font-semibold tracking-[-0.03em]">How should the agent loop appear?</h1>
        <p class="mt-4 text-[13px] leading-6 text-muted">The same simulated job appears in three layouts. Every visible claim points to its source in the image.</p>

        <div class="mt-8 border-l-2 border-accent pl-4">
          <p class="text-[12px] font-semibold">{{ currentKey }} · {{ currentVariant.name }}</p>
          <p class="mt-2 text-[13px] leading-5 text-neutral-300">{{ currentVariant.idea }}</p>
          <p class="mt-3 text-[12px] leading-5 text-muted">Risk: {{ currentVariant.risk }}</p>
        </div>

        <p class="mt-8 text-[11px] leading-5 text-neutral-600">Use the bottom arrows to compare layouts. Use the screen button to advance the same job. Nothing reaches the API.</p>
      </aside>

      <main class="mx-auto min-h-screen w-full max-w-[390px] overflow-hidden bg-ink shadow-[0_30px_100px_rgba(0,0,0,0.65)] lg:min-h-[844px] lg:rounded-[32px] lg:border lg:border-white/10">
        <VisualLoopPrototypeVariantA v-if="currentKey === 'A'" :image="image" :result-images="resultImages" :step="step" :content="content" :action-label="actionLabel" @advance="advance" @back="back" />
        <VisualLoopPrototypeVariantB v-else-if="currentKey === 'B'" :image="image" :result-images="resultImages" :step="step" :content="content" :action-label="actionLabel" @advance="advance" @back="back" />
        <VisualLoopPrototypeVariantC v-else-if="currentKey === 'C'" :image="image" :result-images="resultImages" :step="step" :content="content" :action-label="actionLabel" @advance="advance" @back="back" @jump="jump" />
        <VisualLoopPrototypeVariantD v-else :image="image" :result-images="resultImages" :phase="delayedPhase" @choose="chooseDelayed" />
      </main>

      <aside class="sticky top-7 hidden pt-6 lg:block">
        <div class="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
          <div class="flex items-center justify-between gap-3">
            <p class="eyebrow">Visible state</p>
            <button type="button" class="text-[11px] text-muted hover:text-paper" @click="reset">Reset</button>
          </div>
          <pre class="mt-4 whitespace-pre-wrap text-[10px] leading-[1.65] text-neutral-400">{{ stateText }}</pre>
        </div>
      </aside>

      <section class="mx-auto mb-28 mt-5 w-full max-w-[390px] px-5 lg:hidden">
        <details class="rounded-2xl border border-edge bg-panel p-4">
          <summary class="cursor-pointer text-[12px] font-medium">Why this variant?</summary>
          <p class="mt-4 text-[13px] leading-5 text-neutral-300">{{ currentVariant.idea }}</p>
          <p class="mt-2 text-[12px] leading-5 text-muted">Risk: {{ currentVariant.risk }}</p>
          <pre class="mt-4 whitespace-pre-wrap border-t border-edge pt-4 text-[10px] leading-5 text-neutral-400">{{ stateText }}</pre>
          <button type="button" class="mt-3 text-[12px] text-accent" @click="reset">Reset state</button>
        </details>
      </section>
    </div>

    <VisualLoopPrototypeSwitcher :variants="variants" :current="currentKey" @select="selectVariant" />
  </div>
</template>
