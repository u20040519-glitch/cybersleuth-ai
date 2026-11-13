/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nexus: {
          dark: '#0f172a',
          deeper: '#020617',
          accent: '#818cf8',
          accentHover: '#a5b4fc',
          danger: '#ef4444',
          success: '#22c55e',
          warning: '#f59e0b',
          muted: '#64748b',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'lg': '0.75rem',
        'xl': '1rem',
      },
    },
  },
  plugins: [],
}
