const { purple, teal, peach, orange, forest, red } = require('./daisyui-theme.js')

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
      "light",
      "dark",
      { purple },
      { teal },
      { peach },
      { orange },
      { forest },
      { red },
    ],
  },
}