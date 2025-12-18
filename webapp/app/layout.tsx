import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JEX - Personal Voice Assistant",
  description: "Your personal voice assistant inspired by Jarvis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
