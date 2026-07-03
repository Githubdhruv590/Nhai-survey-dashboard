/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nhai: {
          blue: {
            DEFAULT: '#0A2540',
            dark: '#002244',
            light: '#1E3E62',
            subtle: '#F4F7FA'
          },
          orange: {
            DEFAULT: '#F26A36',
            dark: '#D94F1A',
            light: '#FA8253',
            subtle: '#FFF7F2'
          }
        }
      },
      fontFamily: {
        sans: ['Inter', 'Outfit', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
