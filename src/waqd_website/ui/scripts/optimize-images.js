import { readdir, stat } from 'fs/promises'
import { join, extname } from 'path'
import sharp from 'sharp'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const distDir = join(__dirname, '../dist/static')
const imageExtensions = ['.jpg', '.jpeg', '.png', '.avif', '.webp']

async function getFiles(dir) {
  const files = []
  const items = await readdir(dir)

  for (const item of items) {
    const fullPath = join(dir, item)
    const stats = await stat(fullPath)

    if (stats.isDirectory()) {
      files.push(...await getFiles(fullPath))
    } else if (imageExtensions.includes(extname(item).toLowerCase())) {
      files.push(fullPath)
    }
  }

  return files
}

async function optimizeImage(filePath) {
  const ext = extname(filePath).toLowerCase()
  const image = sharp(filePath)
  const metadata = await image.metadata()

  console.log(`Optimizing: ${filePath}`)

  try {
    if (ext === '.jpg' || ext === '.jpeg') {
      await image
        .jpeg({ quality: 80, mozjpeg: true })
        .toFile(filePath + '.tmp')
    } else if (ext === '.png') {
      await image
        .png({ quality: 80, compressionLevel: 9 })
        .toFile(filePath + '.tmp')
    } else if (ext === '.avif') {
      await image
        .avif({ quality: 70 })
        .toFile(filePath + '.tmp')
    } else if (ext === '.webp') {
      await image
        .webp({ quality: 80 })
        .toFile(filePath + '.tmp')
    } else {
      return
    }

    // Replace original with optimized
    const fs = await import('fs/promises')
    await fs.rename(filePath + '.tmp', filePath)

    const newStats = await stat(filePath)
    const oldSize = metadata.size
    const newSize = newStats.size
    if (oldSize && newSize) {
      const ratio = 1 - newSize / oldSize
      if (Number.isFinite(ratio) && ratio > 0) {
        console.log(`  ✓ Reduced by ${(ratio * 100).toFixed(1)}%`)
      } else {
        console.log('  ✓ Optimized')
      }
    } else {
      console.log('  ✓ Optimized')
    }

  } catch (error) {
    console.error(`  ✗ Failed to optimize: ${error.message}`)
  }
}

async function main() {
  console.log('🖼️  Optimizing images in dist/static...\n')

  try {
    const files = await getFiles(distDir)
    console.log(`Found ${files.length} images to optimize\n`)

    for (const file of files) {
      await optimizeImage(file)
    }

    console.log('\n✅ Image optimization complete!')
  } catch (error) {
    console.error('❌ Error during optimization:', error)
    process.exit(1)
  }
}

main()
