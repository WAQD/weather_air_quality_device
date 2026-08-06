import type { CapacitorConfig } from '@capacitor/cli';
import fs from 'node:fs';
import path from 'node:path';

function loadEnvVar(name: string, fallback: string): string {
  if (process.env[name]) {
    return process.env[name];
  }
  const envPath = path.join(process.cwd(), '.env');
  try {
    const raw = fs.readFileSync(envPath, 'utf8');
    for (const line of raw.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eq = trimmed.indexOf('=');
      if (eq === -1) continue;
      const key = trimmed.slice(0, eq).trim();
      if (key === name) {
        return trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '');
      }
    }
  } catch {
    // .env not present, fall back to default
  }
  return fallback;
}

const baseUrl = loadEnvVar('VITE_WAQD_BASE_URL', 'https://waqd.de');

const config: CapacitorConfig = {
  appId: 'com.waqd.app',
  appName: 'Waqd App',
  webDir: 'dist',
  server: {
    url: baseUrl,
    cleartext: true
  },
};

export default config;
