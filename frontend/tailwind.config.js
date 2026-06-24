/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: '#0f1724',
          pink: '#ff6fa3',
          orange: '#ff8a3d',
          yellow: '#ffd166',
          blue: '#4fc3f7',
          red: '#ff4655',
          bg: '#f7f9fc',
        },
        gradientFrom: '#6EE7F5',
        gradientTo: '#FF9AC6',
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

