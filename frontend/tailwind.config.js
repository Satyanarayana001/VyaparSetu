/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#26332B", muted: "#66736A", paper: "#F7F8F4", line: "#E4E9E2",
        forest: { DEFAULT: "#174D38", dark: "#103D2B", soft: "#EAF3ED" },
        indigo: { DEFAULT: "#174D38", dark: "#103D2B", soft: "#EAF3ED" },
        amber: { soft: "#FFF4DF", ink: "#875313", line: "#F0D9A8" },
        ok: { DEFAULT: "#137A4F", soft: "#E3F5EC" }, warn: { DEFAULT: "#8A5200", soft: "#FFF3D6" },
        bad: { DEFAULT: "#B42318", soft: "#FDECEA" },
      },
      fontFamily: {
        sans: ['"Inter"', '"Segoe UI"', "system-ui", "-apple-system", '"Noto Sans"', '"Noto Sans Devanagari"', "Roboto", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(25,45,33,.035), 0 8px 24px rgba(25,45,33,.045)",
        float: "0 12px 32px rgba(25,45,33,.10)",
        brut: "0 1px 2px rgba(25,45,33,.06), 0 4px 12px rgba(25,45,33,.05)",
        "brut-sm": "0 1px 2px rgba(25,45,33,.06)",
      },
      borderRadius: { tile: "18px" },
    },
  },
  plugins: [],
};
