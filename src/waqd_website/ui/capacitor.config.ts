import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.waqd.app',
  appName: 'Waqd App',
  webDir: 'dist',
  server: {
    url: 'https://waqd.de', 
    //url: 'http://192.168.0.151:8000',
    //url: 'http://192.168.178.57:8000',
    cleartext: true
  },
  plugins: {
    BackgroundRunner: {
      // Path to the bundled runner JS (relative to webDir / dist root).
      // Built by: npm run build:runner → public/background-runner.js
      label: 'com.waqd.app.background',
      src: 'background-runner.js',
      event: 'gpsWeatherRefresh',
      // Not periodically scheduled — dispatched on demand by WeatherWidgetProvider
      repeat: false,
      interval: 0,
      autoStart: false,
    },
  },
};

export default config;
