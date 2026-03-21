import type { Metadata } from "next";

import "@/app/globals.css";
import { AppProviders } from "@/lib/providers/app-providers";

export const metadata: Metadata = {
  title: "easyStory Web",
  description: "easyStory Web workspace",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
