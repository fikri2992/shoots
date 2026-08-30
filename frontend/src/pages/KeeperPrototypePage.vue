<script>
// Three Keeper hierarchy variants, switchable via ?variant=, on the dev-only /prototype/keeper route.
import doorwayImage from '../../../docs/test-corpus/generated-intent/11-intent-doorway-hard-light.png'
import cyclistImage from '../../../docs/test-corpus/generated-intent/12-intent-panning-cyclist.png'
import marketImage from '../../../docs/test-corpus/generated-intent/13-intent-color-market.png'

import KeeperPrototypeSwitcher from '@/pages/KeeperPrototypeSwitcher.vue'
import KeeperPrototypeVariantA from '@/pages/KeeperPrototypeVariantA.vue'
import KeeperPrototypeVariantB from '@/pages/KeeperPrototypeVariantB.vue'
import KeeperPrototypeVariantC from '@/pages/KeeperPrototypeVariantC.vue'
import KeeperPrototypeVariantD from '@/pages/KeeperPrototypeVariantD.vue'

const VARIANTS = [
  {
    key: 'A',
    name: 'Quiet bookmark',
    idea: 'Keep the action beside the Shot, but reduce it to a quiet utility control.',
    risk: 'Still asks for a decision before the Photographer reaches the evidence.',
  },
  {
    key: 'B',
    name: 'After the read',
    idea: 'Finish the visual lesson first. Ask for the optional signal only after the main action.',
    risk: 'Fewer people will notice it, which may be correct or may starve Reproduce of signals.',
  },
  {
    key: 'C',
    name: 'Shoot-level choice',
    idea: 'Prove the autonomous Shoot job first, then let the Photographer mark any valued Shots together.',
    risk: 'Adds a distinct review moment and moves Keeper away from the individual Shot detail.',
  },
  {
    key: 'D',
    name: 'Record then Shot',
    idea: 'Finish on the Shoot Record, then open a Shot into a quiet detail view where Keeper lives.',
    risk: 'Keeper takes one extra tap to reach, but it no longer competes with the autonomous result.',
  },
]

export default {
  name: 'KeeperPrototypePage',
  components: {
    KeeperPrototypeSwitcher,
    KeeperPrototypeVariantA,
    KeeperPrototypeVariantB,
    KeeperPrototypeVariantC,
    KeeperPrototypeVariantD,
  },
  data() {
    return {
      variants: VARIANTS,
      keeperIds: [],
      hybridShotId: null,
      shots: [
        { id: 'shot_market', label: 'Market aisle', image: marketImage, alt: 'Rainy market with a red umbrella' },
        { id: 'shot_cyclist', label: 'Cyclist at dusk', image: cyclistImage, alt: 'Cyclist moving across a wet street' },
        { id: 'shot_doorway', label: 'Doorway light', image: doorwayImage, alt: 'Person standing in a dark doorway' },
      ],
    }
  },
  computed: {
    currentKey() {
      const requested = String(this.$route.query.variant || 'D').toUpperCase()
      return this.variants.some((item) => item.key === requested) ? requested : 'D'
    },
    currentVariant() {
      return this.variants.find((item) => item.key === this.currentKey)
    },
    marketMarked() {
      return this.keeperIds.includes('shot_market')
    },
    hybridShot() {
      return this.shots.find((shot) => shot.id === this.hybridShotId) || null
    },
    prototypeState() {
      return {
        autonomous_job: 'settled',
        terminal_runs: '4/4',
        scout_outcome: 'explain',
        keeper_shot_ids: this.keeperIds,
        hybrid_view: this.hybridShot ? `shot:${this.hybridShot.id}` : 'shoot_record',
        later_reproduce: this.keeperIds.length
          ? 'candidate after Evidence gate'
          : 'unavailable without a Keeper',
        deconstruction: this.keeperIds.length
          ? 'needs Photographer cover choice'
          : 'needs a Keeper cover',
      }
    },
    stateText() {
      return JSON.stringify(this.prototypeState, null, 2)
    },
  },
  methods: {
    selectVariant(key) {
      this.hybridShotId = null
      this.$router.replace({ query: { ...this.$route.query, variant: key } })
      this.resetPrototypeScroll()
    },
    openHybridShot(id) {
      this.hybridShotId = id
      this.resetPrototypeScroll()
    },
    closeHybridShot() {
      this.hybridShotId = null
      this.resetPrototypeScroll()
    },
    resetPrototypeScroll() {
      this.$nextTick(() => {
        if (this.$refs.prototypeShell) this.$refs.prototypeShell.scrollTop = 0
      })
    },
    toggleKeeper(id = 'shot_market') {
      this.keeperIds = this.keeperIds.includes(id)
        ? this.keeperIds.filter((keeperId) => keeperId !== id)
        : [...this.keeperIds, id]
    },
    resetState() {
      this.keeperIds = []
    },
  },
}
</script>

