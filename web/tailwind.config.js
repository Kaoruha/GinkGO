/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
      extend: {
          animation:{
              'pulse-slow':"pulse-slow 1s infinite",
              'pulse-fast':"pulse-slow .5s infinite",
          },
          keyframes:{
              'pulse-slow':{
                  '0%, 100%':{opacity:1},
                  '50%':{opacity:.2},
              }
          },
      },
  },
  plugins: [],
}

