import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.waqd.app',
  appName: 'Waqd App',
  webDir: 'dist',
  server: {
    url: 'https://waqd.de',
    cleartext: true
  }
};

export default config;
