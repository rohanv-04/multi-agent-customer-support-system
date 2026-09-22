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
        charcoal: {
          950: '#060709',
          900: '#0B0D12',
          850: '#10131A',
          800: '#161B24',
          700: '#232A38',
          600: '#343E52'
        },
        brand: {
          cyan: '#00F2FE',
          blue: '#4FACFE',
          violet: '#7F00FF',
          pink: '#E100FF',
          emerald: '#10B981',
          amber: '#F59E0B',
          rose: '#F43F5E'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      boxShadow: {
        'glass-subtle': '0 4px 20px -2px rgba(0, 0, 0, 0.5), inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',
        'glass-standard': '0 8px 32px 0 rgba(0, 0, 0, 0.55), inset 0 1px 0 0 rgba(255, 255, 255, 0.14)',
        'glass-elevated': '0 16px 48px -4px rgba(0, 0, 0, 0.65), inset 0 1px 0 0 rgba(255, 255, 255, 0.22)',
        'glass-floating': '0 24px 64px -8px rgba(0, 0, 0, 0.75), inset 0 1px 0 0 rgba(255, 255, 255, 0.3)',
        'glow-cyan': '0 0 25px -3px rgba(0, 242, 254, 0.25)',
        'glow-emerald': '0 0 25px -3px rgba(16, 185, 129, 0.25)',
        'glow-rose': '0 0 25px -3px rgba(244, 63, 94, 0.25)',
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float-slow': 'float 8s ease-in-out infinite',
        'ambient-glow': 'ambient 10s ease infinite alternate',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        ambient: {
          '0%': { transform: 'scale(1) translate(0px, 0px)' },
          '50%': { transform: 'scale(1.15) translate(20px, -15px)' },
          '100%': { transform: 'scale(0.95) translate(-15px, 20px)' },
        }
      }
    },
  },
  plugins: [],
}
