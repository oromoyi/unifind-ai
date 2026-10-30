/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        navy: { 50: '#eef3fb', 100: '#d9e4f5', 200: '#b3c9ea', 300: '#7fa3d9', 400: '#4a79c2', 500: '#2a58a3', 600: '#1d4283', 700: '#16336a', 800: '#0f2550', 900: '#0b1c3d', 950: '#071229' },
        teal: { 50: '#effcfa', 100: '#d3f7f2', 200: '#a8ede4', 300: '#6fddd1', 400: '#38c4b8', 500: '#17a89f', 600: '#0f8883', 700: '#106d6a', 800: '#115755', 900: '#124846' },
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'] },
      keyframes: { fadeUp: { '0%': { opacity: 0, transform: 'translateY(8px)' }, '100%': { opacity: 1, transform: 'none' } } },
      animation: { 'fade-up': 'fadeUp .35s ease-out both' },
    },
  },
  plugins: [],
}
