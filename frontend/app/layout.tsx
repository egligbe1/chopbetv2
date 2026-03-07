import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit" });

export const metadata: Metadata = {
  title: "ChopBet | Sports Bet Predictions",
  description: "Sports Bet predictions",
  openGraph: {
    title: "ChopBet | Sports Bet Predictions",
    description: "Sports Bet predictions",
    url: "https://chopbets.onrender.com",
    siteName: "ChopBet",
    images: [
      {
        url: "https://chopbets.onrender.com/og-image.png",
        width: 1200,
        height: 630,
        alt: "ChopBet Sports Bet Predictions Preview",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "ChopBet | Sports Bet Predictions",
    description: "Sports Bet predictions",
    images: ["https://chopbets.onrender.com/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${outfit.variable} font-inter bg-background text-foreground min-h-screen flex flex-col`}>
        <Navbar />
        <main className="flex-1 w-full max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-10 lg:py-14">
          {children}
        </main>
        <footer className="border-t border-white/5 bg-black/20 py-10 text-center text-sm text-muted-foreground">
          <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <p>© {new Date().getFullYear()} ChopBet. All rights reserved.</p>
            <p className="mt-2 text-xs opacity-50">Predictions are for informational purposes only. Gamble responsibly.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
