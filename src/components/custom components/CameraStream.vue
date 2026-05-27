<script setup lang="ts">
const streamUrl = import.meta.env.VITE_CAMERA_STREAM
</script>
<template>
    <div class="frame-container">
        <iframe :src="streamUrl" />
    </div>
</template>

<style scoped>
.frame-container {
    overflow: hidden;

    >iframe {
        height: 680px;
        width: 920px;

    }
}
</style>