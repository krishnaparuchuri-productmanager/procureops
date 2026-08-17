/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Warm paper aesthetic — matches the portfolio site's design tokens
        // (--paper, --ink, --accent etc. at krishnaparuchuri.com). ProcureOps
        // is the first vertical dashboard to actually use this system rather
        // than the generic Tailwind gray/indigo the older verticals use.
        paper: {
          DEFAULT: '#f5f1ea',
          deep: '#ece6db',
        },
        ink: {
          DEFAULT: '#1a1a1a',
          soft: '#3a3a3a',
          muted: '#6b6660',
        },
        accent: '#b8451f',
        rule: 'rgba(26, 26, 26, 0.12)',
        'rule-strong': 'rgba(26, 26, 26, 0.25)',
      },
      fontFamily: {
        serif: ['Fraunces', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '0px',
      },
    },
  },
  plugins: [],
}
