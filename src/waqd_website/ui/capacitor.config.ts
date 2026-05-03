import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.waqd.app',
  appName: 'Waqd App',
  webDir: 'dist',
  server: {
    url: 'https://waqd.de', // http://192.168.178.57:8000
    cleartext: true
  }
};

export default config;
