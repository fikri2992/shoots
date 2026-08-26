import { acceptHMRUpdate, defineStore } from 'pinia'

import api from '@/api'

const POLL_MS = 5000

/**
 * Everything the dashboard shows, in one store. The backend is the truth;
 * this polls it while the tab is visible so the feed ticks during a run.
 * Options syntax (AGENTS.md).
 */
export const useShootsStore = defineStore('shoots', {
  state: () => ({
    me: null, // User record (drive_folder_id tells us if Connect happened)
    experiment: null, // open experiment or null
    experiments: [],
    techniques: [],
    shots: [], // [{ shot, analysis }]
    inspirations: [], // explicit references; never Photographer work
    events: [],
    runs: [], // durable per-Shot stage accounts; events only explain them
    loading: false,
    busy: '', // which action is in flight: connect | sync | issue | skip | shoot | preflight
    error: '',
    timer: null,
    lastEventAt: '',
    push: 'unknown', // unknown | unsupported | off | on | denied
    profile: null, // the Tendency Profile: what the photographer keeps doing
    journey: [], // Journey Updates, newest first
    pairCode: null, // { code, expires_in_seconds } while pairing a camera
    seeding: null, // { done, total, name } while the first Shots upload
  }),

  getters: {
    connected: (state) => Boolean(state.me),
    analysedShots: (state) => state.shots.filter((v) => v.analysis),
    observed: (state) => state.techniques.filter((technique) => technique.status !== 'unobserved'),
    techniquesByFamily: (state) => {
      const groups = {}
      for (const node of state.techniques) (groups[node.family] ||= []).push(node)
      return groups
    },
    shotById: (state) => (id) => state.shots.find((v) => v.shot.id === id) || null,
    experimentById: (state) => (id) => state.experiments.find((q) => q.id === id) || null,

    /** Newest first by when we received it, not by when the camera says it was
        taken: an older holiday Shot dropped in today belongs at the top. */
    orderedShots: (state) =>
      [...state.shots].sort((a, b) => (b.shot.ingested_at || '').localeCompare(a.shot.ingested_at || '')),

    /**
     * Still moving through the pipeline — the Now screen narrates these. Bounded
     * in time: a Shot the Analyst never got to must not pin the home screen on
     * "reading it now" for the rest of the week.
     */
    working: (state) =>
      state.shots.filter(
        (v) =>
          !v.analysis &&
          v.shot.status !== 'failed' &&
          v.shot.status !== 'analyzed' &&
          Date.now() - new Date(v.shot.ingested_at) < 15 * 60 * 1000,
      ),

    pastExperiments: (state) => state.experiments.filter((q) => q.status !== 'open'),

    /** The newest verdict anywhere, with the experiment it belongs to. */
    lastVerdict: (state) => {
      let best = null
      for (const experiment of state.experiments) {
        for (const verdict of experiment.verdicts || []) {
          if (!best || (verdict.judged_at || '') > (best.verdict.judged_at || '')) best = { experiment, verdict }
        }
      }
      return best
    },
  },

  actions: {
    async fetchAll() {
      this.loading = true
      this.error = ''
      try {
        const [me, experiment, experiments, techniques, shots, inspirations, events, runs, profile, journey] = await Promise.all([
          api.get('/api/me'),
          api.get('/api/experiments/open'),
          api.get('/api/experiments?limit=20'),
          api.get('/api/techniques'),
          api.get('/api/shots?limit=100'),
          api.get('/api/inspirations?limit=100'),
          api.get('/api/events?limit=100'),
          api.get('/api/runs?limit=20'),
          api.get('/api/profile'),
          api.get('/api/journey?limit=10'),
        ])
        this.me = me
        this.experiment = experiment
        this.experiments = experiments
        this.techniques = techniques
        this.shots = shots
        this.inspirations = inspirations
        this.events = events
        this.runs = runs
        this.profile = profile
        this.journey = journey
        this.lastEventAt = events[0]?.at || ''
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    /** Cheap tick: only events and the open experiment; refetch the rest when something moved. */
    async poll() {
      try {
        const events = await api.get('/api/events?limit=100')
        const newest = events[0]?.at || ''
        if (newest !== this.lastEventAt) {
          this.events = events
          this.lastEventAt = newest
          const [experiment, experiments, techniques, shots, inspirations, runs, profile, journey] = await Promise.all([
            api.get('/api/experiments/open'),
            api.get('/api/experiments?limit=20'),
            api.get('/api/techniques'),
            api.get('/api/shots?limit=100'),
            api.get('/api/inspirations?limit=100'),
            api.get('/api/runs?limit=20'),
            api.get('/api/profile'),
            api.get('/api/journey?limit=10'),
          ])
          this.experiment = experiment
          this.experiments = experiments
          this.techniques = techniques
          this.shots = shots
          this.inspirations = inspirations
          this.runs = runs
          this.profile = profile
          this.journey = journey
        }
      } catch {
        // a failed poll is not an error the user needs to see
      }
    },

    startPolling() {
      this.stopPolling()
      this.timer = setInterval(() => {
        if (document.visibilityState === 'visible') this.poll()
      }, POLL_MS)
    },

    stopPolling() {
      if (this.timer) clearInterval(this.timer)
      this.timer = null
    },

    async run(name, fn) {
      this.busy = name
      this.error = ''
      try {
        return await fn()
      } catch (error) {
        this.error = error.message
        return null
      } finally {
        this.busy = ''
      }
    },

    connect() {
      return this.run('connect', async () => {
        const result = await api.post('/drive/connect')
        await this.fetchAll()
        return result
      })
    },

    sync() {
      return this.run('sync', async () => {
        const result = await api.post('/drive/sync')
        await this.poll()
        return result
      })
    },

    issueExperiment(force = false) {
      return this.run('issue', async () => {
        const experiment = await api.post(`/api/experiments/issue?force=${force}`)
        await this.fetchAll()
        return experiment
      })
    },

    skipExperiment(id) {
      return this.run('skip', async () => {
        await api.post(`/api/experiments/${id}/skip`)
        await this.fetchAll()
      })
    },

    leaveExperiment(id) {
      return this.run('leave', async () => {
        await api.post(`/api/experiments/${id}/leave`)
        await this.fetchAll()
      })
    },

    /** On location: the experiment's criteria on a preview, before the upload. */
    preflight(file, experimentId) {
      return this.run('preflight', async () => {
        const form = new FormData()
        form.append('file', file, file.name)
        form.append('experiment_id', experimentId)
        return api.postForm('/drive/preflight', form)
      })
    },

    shoot(file, experimentId = '') {
      return this.run('shoot', async () => {
        const form = new FormData()
        form.append('file', file, file.name)
        form.append('source_id', webSourceId(file))
        form.append('source_role', 'mine')
        if (experimentId) form.append('experiment_id', experimentId)
        const result = await api.postForm('/api/ingress/shots', form)
        await this.poll()
        return result
      })
    },

    /**
     * First run: a handful of Shots in one go, so the agent has something to
     * read before it is asked for an opinion. Sequential on purpose — each one
     * enters the same idempotent direct-ingress path as the Phone Source.
     */
    async seed(files, sourceRole = 'mine') {
      this.error = ''
      this.seeding = { done: 0, total: files.length, name: files[0]?.name || '' }
      try {
        for (const file of files) {
          this.seeding.name = file.name
          const form = new FormData()
          form.append('file', file, file.name)
          form.append('source_id', webSourceId(file))
          form.append('source_role', sourceRole)
          await api.postForm('/api/ingress/shots', form)
          this.seeding.done += 1
        }
        await this.fetchAll()
      } catch (error) {
        this.error = error.message
      } finally {
        this.seeding = null
      }
    },

    /** Where push stands on this device, without prompting. */
    async checkPush() {
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        this.push = 'unsupported'
        return
      }
      if (Notification.permission === 'denied') {
        this.push = 'denied'
        return
      }
      const registration = await navigator.serviceWorker.getRegistration()
      const existing = await registration?.pushManager.getSubscription()
      this.push = existing ? 'on' : 'off'
    },

    /** Must run from a tap: the browser shows the permission prompt. */
    enablePush() {
      return this.run('push', async () => {
        const { key, enabled } = await api.get('/api/push/key')
        if (!enabled) throw new Error('Push is not configured on the server')
        const registration = await navigator.serviceWorker.ready
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(key),
        })
        await api.post('/api/push/subscribe', subscription.toJSON())
        this.push = 'on'
        await api.post('/api/push/test')
      })
    },

    async fetchShot(id) {
      const view = await api.get(`/api/shots/${id}`)
      const index = this.shots.findIndex((v) => v.shot.id === id)
      if (index >= 0) this.shots.splice(index, 1, view)
      else this.shots.unshift(view)
      return view
    },

    /**
     * The photographer marks a shot worth keeping. One optional tap, and the
     * only source of taste in the system: nothing else can separate "you do
     * this often", which the profile measures on its own, from "this is what
     * you value". It is not a score and it promotes nothing.
     */
    async setKeeper(id, keeper) {
      const shot = await api.put(`/api/shots/${id}/keeper`, { keeper })
      const index = this.shots.findIndex((v) => v.shot.id === id)
      if (index >= 0) this.shots.splice(index, 1, { ...this.shots[index], shot })
      this.profile = await api.get('/api/profile')
      return shot
    },

    async moveShotToInspiration(id) {
      await api.put(`/api/shots/${id}/source-role`, { source_role: 'inspiration' })
      await this.fetchAll()
    },

    async restoreInspiration(id) {
      await api.put(`/api/inspirations/${id}/source-role`, { source_role: 'mine' })
      await this.fetchAll()
    },

    /** A code to type into the native camera, so it can be handed this account. */
    async pairCamera() {
      return this.run('pair', async () => {
        this.pairCode = await api.post('/api/pair', {})
        return this.pairCode
      })
    },
  },
})

function urlBase64ToUint8Array(base64) {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const raw = atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(raw, (c) => c.charCodeAt(0))
}

function webSourceId(file) {
  return `web:${file.name}:${file.size}:${file.lastModified}`
}

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useShootsStore, import.meta.hot))
}
