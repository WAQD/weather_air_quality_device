/**
 * Separate Vite build for the @capacitor/background-runner task file.
 *
 * Output: public/background-runner.js (IIFE, no external deps)
 * This file is copied into the app's web assets by Capacitor and executed
 * in a V8 isolate when a background task fires.
 *
 * Run with: vite build --config vite.runner.config.ts
 */

import { defineConfig } from 'vite'
import { resolve } from 'node:path'

export default defineConfig({
  // Disable public dir handling — this build only produces one output file.
  publicDir: false,
  build: {
    // Output alongside the PWA assets so Capacitor picks it up.
    outDir: 'public',
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, 'src/background/runner.ts'),
      name: 'WaqdBackgroundRunner',
      // IIFE format: addEventListener is called at module evaluation time,
      // which is exactly what the background runner runtime expects.
      formats: ['iife'],
      fileName: () => 'background-runner.js',
    },
    minify: false, // Keep readable for debugging; set to true for production
    rollupOptions: {
      // The runner must be fully self-contained — no external imports.
      external: [],
    },
  },
})
