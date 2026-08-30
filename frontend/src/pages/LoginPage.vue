<script>
import { mapActions } from 'pinia'

import api from '@/api'
import { useAuthStore } from '@/stores/auth'

export default {
  name: 'LoginPage',
  data() {
    return { config: { google: false, dev_login: false }, email: '', error: '' }
  },
  async created() {
    try {
      this.config = await api.get('/auth/config')
    } catch {
      this.config = { google: true, dev_login: false }
    }
  },
  methods: {
    ...mapActions(useAuthStore, ['login', 'fetchMe']),
    async devLogin() {
      this.error = ''
      try {
        await api.post('/auth/dev-login', { email: this.email.trim() })
        await this.fetchMe()
        this.$router.push({ name: 'now' })
      } catch (error) {
        this.error = error.message
      }
    },
  },
}
</script>

<template>
  <div class="page-shell flex min-h-screen items-center py-10 sm:py-16">
    <div class="grid w-full gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:gap-20">
      <section>
        <p class="eyebrow text-accent">Shoots</p>
        <h1 class="mt-4 max-w-xl t-hero sm:text-[54px]">Learn to see like yourself.</h1>
        <p class="mt-5 max-w-lg text-[17px] leading-7 text-neutral-300">
          Shoots learns from every Shot, offers one personal Experiment, and tracks what changes.
        </p>

        <div class="mt-9 grid gap-3 sm:grid-cols-3 lg:max-w-2xl">
          <div class="surface-soft p-4">
            <p class="eyebrow">Notice</p>
            <p class="mt-2 text-sm leading-5 text-neutral-300">Patterns across your own Shots</p>
          </div>
          <div class="surface-soft p-4">
            <p class="eyebrow">Try</p>
            <p class="mt-2 text-sm leading-5 text-neutral-300">One bounded Experiment</p>
          </div>
          <div class="surface-soft p-4">
            <p class="eyebrow">Remember</p>
            <p class="mt-2 text-sm leading-5 text-neutral-300">Only Change the Evidence supports</p>
          </div>
        </div>
      </section>

      <section class="surface p-5 sm:p-7">
        <p class="eyebrow">Continue your Journey</p>
        <h2 class="mt-3 text-2xl font-semibold tracking-[-0.03em] text-paper">Your archive becomes the memory.</h2>
        <p class="mt-3 t-body">
          Sign in to reconnect the Shots, Experiments, Keeper signals, and Evidence already tied to you.
        </p>

        <button v-if="config.google" class="btn mt-7 w-full" @click="login">
          Continue with Google
        </button>

        <form v-if="config.dev_login" class="mt-6 border-t border-edge pt-6" @submit.prevent="devLogin">
          <p class="eyebrow text-accent">Local development</p>
          <p class="mt-2 t-meta">OAuth is unavailable here. This email creates a local session only.</p>
          <input
            v-model="email"
            type="email"
            placeholder="you@example.com"
            class="mt-4 w-full rounded-xl border border-edge bg-panel-2 px-4 py-3 text-[15px] text-paper outline-none transition placeholder:text-muted focus:border-accent"
          />
          <button type="submit" :disabled="!email.includes('@')" class="btn mt-3 w-full">Enter Shoots</button>
          <p v-if="error" class="mt-3 t-meta text-bad">{{ error }}</p>
        </form>

        <p v-if="!config.google && !config.dev_login" class="mt-7 rounded-xl border border-bad/40 bg-bad/10 p-4 t-body text-bad">
          No sign-in method is configured. Set GOOGLE_CLIENT_ID, or ALLOW_DEV_LOGIN=true for local development.
        </p>

        <p class="mt-6 border-t border-edge pt-5 t-meta">
          Shoots does not grade your eye. It separates measured Evidence, model opinion, and the Shots you choose to keep.
        </p>
      </section>
    </div>
  </div>
</template>
