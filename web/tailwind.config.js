/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Status colors
        status: {
          running: '#10B981',
          paused: '#F59E0B',
          error: '#EF4444',
          success: '#10B981',
          warning: '#F59E0B',
        },
        // Node state colors
        node: {
          active: '#3B82F6',
          executing: '#10B981',
          failed: '#EF4444',
          idle: '#6B7280',
        },
      },
      animation: {
        'pulse-green': 'pulse-green 1.5s ease-in-out infinite',
        'shake': 'shake 0.3s ease-in-out',
      },
      keyframes: {
        'pulse-green': {
          '0%, 100%': {
            borderColor: '#10B981',
            transform: 'scale(1)',
          },
          '50%': {
            borderColor: '#34D399',
            transform: 'scale(1.02)',
          },
        },
        'shake': {
          '0%, 100%': { transform: 'translateX(0)' },
          '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-5px)' },
          '20%, 40%, 60%, 80%': { transform: 'translateX(5px)' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