<template>
  <div ref="prototypeShell" class="fixed inset-0 z-[60] overflow-y-auto bg-[#060607] text-paper">
    <div class="mx-auto grid min-h-screen max-w-[1100px] items-start justify-center lg:grid-cols-[250px_390px_250px] lg:gap-7 lg:px-5 lg:py-7">
      <aside class="sticky top-7 hidden pt-6 lg:block">
        <p class="eyebrow text-accent">Throwaway prototype</p>
        <h1 class="mt-4 text-[24px] leading-7 font-semibold tracking-[-0.03em] text-paper">Where should Keeper live?</h1>
        <p class="mt-4 text-[14px] leading-6 text-muted">
          The autonomous Shoot must feel finished without this signal. Keeper still needs a quiet home for taste and later Reproduce.
        </p>

        <div class="mt-8 border-l-2 border-accent pl-4">
          <p class="text-[12px] font-semibold text-paper">{{ currentKey }} · {{ currentVariant.name }}</p>
          <p class="mt-2 text-[13px] leading-5 text-neutral-300">{{ currentVariant.idea }}</p>
          <p class="mt-3 text-[12px] leading-5 text-muted">Risk: {{ currentVariant.risk }}</p>
        </div>

        <p class="mt-8 text-[11px] leading-5 text-neutral-600">Use the bottom arrows or keyboard arrow keys. Fixture images only. Nothing reaches the API.</p>
      </aside>

      <main class="mx-auto min-h-screen w-full max-w-[390px] overflow-hidden bg-ink shadow-[0_30px_100px_rgba(0,0,0,0.65)] lg:min-h-[844px] lg:rounded-[32px] lg:border lg:border-white/10">
        <KeeperPrototypeVariantA
          v-if="currentKey === 'A'"
          :image="shots[0].image"
          :marked="marketMarked"
          @toggle-keeper="toggleKeeper()"
        />
        <KeeperPrototypeVariantB
          v-else-if="currentKey === 'B'"
          :image="shots[0].image"
          :marked="marketMarked"
          @toggle-keeper="toggleKeeper()"
        />
        <KeeperPrototypeVariantC
          v-else-if="currentKey === 'C'"
          :shots="shots"
          :keeper-ids="keeperIds"
          @toggle-keeper="toggleKeeper"
        />
        <KeeperPrototypeVariantD
          v-else
          :shots="shots"
          :selected-shot="hybridShot"
          :keeper-ids="keeperIds"
          @open-shot="openHybridShot"
          @close-shot="closeHybridShot"
          @toggle-keeper="toggleKeeper"
        />
      </main>

      <aside class="sticky top-7 hidden pt-6 lg:block">
        <div class="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
          <div class="flex items-center justify-between gap-3">
            <p class="eyebrow">Prototype state</p>
            <button type="button" class="text-[11px] text-muted hover:text-paper" @click="resetState">Reset</button>
          </div>
          <pre class="mt-4 whitespace-pre-wrap text-[11px] leading-5 text-neutral-400">{{ stateText }}</pre>
        </div>
        <p class="mt-4 text-[11px] leading-5 text-neutral-600">The autonomous job never changes when a Keeper is added. Only later product possibilities change.</p>
      </aside>

      <section class="mx-auto mb-28 mt-5 w-full max-w-[390px] px-5 lg:hidden">
        <details class="rounded-2xl border border-edge bg-panel p-4">
          <summary class="cursor-pointer text-[12px] font-medium text-paper">Prototype state and tradeoff</summary>
          <p class="mt-4 text-[13px] leading-5 text-neutral-300">{{ currentVariant.idea }}</p>
          <p class="mt-2 text-[12px] leading-5 text-muted">Risk: {{ currentVariant.risk }}</p>
          <pre class="mt-4 whitespace-pre-wrap border-t border-edge pt-4 text-[11px] leading-5 text-neutral-400">{{ stateText }}</pre>
          <button type="button" class="mt-3 text-[12px] text-accent" @click="resetState">Reset state</button>
        </details>
      </section>
    </div>

    <KeeperPrototypeSwitcher :variants="variants" :current="currentKey" @select="selectVariant" />
  </div>
</template>
