import type { Metadata } from "next";
import "./globals.css";
import Masthead from "@/components/layout/Masthead";
import NavTabs from "@/components/layout/NavTabs";
import IngestStatusBanner from "@/components/layout/IngestStatusBanner";

export const metadata: Metadata = {
  title: "The Daily Query - Reddit Research Intelligence",
  description:
    "Semantic search, network analysis, topic clustering, and AI-powered intelligence across Reddit datasets.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-paper px-2 md:px-3">
        <div className="edition-shell min-h-screen">
          <IngestStatusBanner />
          <Masthead />
          <NavTabs />
          <main className="edition-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
