/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "bg-dark": "#050712",
        "card-dark": "#111322",
        "card-elevated": "#181A2A",
        accent: "#9C6BFF",
        "text-main": "#FFFFFF",
        "text-muted": "#9CA3AF",
        "chip-muted": "#222433",
        "chip-selected": "#185A4A",
      },
      borderRadius: {
        "3xl": "1.75rem",
        "4xl": "2.5rem",
      },
      boxShadow: {
        card: "0 16px 40px rgba(0,0,0,0.55)",
      },
      backgroundImage: {
        "accent-soft": "linear-gradient(135deg, #9C6BFF 0%, #FF7AC7 100%)",
      },
    },
  },
  plugins: [],
}
