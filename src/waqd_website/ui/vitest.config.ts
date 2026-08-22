import { defineConfig } from 'vitest/config'

// Minimal, standalone Vitest config. Deliberately separate from vite.config.ts,
// which loads heavy plugins (PWA, compression, static-copy) and runs git/exec
// at import time — none of which unit tests need.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/unit/**/*.test.ts'],
  },
})
