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
    quest: null, // open quest or null
    quests: [],
    skills: [],
    shots: [], // [{ shot, analysis }]
    events: [],
    loading: false,
    busy: '', // which action is in flight: connect | sync | issue | skip | shoot | preflight
    error: '',
    timer: null,
    lastEventAt: '',
    push: 'unknown', // unknown | unsupported | off | on | denied
    seeding: null, // { done, total, name } while the first frames upload
  }),

  getters: {
    connected: (state) => Boolean(state.me?.drive_folder_id),
    analysedShots: (state) => state.shots.filter((v) => v.analysis),
    attempted: (state) => state.skills.filter((s) => s.status !== 'unexplored'),
    skillsByFamily: (state) => {
      const groups = {}
      for (const node of state.skills) (groups[node.family] ||= []).push(node)
      return groups
    },
    shotById: (state) => (id) => state.shots.find((v) => v.shot.id === id) || null,
    questById: (state) => (id) => state.quests.find((q) => q.id === id) || null,

    /** Newest first by when we received it, not by when the camera says it was
        taken: an old holiday photo dropped in today belongs at the top. */
    frames: (state) =>
      [...state.shots].sort((a, b) => (b.shot.ingested_at || '').localeCompare(a.shot.ingested_at || '')),

    /** Still moving through the pipeline — the Now screen narrates these. */
    working: (state) =>
      state.shots.filter((v) => !v.analysis && v.shot.status !== 'failed' && v.shot.status !== 'analyzed'),

    pastQuests: (state) => state.quests.filter((q) => q.status !== 'open'),

    /** The newest verdict anywhere, with the quest it belongs to. */
    lastVerdict: (state) => {
      let best = null
      for (const quest of state.quests) {
        for (const verdict of quest.verdicts || []) {
          if (!best || (verdict.judged_at || '') > (best.verdict.judged_at || '')) best = { quest, verdict }
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
        const [me, quest, quests, skills, shots, events] = await Promise.all([
          api.get('/api/me'),
          api.get('/api/quests/open'),
          api.get('/api/quests?limit=20'),
          api.get('/api/skills'),
          api.get('/api/shots?limit=100'),
          api.get('/api/events?limit=60'),
        ])
        this.me = me
        this.quest = quest
        this.quests = quests
        this.skills = skills
        this.shots = shots
        this.events = events
        this.lastEventAt = events[0]?.at || ''
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    /** Cheap tick: only events and the open quest; refetch the rest when something moved. */
    async poll() {
      try {
        const events = await api.get('/api/events?limit=60')
        const newest = events[0]?.at || ''
        if (newest !== this.lastEventAt) {
          this.events = events
          this.lastEventAt = newest
          const [quest, quests, skills, shots] = await Promise.all([
            api.get('/api/quests/open'),
            api.get('/api/quests?limit=20'),
            api.get('/api/skills'),
            api.get('/api/shots?limit=100'),
          ])
          this.quest = quest
          this.quests = quests
          this.skills = skills
          this.shots = shots
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

    issueQuest(force = false) {
      return this.run('issue', async () => {
        const quest = await api.post(`/api/quests/issue?force=${force}`)
        await this.fetchAll()
        return quest
      })
    },

    skipQuest(id) {
      return this.run('skip', async () => {
        await api.post(`/api/quests/${id}/skip`)
        await this.fetchAll()
      })
    },

    /** On location: the quest's criteria on a preview, before the upload. */
    preflight(file, questId) {
      return this.run('preflight', async () => {
        const form = new FormData()
        form.append('file', file, file.name)
        form.append('quest_id', questId)
        return api.postForm('/drive/preflight', form)
      })
    },

    shoot(file, questId = '') {
      return this.run('shoot', async () => {
        const form = new FormData()
        form.append('file', file, file.name)
        if (questId) form.append('quest_id', questId)
        const result = await api.postForm('/drive/shoot', form)
        await this.poll()
        return result
      })
    },

    /**
     * First run: a handful of frames in one go, so the agent has something to
     * read before it is asked for an opinion. Sequential on purpose — each one
     * goes through Drive, and the pipeline narrates them as they land.
     */
    async seed(files) {
      this.error = ''
      this.seeding = { done: 0, total: files.length, name: files[0]?.name || '' }
      try {
        for (const file of files) {
          this.seeding.name = file.name
          const form = new FormData()
          form.append('file', file, file.name)
          await api.postForm('/drive/shoot', form)
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
  },
})

function urlBase64ToUint8Array(base64) {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const raw = atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(raw, (c) => c.charCodeAt(0))
}

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useShootsStore, import.meta.hot))
}
