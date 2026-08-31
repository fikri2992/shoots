import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it } from 'vitest'

import JourneyPage from '@/pages/JourneyPage.vue'
import { useShootsStore } from '@/stores/shoots'

let wrapper

afterEach(() => wrapper?.unmount())

describe('Journey image download integration', () => {
  it.each(['standard', 'A', 'B', 'C'])('offers separate JPEGs without a ZIP link in Journey %s', async (variant) => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/journey', name: 'journey', component: JourneyPage },
        { path: '/shots', name: 'shots', component: () => import('@/pages/ShotsPage.vue') },
        {
          path: '/shoots/:shootId/records/:revision',
          name: 'shoot-record',
          component: () => import('@/pages/ShootRecordPage.vue'),
        },
      ],
    })
    await router.push({ path: '/journey', query: variant === 'standard' ? {} : { variant } })
    await router.isReady()

    const store = useShootsStore()
    store.me = { id: 'download-check', drive_folder_id: '' }
    store.profile = { shots: 2, keepers: 1, scenes: 1, dimensions: [], blind_spots: [] }
    store.shots = [{ shot: { id: 'opening-shot', kept_at: '2026-08-31T00:00:00Z', blobs: {} } }]
    store.mobile = {
      latest_shoot_record: {
        shoot_id: 'shoot-check',
        revision: 1,
        shot_ids: ['opening-shot'],
        receipt: { keeper_shot_ids: ['opening-shot'] },
      },
      latest_deconstruction: {
        id: 'story-check',
        source_type: 'shoot',
        source_id: 'shoot-check',
        source_revision: 1,
        status: 'drafted',
        cover_shot_id: 'opening-shot',
        suggested_caption: 'Caption remains available separately.',
        writing: { model: 'integration-checkpoint-fixture' },
        pages: [
          { title: 'The opening', blob_path: 'users/download-check/story/page-1.jpg' },
          { kind: 'clean', title: '', blob_path: 'users/download-check/story/page-2.jpg' },
        ],
      },
    }

    wrapper = mount(JourneyPage, { global: { plugins: [pinia, router] } })
    const story = variant === 'standard' ? wrapper.get('#journey-deconstruction') : wrapper
    const images = story.findAll('a[data-story-page-download]')

    expect(images).toHaveLength(2)
    images.forEach((link, index) => {
      expect(link.attributes('href')).toBe(`/api/blobs/users/download-check/story/page-${index + 1}.jpg`)
      expect(link.attributes('download')).toBe(`Shoots-story-check-0${index + 1}.jpg`)
    })
    const downloadButton = story.findAll('button').find((button) => /^Download (all )?images$/.test(button.text()))
    expect(downloadButton).toBeDefined()
    expect(story.find('a[href*="/api/deconstructions/"]').exists()).toBe(false)
    expect(story.text()).toContain('Caption remains available separately.')
    expect(story.text()).toContain('allow multiple downloads')
    expect(story.text()).toContain('Review the words and images before sharing')
    const clean = story.get('img[alt="Clean Shot, full image without text"]')
    expect(clean.classes()).toContain('object-contain')
    expect(clean.classes()).not.toContain('object-cover')
    expect(story.text()).toContain('Clean Shot · no text or crop')

    store.busy = 'download-deconstruction'
    await wrapper.vm.$nextTick()
    expect(downloadButton.attributes('disabled')).toBeDefined()
  })
})
