/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Syne', 'system-ui', 'sans-serif'],
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        mesh: {
          bg: '#041210',
          panel: 'rgba(255,255,255,0.04)',
          accent: '#1ec9a8',
          violet: '#f0a33a',
          ok: '#34d399',
          warn: '#fbbf24',
        },
      },
      boxShadow: {
        glow: '0 0 40px -10px rgba(34, 211, 238, 0.35)',
      },
    },
  },
  plugins: [],
};
