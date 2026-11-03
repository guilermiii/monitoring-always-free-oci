/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        oci: {
          red: '#F80000',
          dark: '#16191F',
          card: '#1F242E',
          border: '#2C3440',
        }
      }
    },
  },
  plugins: [],
}
