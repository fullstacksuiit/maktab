/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './management/templates/**/*.html',
    './templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#0d6b4e',
        secondary: '#1a9e6f',
        gold: '#c9a84c',
        dark: '#1e1e1e',
        light: '#f8f9fa',
      },
      fontFamily: {
        sans: ['Poppins', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
