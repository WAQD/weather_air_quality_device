import { copyFile, mkdir, readdir, rename, stat } from 'fs/promises'
import { join, extname, relative } from 'path'
import sharp from 'sharp'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const distDir = join(__dirname, '../dist/static')
const cacheDir = join(__dirname, '../node_modules/.cache/waqd-image-optimization')
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
  const cachedFilePath = join(cacheDir, relative(distDir, filePath))

  // Images in the website are immutable. Once an image has been optimized,
  // restore that result instead of invoking Sharp again.
  if (await fileExists(cachedFilePath)) {
    await copyFile(cachedFilePath, filePath)
    console.log(`Skipping (cached): ${filePath}`)
    return
  }

  const image = sharp(filePath)
  const metadata = await image.metadata()

  console.log(`Optimizing: ${filePath}`)

  try {
    await mkdir(join(cachedFilePath, '..'), { recursive: true })

    if (ext === '.jpg' || ext === '.jpeg') {
      await image
        .jpeg({ quality: 80, mozjpeg: true })
        .toFile(cachedFilePath + '.tmp')
    } else if (ext === '.png') {
      await image
        .png({ quality: 80, compressionLevel: 9 })
        .toFile(cachedFilePath + '.tmp')
    } else if (ext === '.avif') {
      await image
        .avif({ quality: 70 })
        .toFile(cachedFilePath + '.tmp')
    } else if (ext === '.webp') {
      await image
        .webp({ quality: 80 })
        .toFile(cachedFilePath + '.tmp')
    } else {
      return
    }

    await rename(cachedFilePath + '.tmp', cachedFilePath)
    await copyFile(cachedFilePath, filePath)

    const newStats = await stat(cachedFilePath)
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

async function fileExists(filePath) {
  try {
    await stat(filePath)
    return true
  } catch (error) {
    if (error.code === 'ENOENT') {
      return false
    }
    throw error
  }
}

async function main() {
  console.log('🖼️  Optimizing images in dist/static...\n')

  try {
    await mkdir(cacheDir, { recursive: true })
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
