<script setup lang="ts">
const camStream = import.meta.env.VITE_CAMERA_STREAM
const audioStream = import.meta.env.VITE_AUDIO_STREAM
const webrtcStream = import.meta.env.VITE_WEB_RTC_STREAM
</script>
<template>
    <div class="frame-container">
        <iframe :src="webrtcStream" />
        <!-- <iframe class="audio-stream" :src="audioStream"/> -->
    </div>
</template>

<style scoped>
.frame-container {
    display: flex;
    justify-content: center;

    /* 854, 480 */
    >iframe {
        width: 1200px;
        height: 676px;
        border-radius: 8px;
        box-shadow: 0px 0px 16px 0px rgba(0, 0, 0, 0.648);
    }
}

.audio-stream {
    width: 0px !important;
    height: 0px !important;
}
</style>