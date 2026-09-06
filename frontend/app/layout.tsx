import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PPV Memory Dashboard",
  description: "Purchase price variance review and resolution dashboard",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col text-zinc-800">
        <header className="sticky top-0 z-10 border-b border-zinc-200/70 bg-white/70 backdrop-blur-md">
          <div className="mx-auto flex w-full max-w-5xl items-center gap-2.5 px-6 py-3.5">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="text-sm font-semibold tracking-tight text-zinc-900">
                PPV Memory
              </span>
            </Link>
          </div>
        </header>
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
