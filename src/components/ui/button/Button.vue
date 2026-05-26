<script setup lang="ts">
import type { PrimitiveProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import type { ButtonVariants } from "."
import { Primitive } from "reka-ui"
import { cn } from "@/lib/utils"
import { buttonVariants } from "."

interface Props extends PrimitiveProps {
  variant?: ButtonVariants["variant"]
  size?: ButtonVariants["size"]
  class?: HTMLAttributes["class"]
}

const props = withDefaults(defineProps<Props>(), {
  as: "button",
})
</script>

<template>
  <Primitive class="button" data-slot="button" :data-variant="variant" :data-size="size" :as="as" :as-child="asChild"
    :class="cn(buttonVariants({ variant, size }), props.class)">
    <slot />
  </Primitive>
</template>

<style>
@layer base {

  button:not(:disabled),
  [role="button"]:not(:disabled) {
    cursor: pointer;

  }

  /* button:disabled {
    opacity: 100% !important;
    background-color: rgb(174, 174, 174) !important;
    color: black !important;
    
  } */
}

.button {
  background-color: var(--primary);
  color: var(--text-foreground);
  border: none;
  border-radius: var(--radius);
  color: white;
  border: 2px solid transparent;
  transition: all 125ms ease-in-out ;
  &:hover {
    color: var(--text-foreground);
    background-color: var(--secondary);
    border-color: var(--primary);
  }
}

.button:hover {
  background-color: var(--primary-hover);
}
</style>
