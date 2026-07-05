import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.waqd.app',
  appName: 'Waqd App',
  webDir: 'dist',
  server: {
    url: 'https://waqd.de', //'https://waqd.de', // for debug: 'http://192.168.0.151:8000',
    cleartext: true
  }
};

export default config;
