import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'node:path'
import fs from 'node:fs'
import { viteStaticCopy } from 'vite-plugin-static-copy'

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

    // Copy assets from src/waqd/assets during build
    viteStaticCopy({
      targets: [
        {
          src: '../../waqd/assets/font/Franzo-E4GA.woff',
          dest: '.'
        },
        {
          src: '../../waqd/assets/gui_base/icon.avif',
          dest: '.'
        },
        {
          src: '../../waqd/assets/gui_base/*.jpg',
          dest: 'gui_base'
        }
      ]
    }),

    // Dev-only middleware to serve /static from src/waqd/assets
    {
      name: 'waqd-static-dev',
      apply: 'serve',
      configureServer(server) {
        const staticRoot = resolve(__dirname, '../../waqd/assets')

        server.middlewares.use('/static', (req, res, next) => {
          // strip the /static prefix
          const urlPath = req.url || '/'
          const filePath = resolve(staticRoot, '.' + urlPath)

          fs.readFile(filePath, (err, data) => {
            if (err) {
              return next()
            }
            // Very simple content-type guessing: you can improve if needed
            if (filePath.endsWith('.avif')) {
              res.setHeader('Content-Type', 'image/avif')
            } else if (filePath.endsWith('.jpg') || filePath.endsWith('.jpeg')) {
              res.setHeader('Content-Type', 'image/jpeg')
            } else if (filePath.endsWith('.png')) {
              res.setHeader('Content-Type', 'image/png')
            } else if (filePath.endsWith('.woff')) {
              res.setHeader('Content-Type', 'font/woff')
            } else if (filePath.endsWith('.woff2')) {
              res.setHeader('Content-Type', 'font/woff2')
            }

            res.end(data)
          })
        })
      },
    },
  ],

  resolve: {
    alias: {
      '@static': resolve(__dirname, '../../waqd/assets'),
    },
  },

  server: {
    fs: {
      allow: [
        __dirname,
        resolve(__dirname, '../../waqd/assets'),
      ],
    },
    proxy: {
      // proxy API calls to your Python backend
      '/public': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
    },
  },
})