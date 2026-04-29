/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Syne','Nunito', 'ui-sans-serif', 'system-ui'],
      },
    },
  },
  plugins: [],
}