/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        tg: {
          bg: '#17212b',
          secondary: '#1e2c3a',
          card: '#242f3d',
          border: '#344150',
          accent: '#2b9fdb',
          text: '#e4ecf2',
          muted: '#7e919f',
          danger: '#e53935',
          success: '#4caf50',
          warn: '#ff9800',
        },
      },
    },
  },
  plugins: [],
}
