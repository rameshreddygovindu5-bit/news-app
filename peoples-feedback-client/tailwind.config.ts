import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['DM Sans', 'sans-serif'],
        serif: ['Source Serif 4', 'Georgia', 'serif'],
      },
      colors: {
        'pf-orange': '#FF9933',
        'pf-green': '#138808',
        'pf-navy': '#000080',
      },
    },
  },
  plugins: [],
} satisfies Config;
