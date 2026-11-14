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
        // CyberSleuth AI dark cyber-forensics palette
        background: '#080D18',
        sidebar: '#0B1220',
        card: '#111B2B',
        secondary: '#162338',
        border: '#1E2A3B',
        primary: {
          blue: '#3B82F6',
          cyan: '#22D3EE',
        },
        text: {
          main: '#E6F0FF',
          secondary: '#91A4BE',
        },
        success: '#34D399',
        warning: '#FBBF24',
        error: '#F87171',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      borderRadius: {
        lg: '0.75rem',
        xl: '1rem',
      },
      boxShadow: {
        'cyber': '0 0 20px rgba(59, 130, 246, 0.15)',
        'cyber-cyan': '0 0 20px rgba(34, 211, 238, 0.15)',
        'glow-blue': '0 0 15px rgba(59, 130, 246, 0.3)',
        'glow-cyan': '0 0 15px rgba(34, 211, 238, 0.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scan': 'scan 2s linear infinite',
      },
      keyframes: {
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
      },
    },
  },
  plugins: [],
}
