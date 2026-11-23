import type { Metadata, Viewport } from "next";
import { Nunito, Unbounded } from "next/font/google";

import { SkyBackdrop } from "@/components/sky-backdrop";

import "./globals.css";

const bodyFont = Nunito({
  variable: "--font-body-family",
  subsets: ["latin", "cyrillic"],
  display: "swap",
});

const displayFont = Unbounded({
  variable: "--font-display-family",
  subsets: ["latin", "cyrillic"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Индивидуальный проект",
    template: "%s · Индивидуальный проект",
  },
  description:
    "Помогаем школьнику вовремя сформулировать тему и определить продукт проекта, а учителю — увидеть, кто застрял.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#eef6ff" },
    { media: "(prefers-color-scheme: dark)", color: "#070b18" },
  ],
};

// Applies the saved (or system) theme before first paint to avoid a flash.
const themeScript = `(function(){try{var k='project-theme';var s=localStorage.getItem(k);var mq=window.matchMedia('(prefers-color-scheme: dark)');var apply=function(dark){document.documentElement.setAttribute('data-theme',dark?'dark':'light');};if(s==='dark'||s==='light'){apply(s==='dark');}else{apply(mq.matches);if(mq.addEventListener){mq.addEventListener('change',function(event){if(!localStorage.getItem(k)){apply(event.matches);}});}}}catch(error){}})();`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ru"
      suppressHydrationWarning
      className={`${bodyFont.variable} ${displayFont.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="flex min-h-full flex-col font-sans">
        <SkyBackdrop />
        {children}
      </body>
    </html>
  );
}


