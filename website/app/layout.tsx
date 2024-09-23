import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import Script from "next/script";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata = {
  title: "UCSD Tickets",
  description: "See parking tickets being issued in realtime",
};
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <>
      {process.env.NODE_ENV === "production" && (
        <Script
          async
          src="https://stats.superfx.dev/script.js"
          data-website-id="9794b6e8-8500-4a2f-a3b4-ee2757c0b6e7"
        />
      )}
      <html lang="en">
        <body className="bg-gray-100 min-h-screen flex flex-col items-center justify-center">
          {children}
        </body>
      </html>
    </>
  );
}
