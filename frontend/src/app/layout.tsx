import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeContext";
import { UserProvider } from "@/components/UserContext";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: "Zasiłkowy Przewodnik Przyszłego Rodzica — ZUS HackNation 2026",
  description:
    "Kompleksowy przewodnik i zintegrowany kalkulator świadczeń ZUS w okresie ciąży i rodzicielstwa.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pl" suppressHydrationWarning>
      <body className="flex min-h-screen flex-col">
        <ThemeProvider>
          <UserProvider>
            <Navbar />
            <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
              {children}
            </main>
            <Footer />
          </UserProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
