import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Deakyne.me - Developer API Documentation",
  description: "Interactive API documentation and developer portal for Deakyne.Dev",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
