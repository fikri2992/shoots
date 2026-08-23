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
  <div class="col gutter flex h-full flex-col justify-center">
    <p class="t-meta text-accent">Shoots</p>
    <h1 class="mt-2 t-hero">A photography coach that watches, decides, and tells you when to go out.</h1>
    <p class="mt-4 t-body text-neutral-300">
      It reads the photos you already take, maps what you can do, and sets you one thing to try — timed to the
      light where you shot last.
    </p>

    <button v-if="config.google" class="btn mt-10 w-full" @click="login">Continue with Google</button>

    <form v-if="config.dev_login" class="mt-8 rounded-2xl bg-panel p-4" @submit.prevent="devLogin">
      <p class="t-meta text-accent">Local development</p>
      <p class="mt-1 t-meta">OAuth is not configured here, so sign-in is by email only.</p>
      <div class="mt-3 flex gap-2">
        <input
          v-model="email"
          type="email"
          placeholder="you@company.com"
          class="min-w-0 flex-1 rounded-xl border border-edge bg-panel-2 px-3 py-2.5 text-[15px] outline-none focus:border-edge-strong"
        />
        <button type="submit" :disabled="!email.includes('@')" class="btn-quiet px-4 py-2.5">Sign in</button>
      </div>
      <p v-if="error" class="mt-2 t-meta text-bad">{{ error }}</p>
    </form>

    <p v-if="!config.google && !config.dev_login" class="mt-8 t-body text-bad">
      No sign-in method is configured. Set GOOGLE_CLIENT_ID, or ALLOW_DEV_LOGIN=true for local development.
    </p>
  </div>
</template>
