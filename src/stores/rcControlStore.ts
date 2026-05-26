import { defineStore } from "pinia";

export const useRcControl = defineStore("rcControl", {
    state: () => ({
        throttleIndex: 0,
        throttleGears: [
            33, 66, 99
        ] as const,
        r1WasPressed: false,
        l1WasPressed: false,
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
        }



    },
});
