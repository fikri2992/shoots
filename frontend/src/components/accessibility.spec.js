import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import DisclosureRow from '@/components/DisclosureRow.vue'

describe('progressive disclosure', () => {
  it('exposes its expanded state and controlled panel', async () => {
    const wrapper = mount(DisclosureRow, {
      props: { label: 'Evidence behind this update' },
      slots: { default: '<p>Exact Evidence</p>' },
    })
    const button = wrapper.get('button')
    const panelId = button.attributes('aria-controls')

    expect(button.attributes('aria-expanded')).toBe('false')
    expect(document.getElementById(panelId)).toBe(null)

    await button.trigger('click')
    expect(button.attributes('aria-expanded')).toBe('true')
    expect(wrapper.get(`#${panelId}`).text()).toContain('Exact Evidence')
  })
})
