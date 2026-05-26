import { defineStore } from "pinia";

export const useRcControl = defineStore("rcControl", {
    state: () => ({
        maxThrottle: 33,
        r1WasPressed: false,
        l1WasPressed: false,
    }),
    getters: {},
    actions: {

        decreaseMaxThrottle() {
            if (this.maxThrottle > 33) {
                this.maxThrottle = this.maxThrottle - 33
            }

        },

        increaseMaxThrottle() {
            if (this.maxThrottle < 99) {
                this.maxThrottle = this.maxThrottle + 33
            }
        },

        handleButtonL1(gp: Gamepad) {
            const pressed = gp.buttons[4]?.pressed

            // Nur beim ersten drücken
            if (pressed && !this.l1WasPressed) {
                this.decreaseMaxThrottle()
            }


                this.l1WasPressed = pressed
        },

        handleButtonR1(gp: Gamepad) {
            const pressed = gp.buttons[5]?.pressed

            // Nur beim ersten drücken
            if (pressed && !this.r1WasPressed) {
                this.increaseMaxThrottle()
            }
    
                this.r1WasPressed = pressed
        }

    },
});
