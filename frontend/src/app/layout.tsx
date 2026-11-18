import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "UniAdmit AI - Hệ Thống Phân Tích Tuyển Sinh & Big Data MLOps",
  description: "Dự báo xác suất trúng tuyển liên tục, cố vấn giỏ nguyện vọng Smart Wishlist, phân tích Google Trends và MLOps Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className="h-full">
      <body className="min-h-full flex flex-col font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
