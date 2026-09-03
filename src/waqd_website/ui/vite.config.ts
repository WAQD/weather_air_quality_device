import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'node:path'
import fs from 'node:fs'
import path from 'node:path'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import { VitePWA } from 'vite-plugin-pwa'
import compression from 'vite-plugin-compression'
import { execSync } from 'node:child_process'
import pkg from './package.json'

let gitHash = process.env.VCS_REF || ''
if (!gitHash) {
  try {
    gitHash = execSync('git rev-parse --short=6 HEAD').toString().trim()
  } catch (e) {
    gitHash = 'unknown'
  }
}
const appVersion = `${pkg.version}+${gitHash}`

const env = loadEnv('', __dirname, '')
const waqdBaseUrl = env.VITE_WAQD_BASE_URL || 'https://waqd.de'

// Signup is opt-in via build flag and disabled by default.
const enableSignup = env.VITE_ENABLE_SIGNUP === 'true'

// Only relax TLS verification for the dev proxy. Node's bundled CA store does not
// include the newer Let's Encrypt ECDSA roots (ISRG Root X2 / Root YE chain) yet,
// which breaks the proxy to waqd.de even though the served chain is valid.
// This block only affects `vite dev`; builds never use server.proxy.
const isDev = process.env.NODE_ENV !== 'production'

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
    __WAQD_BASE_URL__: JSON.stringify(waqdBaseUrl),
    __ENABLE_SIGNUP__: JSON.stringify(enableSignup),
  },
  plugins: [
    vue({
      script: {
        defineModel: true,
        propsDestructure: true,
      },
      template: {
        compilerOptions: {
          isCustomElement: (tag) => tag.startsWith('use'),
        },
      },
    }),

    // PWA Configuration
    VitePWA({
      registerType: 'prompt',
      includeAssets: ['favicon.ico', 'pwa-192x192.png', 'pwa-512x512.png'],
      manifest: {
        name: 'WAQD - Weather & Air Quality Device',
        short_name: 'WAQD',
        description: 'Monitor your Weather and Air Quality Device in real-time',
        theme_color: '#1f2937',
        background_color: '#111827',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        scope: '/',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable'
          }
        ]
      },
      injectRegister: 'auto',
      strategies: 'generateSW',
      workbox: {
        // Only precache critical assets (JS, CSS, HTML, fonts)
        // Images will be cached on-demand via runtime caching
        globPatterns: ['**/*.{js,css,html,ico,woff2}'],
        cleanupOutdatedCaches: true,
        sourcemap: false,
        runtimeCaching: [
          // Never cache auth/session-related endpoints. Caching 401/redirects here
          // can make it look like the cookie/session "disappeared" in PWA mode.
          {
            urlPattern: /^\/api\/(public\/token|public\/logout|public\/keepalive|user\/me)\b/i,
            handler: 'NetworkOnly',
            method: 'GET',
          },
          {
            urlPattern: /^\/api\/(public\/token|public\/logout|public\/keepalive|user\/me)\b/i,
            handler: 'NetworkOnly',
            method: 'POST',
          },
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365 // 1 year
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          {
            urlPattern: /^\/api\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              cacheableResponse: {
                // Avoid caching 401/403/5xx which can incorrectly persist "logged out"
                // states while the cookie is still valid.
                statuses: [200],
              },
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 5 // 5 minutes
              },
              networkTimeoutSeconds: 10
            }
          },
          // Cache locale files with NetworkFirst for updates
          {
            urlPattern: /\/static\/locales\/.*\.json$/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'locales-cache',
              cacheableResponse: {
                statuses: [0, 200]
              },
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 // 1 day
              },
              networkTimeoutSeconds: 3
            }
          },
          // Keep map tiles in a separate bounded cache. Weather tiles are
          // short-lived because the upstream forecast changes regularly.
          {
            urlPattern: /^https:\/\/(?:openmeteo\.s3\.amazonaws\.com|tile\.openstreetmap\.org)\/.*$/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'map-tiles-cache',
              expiration: {
                maxEntries: 800,
                maxAgeSeconds: 60 * 15
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          // Cache images on-demand instead of precaching
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'images-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 30 // 30 days
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          }
        ],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api/, /^\/ws/]
      },
      devOptions: {
        enabled: false // Disable in dev mode to avoid conflicts
      }
    }),

    // Copy assets from src/waqd_assets during build (excluding Python files)
    viteStaticCopy({
      targets: [
        {
          src: '../../waqd_assets/gui_base/**/*.{avif,jpg,jpeg,png,svg}',
          dest: 'static/gui_base',
          rename: { stripBase: 2 }
        },
        {
          src: '../../waqd_assets/doc_images/**/*.{avif,jpg,jpeg,png,svg}',
          dest: 'static/doc_images',
          rename: { stripBase: 2 }
        },
        {
          src: '../../waqd_assets/general_icons/**/*.svg',
          dest: 'static/general_icons',
          rename: { stripBase: 2 }
        },
        {
          // Copy entire folder preserving nested structure (keep 'google' subfolder)
          src: '../../waqd_assets/weather_icons',
          dest: 'static/',
          rename: { stripBase: 1 }
        },
        {
          src: '../../waqd_assets/weather_bgrs/**/*.jpg',
          dest: 'static/weather_bgrs',
          rename: { stripBase: 2 }
        },
        {
          src: '../../waqd_assets/font/**/*.{woff,woff2,ttf,otf}',
          dest: 'static/font',
          rename: { stripBase: 2 }
        },
        {
          src: '../../waqd_assets/locales/*.json',
          dest: 'static/locales',
          rename: { stripBase: 2 }
        }
      ]
    }),

    // Dev-only middleware to serve /static from src/waqd_assets
    {
      name: 'waqd-static-dev',
      apply: 'serve',
      configureServer(server) {
        const staticRoot = resolve(__dirname, '../../waqd_assets')

        server.middlewares.use((req, res, next) => {
          if (!req.url?.startsWith('/static/')) {
            return next()
          }

          const urlPath = req.url.replace('/static/', '/')
          const filePath = resolve(staticRoot, '.' + urlPath)

          // Check if file exists
          if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
            return next()
          }

          // Set proper content type
          const ext = path.extname(filePath).toLowerCase()
          const contentTypes: Record<string, string> = {
            '.avif': 'image/avif',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.svg': 'image/svg+xml',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
          }

          if (contentTypes[ext]) {
            res.setHeader('Content-Type', contentTypes[ext])
          }

          // Stream the file
          const stream = fs.createReadStream(filePath)
          stream.pipe(res)
          stream.on('error', () => next())
        })
      },
    },

    // Compression plugins for gzip and brotli
    compression({
      algorithm: 'gzip',
      ext: '.gz',
    }),
    compression({
      algorithm: 'brotliCompress',
      ext: '.br',
    }),
  ],

  assetsInclude: ['**/*.svg', '**/*.avif'],

  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
      },
    },
    sourcemap: false, // Disable source maps in production for smaller bundles
    reportCompressedSize: true, // Enable build warnings and size reporting
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) => {
          // Keep static assets in their original paths
          if (assetInfo.name?.includes('static/')) {
            return assetInfo.name;
          }
          return 'assets/[name]-[hash][extname]';
        },
      },
    },
  },

  resolve: {
    alias: {
      '@static': resolve(__dirname, '../../waqd_assets'),
    },
  },

  optimizeDeps: {
    // The Open-Meteo OM file reader ships an Emscripten WASM module whose glue
    // resolves its .wasm relative to import.meta.url. If Vite pre-bundles the
    // package into .vite/deps, that relative URL breaks in dev and the weather
    // map layers never render. Excluding it keeps the glue in node_modules so
    // the sibling .wasm is found by the dev server.
    exclude: ['@openmeteo/file-format-wasm'],
  },

  server: {
    fs: {
      allow: [
        __dirname,
        resolve(__dirname, '../../waqd_assets'),
      ],
    },
    proxy: {
      // proxy API calls to the WAQD backend
      '/api': {
        target: waqdBaseUrl,
        changeOrigin: true,
        secure: !isDev,
      },
      // proxy WebSocket connections
      '/ws': {
        target: waqdBaseUrl.replace('http', 'ws'),
        ws: true,
        changeOrigin: true,
        secure: !isDev,
      },
    },
  },
})