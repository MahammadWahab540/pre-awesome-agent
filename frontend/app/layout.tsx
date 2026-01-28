import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "@/app/multimodal-live/multimodal.scss";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Multimodal Live Agent",
    description: "Advanced AI Voice Agent Experience",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <head>
                <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
                <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap" />
                <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
            </head>
            <body className={inter.className}>{children}</body>
        </html>
    );
}
