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
        this.$router.push({ name: 'dashboard' })
      } catch (error) {
        this.error = error.message
      }
    },
  },
}
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center gap-8 px-6">
    <div class="max-w-md text-center">
      <h1 class="text-3xl font-semibold tracking-tight">Shoots</h1>
      <p class="mt-3 text-neutral-400">
        You shoot. Shoots watches your Drive folder, maps the techniques you have actually used,
        and issues one quest a day for the one you have not.
      </p>
    </div>

    <button
      v-if="config.google"
      class="rounded-lg bg-neutral-100 px-5 py-2.5 font-medium text-neutral-900 hover:bg-white"
      @click="login"
    >
      Continue with Google
    </button>

    <form
      v-if="config.dev_login"
      class="w-full max-w-sm rounded-lg border border-dashed border-amber-700/60 p-4"
      @submit.prevent="devLogin"
    >
      <p class="text-xs font-medium uppercase tracking-wide text-amber-400">Local development</p>
      <p class="mt-1 text-xs text-neutral-500">
        OAuth is not configured, so sign-in is by email only. This is disabled automatically on any
        deployment with cloud storage configured.
      </p>
      <div class="mt-3 flex gap-2">
        <input
          v-model="email"
          type="email"
          placeholder="you@company.com"
          class="flex-1 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
        <button
          type="submit"
          :disabled="!email.includes('@')"
          class="rounded bg-neutral-800 px-3 py-2 text-sm font-medium hover:bg-neutral-700 disabled:opacity-40"
        >
          Sign in
        </button>
      </div>
      <p v-if="error" class="mt-2 text-xs text-red-400">{{ error }}</p>
    </form>

    <p v-if="!config.google && !config.dev_login" class="max-w-sm text-center text-sm text-red-400">
      No sign-in method is configured. Set GOOGLE_CLIENT_ID, or ALLOW_DEV_LOGIN=true for local
      development.
    </p>
  </div>
</template>
