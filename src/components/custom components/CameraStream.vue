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
    display: flex;
    justify-content: center;

    >iframe {
        width: 1200px;
        height: 675px;
        border-radius: 8px;
        box-shadow: 0px 0px 16px 0px rgba(0, 0, 0, 0.648);
    }
}
</style>