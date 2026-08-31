import { acceptHMRUpdate, defineStore } from 'pinia'

import api from '@/api'
import { downloadImages, storyPageFilename } from '@/downloads'

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
    mobile: null, // shared read model: latest Shoot Record and Deconstruction
    shotDeconstructions: {}, // Saved visual stories, keyed by their exact source Shot.
    shotStoryBusy: {},
    shotStoryErrors: {},
    driveImport: null, // latest explicit Picker result; never Photographer memory
  }),

  getters: {
    accountReady: (state) => Boolean(state.me),
    driveConnected: (state) => Boolean(state.me?.drive_folder_id),
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
    clearError() {
      this.error = ''
    },

    async fetchAll() {
      this.loading = true
      this.error = ''
      try {
        const [me, experiment, experiments, techniques, shots, inspirations, events, runs, profile, journey, mobile] = await Promise.all([
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
          api.get('/api/mobile/snapshot'),
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
        this.mobile = mobile
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
          const [experiment, experiments, techniques, shots, inspirations, runs, profile, journey, mobile] = await Promise.all([
            api.get('/api/experiments/open'),
            api.get('/api/experiments?limit=20'),
            api.get('/api/techniques'),
            api.get('/api/shots?limit=100'),
            api.get('/api/inspirations?limit=100'),
            api.get('/api/runs?limit=20'),
            api.get('/api/profile'),
            api.get('/api/journey?limit=10'),
            api.get('/api/mobile/snapshot'),
          ])
          this.experiment = experiment
          this.experiments = experiments
          this.techniques = techniques
          this.shots = shots
          this.inspirations = inspirations
          this.runs = runs
          this.profile = profile
          this.journey = journey
          this.mobile = mobile
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

    openDrivePicker(sourceRole = 'mine') {
      return this.run('drive-import', async () => {
        this.driveImport = null
        const config = await api.get('/drive/picker-config')
        if (!config.enabled) throw new Error(config.reason)
        await loadPickerApi()
        const fileIds = await pickDriveFiles(config)
        if (!fileIds.length) return null
        const result = await api.post('/drive/import', {
          file_ids: fileIds,
          source_role: sourceRole,
        })
        this.driveImport = { ...result, source_role: sourceRole }
        await this.fetchAll()
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

    correctExperimentCriteria(previous) {
      return this.run('correct-criteria', async () => {
        if (!previous.criteria_notice) throw new Error('This Experiment does not need a Criteria correction.')
        const experiment = await api.post(`/api/experiments/${previous.id}/correct-criteria`)
        await this.fetchAll()
        this.experiment = experiment
        return experiment
      })
    },

    issueExplore(force = false) {
      return this.run('issue-explore', async () => {
        const experiment = await api.post(`/api/experiments/explore?force=${force}`)
        await this.fetchAll()
        return experiment
      })
    },

    completeExplore(id) {
      return this.run('complete-explore', async () => {
        await api.post(`/api/experiments/${id}/complete`)
        await this.fetchAll()
      })
    },

    async fetchShotDeconstruction(shotId) {
      if (this.shotStoryBusy[shotId]) return this.shotDeconstructions[shotId] || null
      this.shotStoryBusy[shotId] = 'loading'
      this.shotStoryErrors[shotId] = ''
      try {
        const draft = await api.get(`/api/deconstructions?shot_id=${encodeURIComponent(shotId)}`)
        this.shotDeconstructions[shotId] = draft
        return draft
      } catch (error) {
        this.shotStoryErrors[shotId] = error.message
        return null
      } finally {
        this.shotStoryBusy[shotId] = ''
      }
    },

    async prepareShotDeconstruction(shotId) {
      if (this.shotStoryBusy[shotId]) return null
      this.shotStoryBusy[shotId] = 'writing'
      this.shotStoryErrors[shotId] = ''
      try {
        const draft = await api.post('/api/deconstructions', {
          source_type: 'shot',
          source_id: shotId,
          source_revision: 1,
          cover_shot_id: shotId,
        })
        this.shotDeconstructions[shotId] = draft
        return draft
      } catch (error) {
        this.shotStoryErrors[shotId] = error.message
        return null
      } finally {
        this.shotStoryBusy[shotId] = ''
      }
    },

    prepareDeconstruction(sourceType, sourceId, sourceRevision, coverShotId) {
      return this.run('deconstruction', async () => {
        const draft = await api.post('/api/deconstructions', {
          source_type: sourceType,
          source_id: sourceId,
          source_revision: sourceRevision,
          cover_shot_id: coverShotId,
        })
        await this.fetchAll()
        return draft
      })
    },

    downloadDeconstructionPages(draft) {
      if (this.busy === 'download-deconstruction') return null
      return this.run('download-deconstruction', async () => {
        if (draft?.status !== 'drafted' || !draft.pages?.length) {
          throw new Error('This visual story has no images to download yet.')
        }
        // Fetch every page before starting downloads so a missing page fails visibly.
        const images = await Promise.all(draft.pages.map(async (page, index) => {
          if (!page.blob_path) throw new Error('One story image is missing. Please rebuild the story.')
          const blob = await api.getBlob(`/api/blobs/${page.blob_path}`)
          if (!blob.size || blob.type !== 'image/jpeg') {
            throw new Error('A story image could not be loaded. Please try again.')
          }
          return { blob, filename: storyPageFilename(draft.id, index) }
        }))
        return downloadImages(images)
      })
    },

    answerScoutQuestion(shootId, revision, optionId) {
      return this.run('scout-answer', async () => {
        const answer = await api.post(`/api/shoots/${shootId}/scout-answer`, {
          revision,
          option_id: optionId,
        })
        await this.fetchAll()
        return answer
      })
    },

    respondToScoutRecommendation(shootId, revision, action, optionId = '') {
      return this.run('scout-recommendation', async () => {
        const result = await api.post(`/api/shoots/${shootId}/scout-recommendation`, {
          revision,
          action,
          option_id: optionId,
        })
        await this.fetchAll()
        return result
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

    replaceExperimentDirection(direction) {
      const directions = [...(this.mobile?.experiment_directions || [])]
      const index = directions.findIndex((item) => item.id === direction.id)
      if (index >= 0) directions.splice(index, 1, direction)
      else directions.unshift(direction)
      this.mobile = { ...(this.mobile || {}), experiment_directions: directions }
    },

    chooseExperimentDirection(sourceShotId, techniqueId, save) {
      return this.run('direction-choice', async () => {
        const direction = await api.put('/api/experiment-directions', {
          source_shot_id: sourceShotId,
          technique_id: techniqueId,
          state: save ? 'saved' : 'left',
        })
        this.replaceExperimentDirection(direction)
        return direction
      })
    },

    startExperimentDirection(directionId) {
      return this.run('direction-start', async () => {
        const experiment = await api.post(`/api/experiment-directions/${directionId}/start`)
        this.experiment = experiment
        const index = this.experiments.findIndex((item) => item.id === experiment.id)
        if (index >= 0) this.experiments.splice(index, 1, experiment)
        else this.experiments.unshift(experiment)
        const direction = this.mobile?.experiment_directions?.find(
          (item) => item.id === directionId,
        )
        if (direction) {
          this.replaceExperimentDirection({
            ...direction,
            state: 'started',
            started_experiment_id: experiment.id,
          })
        }
        return experiment
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

    fetchShot(id) {
      return this.run('shot', async () => {
        const view = await api.get(`/api/shots/${id}`)
        const index = this.shots.findIndex((v) => v.shot.id === id)
        if (index >= 0) this.shots.splice(index, 1, view)
        else this.shots.unshift(view)
        return view
      })
    },

    /**
     * The photographer marks a shot worth keeping. One optional tap, and the
     * only source of taste in the system: nothing else can separate "you do
     * this often", which the profile measures on its own, from "this is what
     * you value". It is not a score and it promotes nothing.
     */
    setKeeper(id, keeper) {
      return this.run('keeper', async () => {
        const shot = await api.put(`/api/shots/${id}/keeper`, { keeper })
        const [profile, view] = await Promise.all([
          api.get('/api/profile'),
          api.get(`/api/shots/${id}`),
        ])
        const index = this.shots.findIndex((v) => v.shot.id === id)
        if (index >= 0) this.shots.splice(index, 1, view)
        else this.shots.unshift(view)
        this.profile = profile
        return shot
      })
    },

    moveShotToInspiration(id) {
      return this.run('source-role', async () => {
        const result = await api.put(`/api/shots/${id}/source-role`, { source_role: 'inspiration' })
        await this.fetchAll()
        return result
      })
    },

    restoreInspiration(id) {
      return this.run('source-role', async () => {
        const result = await api.put(`/api/inspirations/${id}/source-role`, { source_role: 'mine' })
        await this.fetchAll()
        return result
      })
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

let pickerApiPromise = null

function loadPickerApi() {
  if (window.google?.picker) return Promise.resolve()
  if (pickerApiPromise) return pickerApiPromise
  pickerApiPromise = new Promise((resolve, reject) => {
    const load = () =>
      window.gapi.load('picker', {
        callback: resolve,
        onerror: () => reject(new Error('Google Drive selection could not load')),
      })
    if (window.gapi) return load()
    const script = document.createElement('script')
    script.src = 'https://apis.google.com/js/api.js'
    script.async = true
    script.onload = load
    script.onerror = () => reject(new Error('Google Drive selection could not load'))
    document.head.appendChild(script)
  }).catch((error) => {
    pickerApiPromise = null
    throw error
  })
  return pickerApiPromise
}

function pickDriveFiles(config) {
  return new Promise((resolve, reject) => {
    const view = new window.google.picker.DocsView(window.google.picker.ViewId.DOCS)
      .setIncludeFolders(false)
      .setSelectFolderEnabled(false)
      .setMimeTypes(
        'image/jpeg,image/png,image/webp,image/gif,image/heic,image/heif,image/avif,video/mp4,video/quicktime',
      )
    const picker = new window.google.picker.PickerBuilder()
      .addView(view)
      .enableFeature(window.google.picker.Feature.MULTISELECT_ENABLED)
      .setOAuthToken(config.oauth_token)
      .setDeveloperKey(config.api_key)
      .setAppId(config.app_id)
      .setOrigin(window.location.origin)
      .setCallback((data) => {
        if (data.action === window.google.picker.Action.PICKED) {
          resolve((data.docs || []).slice(0, config.max_files).map((document) => document.id))
        } else if (data.action === window.google.picker.Action.CANCEL) {
          resolve([])
        } else if (data.action === window.google.picker.Action.ERROR || data.action === 'error') {
          reject(new Error(data.error || 'Google Drive could not open this selection'))
        }
      })
      .build()
    picker.setVisible(true)
  })
}

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useShootsStore, import.meta.hot))
}
