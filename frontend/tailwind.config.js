export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        medblue: '#2563EB',
        medbluehover: '#1D4ED8',
      }
    },
  },
  plugins: [],
}
