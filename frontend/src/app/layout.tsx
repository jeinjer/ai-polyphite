import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "AI-Polyphite",
  description: "Laboratorio experimental de mercados de predicción.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es-ES">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
