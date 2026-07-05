import { defineStore } from "pinia";
import { ref } from "vue";

export const useRcControl = defineStore("rcControl", {
    state: () => ({
        throttleIndex: 0,
        throttleGears: [
            33, 66, 99
        ] as const,
        r1WasPressed: false,
        l1WasPressed: false,
        steeringOffset: ref(0),
        OFFSET_STEP: 0.01,
        OFFSET_MAX: 0.7,
    }),
    getters: {
        maxThrottle: (state): number => {
            return state.throttleGears[state.throttleIndex] ?? state.throttleGears[0]
        }
    },
    actions: {

        decreaseMaxThrottle() {
            if (this.throttleIndex > 0) {
                this.throttleIndex = this.throttleIndex - 1
            }

        },

        increaseMaxThrottle() {
            if (this.throttleIndex < this.throttleGears.length - 1) {
                this.throttleIndex = this.throttleIndex + 1
            }
        },

        handleButtonL1(gp: Gamepad) {
            const pressed = gp.buttons[13]?.pressed

            if (pressed && !this.l1WasPressed) {
                this.decreaseMaxThrottle()
            }

            this.l1WasPressed = pressed!
        },

        handleButtonR1(gp: Gamepad) {
            const pressed = gp.buttons[12]?.pressed

            if (pressed && !this.r1WasPressed) {
                this.increaseMaxThrottle()
            }

            this.r1WasPressed = pressed!
        },

        handleButtonLeft(gp: Gamepad) {
            const pressed = gp.buttons[14]?.pressed

            if (pressed) {
                this.decreaseSteeringOffset()
            }
        },

        handleButtonRight(gp: Gamepad) {
            const pressed = gp.buttons[15]?.pressed

            if (pressed) {
                this.increaseSteeringOffset()
            }
        },


        decreaseSteeringOffset() {

            this.steeringOffset = Math.max(-this.OFFSET_MAX,
                Math.round((this.steeringOffset - this.OFFSET_STEP) * 100) / 100)
        },

        increaseSteeringOffset() {
            this.steeringOffset = Math.min(this.OFFSET_MAX,
                Math.round((this.steeringOffset + this.OFFSET_STEP) * 100) / 100)
        },


        resetSteeringOffset() {
            this.steeringOffset = 0
        },

applySteeringOffset(steering: number): number {
    return Math.max(-1, Math.min(1, (-steering) + (-this.steeringOffset)))
}



    },
});
