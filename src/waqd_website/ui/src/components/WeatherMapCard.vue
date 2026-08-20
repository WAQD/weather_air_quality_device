<template>
    <div v-if="currentLocation" class="card bg-base-100 shadow-xl overflow-hidden w-full">
        <div class="card-body p-0">
            <iframe width="100%" height="400" frameborder="0" scrolling="no" marginheight="0"
                marginwidth="0" :src="osmEmbedUrl" style="border: 0;">
            </iframe>
            <div class="text-xs p-2 text-center opacity-70">
                <a :href="osmLinkUrl" target="_blank" class="hover:underline">
                    View Larger Map on OpenStreetMap
                </a>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWebsiteWeather } from '../composables/useWebsiteWeather'

const { currentLocation } = useWebsiteWeather()

const osmEmbedUrl = computed(() => {
    if (!currentLocation.value) {
        return ''
    }

    const lat = currentLocation.value.latitude
    const lon = currentLocation.value.longitude
    const offset = 0.05
    return `https://www.openstreetmap.org/export/embed.html?bbox=${lon - offset},${lat - offset},${lon + offset},${lat + offset}&layer=mapnik&marker=${lat},${lon}`
})

const osmLinkUrl = computed(() => {
    if (!currentLocation.value) {
        return ''
    }

    const lat = currentLocation.value.latitude
    const lon = currentLocation.value.longitude
    return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=12/${lat}/${lon}`
})
</script>
