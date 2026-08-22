<script>
import ActivityFeed from '@/components/ActivityFeed.vue'

export default {
  name: 'FeedPage',
  components: { ActivityFeed },
}
</script>

<template>
  <div class="mx-auto max-w-3xl p-4 pb-24 md:pb-8">
    <ActivityFeed :limit="200" />
  </div>
</template>
