import type { Metadata } from "next";
import { IBM_Plex_Sans } from "next/font/google";
import NavBar from "@/components/NavBar";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Sözleşme Analiz Asistanı",
  description: "Sözleşme yükleme, risk analizi ve soru-cevap asistanı",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="tr" className={`${plexSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-paper text-ink">
        <NavBar />
        {children}
      </body>
    </html>
  );
}
