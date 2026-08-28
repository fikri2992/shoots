<script>
import { mapActions, mapState } from 'pinia'

import { useShootsStore } from '@/stores/shoots'

export default {
  name: 'DriveImportPanel',
  computed: {
    ...mapState(useShootsStore, ['busy', 'driveImport']),
    resultText() {
      if (!this.driveImport) return ''
      const role = this.driveImport.source_role === 'inspiration' ? 'Inspiration' : 'Shots'
      const parts = [`${this.driveImport.imported} ${role} added`]
      if (this.driveImport.duplicates) parts.push(`${this.driveImport.duplicates} already here`)
      if (this.driveImport.failures?.length) parts.push(`${this.driveImport.failures.length} could not be read`)
      return parts.join(' · ')
    },
  },
  methods: {
    ...mapActions(useShootsStore, ['openDrivePicker']),
  },
}
</script>

<template>
  <section class="mt-6 rounded-2xl border border-edge bg-panel p-4 sm:p-5">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p class="eyebrow text-accent">Google Drive</p>
        <h2 class="mt-1 t-title">Choose existing files</h2>
        <p class="mt-2 max-w-xl t-body text-neutral-400">
          Shoots receives only the files you select. Choose whether they belong to your record before importing.
        </p>
      </div>
      <div class="grid shrink-0 gap-2 sm:min-w-56">
        <button
          type="button"
          class="btn"
          :disabled="Boolean(busy)"
          @click="openDrivePicker('mine')"
        >
          {{ busy === 'drive-import' ? 'Opening Drive…' : 'Add my Shots' }}
        </button>
        <button
          type="button"
          class="btn-quiet"
          :disabled="Boolean(busy)"
          @click="openDrivePicker('inspiration')"
        >
          Add as Inspiration
        </button>
      </div>
    </div>
    <p v-if="resultText" class="mt-4 rounded-xl bg-panel-2 px-3 py-2 t-meta text-neutral-300">
      {{ resultText }}
    </p>
  </section>
</template>
