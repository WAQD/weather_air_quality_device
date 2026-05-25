const { light, dark } = require('./daisyui-theme.js')

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  plugins: [
    require("daisyui"),
  ],
  daisyui: {
    themes: [
      { light },
      { dark },
    ],
  },
}
