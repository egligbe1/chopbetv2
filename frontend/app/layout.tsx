import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit" });

export const metadata: Metadata = {
  title: "ChopBet | AI Football Predictions",
  description: "Professional-grade football predictions powered by Google Gemini with Search Grounding.",
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
        <main className="flex-1 container mx-auto px-4 py-8">
          {children}
        </main>
        <footer className="border-t border-white/5 bg-black/20 py-8 text-center text-sm text-muted-foreground">
          <div className="container mx-auto px-4">
            <p>© {new Date().getFullYear()} ChopBet. All rights reserved.</p>
            <p className="mt-2 text-xs opacity-50">Predictions are for informational purposes only. Gamble responsibly.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
