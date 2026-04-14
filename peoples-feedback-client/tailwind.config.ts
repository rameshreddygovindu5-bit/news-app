import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display:  ['Inter', 'sans-serif'],
        headline: ['Playfair Display', 'Georgia', 'serif'],
        serif:    ['Source Serif 4', 'Georgia', 'serif'],
        telugu:   ['Noto Sans Telugu', 'sans-serif'],
      },
      colors: {
        'pf-saffron': '#FF9933',
        'pf-green':   '#138808',
        'pf-navy':    '#000080',
        'pf-orange':  '#E8621A',
        'pf-gold':    '#FFB300',
        'pf-red':     '#C62828',
      },
      animation: {
        marquee: 'marquee 45s linear infinite',
      },
      keyframes: {
        marquee: {
          '0%':   { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
