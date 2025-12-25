import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'node:path'
import fs from 'node:fs'
import path from 'node:path'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
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
      registerType: 'autoUpdate',
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
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        cleanupOutdatedCaches: true,
        sourcemap: false,
        runtimeCaching: [
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
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 5 // 5 minutes
              },
              networkTimeoutSeconds: 10
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
          dest: 'static/gui_base'
        },
        {
          src: '../../waqd_assets/doc_images/**/*.{avif,jpg,jpeg,png,svg}',
          dest: 'static/doc_images'
        },
        {
          src: '../../waqd_assets/general_icons/**/*.svg',
          dest: 'static/general_icons'
        },
        {
          src: '../../waqd_assets/weather_icons/**/*.svg',
          dest: 'static/weather_icons'
        },
        {
          src: '../../waqd_assets/font/**/*.{woff,woff2,ttf,otf}',
          dest: 'static/font'
        },
        {
          src: '../../waqd_assets/base/ui_dict.json',
          dest: 'static/base'
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
  ],

  assetsInclude: ['**/*.svg', '**/*.avif'],

  build: {
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

  server: {
    fs: {
      allow: [
        __dirname,
        resolve(__dirname, '../../waqd_assets'),
      ],
    },
    proxy: {
      // proxy API calls to your Python backend
      '/api': 'http://localhost:8000',
      // proxy WebSocket connections
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})