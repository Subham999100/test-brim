// Brand ramp built on the logo orange #FF6600 (500). For small text use 700 on light surfaces
// (5.5:1 on white) and 400 on dark surfaces; 500 is for fills, icons and large text.
const brandOrange = {
  50: '#fff4eb',
  100: '#ffe6d1',
  200: '#ffc9a1',
  300: '#ffa766',
  400: '#ff8a38',
  500: '#ff6600',
  600: '#d95700',
  700: '#b34700',
  800: '#8c3800',
  900: '#662900',
  950: '#3d1900',
};

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: '#0f172a',
        brand: brandOrange,
        orange: brandOrange,
        sap: brandOrange,
        slate: {
          700: '#252e42',
          750: '#1e2638',
          800: '#161d2d',
          850: '#101624',
          900: '#0b101c',
          950: '#070a12',
        }
      },
      fontFamily: {
        sans: ['"DM Sans"', 'Inter', 'system-ui', 'sans-serif'],
        display: ['Manrope', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'brand': '0 10px 30px -10px rgba(255, 102, 0, 0.35)',
        'brand-glow': '0 0 25px rgba(255, 102, 0, 0.45)',
      }
    },
  },
  plugins: [],
}
