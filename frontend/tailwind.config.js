/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#12162B", muted: "#555B73", paper: "#F5F6F8", line: "#E3E5EC",
        indigo: { DEFAULT: "#3640D6", dark: "#2830B0", soft: "#ECEEFF" },
        ok: { DEFAULT: "#137A4F", soft: "#E3F5EC" }, warn: { DEFAULT: "#8A5200", soft: "#FFF3D6" },
        bad: { DEFAULT: "#B42318", soft: "#FDECEA" },
      },
      fontFamily: {
        sans: ['"Segoe UI"', "system-ui", "-apple-system", '"Noto Sans"', '"Noto Sans Devanagari"', "Roboto", "sans-serif"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(18,22,43,.05), 0 4px 14px rgba(18,22,43,.05)",
        brut: "3px 3px 0 0 #12162B", "brut-sm": "2px 2px 0 0 #12162B",
      },
      borderRadius: { tile: "20px" },
    },
  },
  plugins: [],
};
