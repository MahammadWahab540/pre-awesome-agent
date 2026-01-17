import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./multimodal-live/**/*.{js,ts,jsx,tsx,mdx}",
        "./contexts/**/*.{js,ts,jsx,tsx,mdx}",
        "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
        "./lib/**/*.{js,ts,jsx,tsx,mdx}",
        "./utils/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "var(--background)",
                foreground: "var(--foreground)",
                brand: {
                    sky: "#C9F0FF",
                    lavender: "#E7D9FF",
                },
                status: {
                    emerald: "#10B981",
                    ruby: "#EF4444",
                    royal: "#3B82F6",
                }
            },
            fontFamily: {
                sans: ["Inter", "ui-sans-serif", "system-ui"],
            },
            animation: {
                'float-slow': 'float 20s ease-in-out infinite',
                'pulse-slow': 'pulse 15s ease-in-out infinite',
            },
            keyframes: {
                float: {
                    '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
                    '33%': { transform: 'translate(100px, 50px) scale(1.1)' },
                    '66%': { transform: 'translate(-50px, 100px) scale(0.95)' },
                }
            }
        },
    },
    plugins: [],
};
export default config;
