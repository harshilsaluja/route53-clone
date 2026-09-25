import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@cloudscape-design/global-styles/index.css";
import "./globals.css";
import { Providers } from "@/app/providers";

export const metadata: Metadata = {
  title: "AWS Route 53 Clone",
  description: "Route 53 clone software engineering assignment",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
