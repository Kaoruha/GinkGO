/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1890ff',
          light: '#40a9ff',
          dark: '#096dd9',
        },
        success: '#52c41a',
        warning: '#faad14',
        error: '#f5222d',
      },
    },
  },
  plugins: [],
}
