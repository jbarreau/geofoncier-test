<script setup lang="ts">
defineProps<{ error?: Error }>()
</script>

<template>
  <main class="container">
    <article>
      <p role="alert" style="color: var(--pico-color-red-500)">
        Ce module est temporairement indisponible. Veuillez réessayer.
      </p>
    </article>
  </main>
</template>
