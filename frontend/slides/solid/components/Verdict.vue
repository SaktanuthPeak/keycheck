<script setup lang="ts">
const props = defineProps<{ kind: 'follows' | 'gap' | 'proposal' }>()

const labels = {
  follows: '✓ follows',
  gap: '✗ gap',
  proposal: '◇ proposal',
}
</script>

<template>
  <span class="verdict" :class="`verdict--${props.kind}`">{{ labels[props.kind] }}</span>
</template>
