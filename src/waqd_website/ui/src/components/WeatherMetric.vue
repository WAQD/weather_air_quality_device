<template>
  <div class="rounded-box bg-base-300 p-3">
    <div class="flex items-center gap-3">
      <svg class="h-6 w-6 flex-none" :class="iconClass" aria-hidden="true"
        :style="rotate !== undefined ? { transform: `rotate(${rotate}deg)`, transformOrigin: 'center' } : undefined">
        <use :href="iconUrl" fill="currentColor" />
      </svg>
      <div class="min-w-0">
        <p class="text-xs uppercase tracking-[0.16em] opacity-60 break-words whitespace-normal">
          {{ label }}</p>
        <p class="mt-1 text-lg font-semibold">{{ value }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  iconUrl: string
  iconClass: string
  label: string
  value: string
  rotate?: number
}>()
</script>
