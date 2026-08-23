import localFont from "next/font/local";
import { Noto_Nastaliq_Urdu } from "next/font/google";

export const switzer = localFont({
  src: [
    { path: "./fonts/switzer-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/switzer-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/switzer-600.woff2", weight: "600", style: "normal" },
    { path: "./fonts/switzer-700.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-sans",
  display: "swap",
});

export const array = localFont({
  src: [
    { path: "./fonts/array-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/array-700.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-display",
  display: "swap",
});

export const sourceSerifDisplay = localFont({
  src: [
    { path: "./fonts/source-serif-4-display-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/source-serif-4-display-600.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-login-display",
  display: "swap",
});

export const notoNastaliqUrdu = Noto_Nastaliq_Urdu({
  subsets: ["arabic"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-urdu",
  display: "swap",
  adjustFontFallback: false,
});
