<script setup lang="ts">
defineProps<{ path: string }>()
</script>

<template>
  <div class="source-ref">
    <span class="source-ref__label">source</span>
    <code>{{ path }}</code>
  </div>
</template>
