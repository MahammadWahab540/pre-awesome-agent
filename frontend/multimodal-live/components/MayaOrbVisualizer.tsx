"use client";

import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface MayaOrbVisualizerProps {
    isListening: boolean;
    isSpeaking: boolean;
    volume: number; // 0 to 1
}

export const MayaOrbVisualizer = ({ isListening, isSpeaking, volume }: MayaOrbVisualizerProps) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            const x = (e.clientX / window.innerWidth - 0.5) * 20;
            const y = (e.clientY / window.innerHeight - 0.5) * 20;
            setMousePos({ x, y });
        };
        window.addEventListener("mousemove", handleMouseMove);
        return () => window.removeEventListener("mousemove", handleMouseMove);
    }, []);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        let animationFrame: number;
        const render = () => {
            const width = canvas.width = 400;
            const height = canvas.height = 400;
            const centerX = width / 2;
            const centerY = height / 2;

            ctx.clearRect(0, 0, width, height);

            // 1. Draw Halo (Radiation Lines)
            if (isSpeaking || isListening) {
                const step = (Math.PI * 2) / 60;
                const baseRadius = 140;
                const maxExtra = 40 * volume;

                ctx.beginPath();
                ctx.strokeStyle = "rgba(201, 240, 255, 0.4)";
                ctx.lineWidth = 2;
                for (let i = 0; i < Math.PI * 2; i += step) {
                    const dynamicExtra = Math.random() * maxExtra;
                    const x1 = centerX + Math.cos(i) * baseRadius;
                    const y1 = centerY + Math.sin(i) * baseRadius;
                    const x2 = centerX + Math.cos(i) * (baseRadius + dynamicExtra);
                    const y2 = centerY + Math.sin(i) * (baseRadius + dynamicExtra);
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);
                }
                ctx.stroke();
            }

            animationFrame = requestAnimationFrame(render);
        };

        render();
        return () => cancelAnimationFrame(animationFrame);
    }, [volume, isSpeaking, isListening]);

    return (
        <div className="relative w-full h-[500px] flex items-center justify-center">
            {/* The Halo Canvas */}
            <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />

            {/* The Glass Orb */}
            <motion.div
                animate={{
                    scale: 1 + volume * 0.1,
                    y: [0, -10, 0]
                }}
                transition={{
                    y: { duration: 4, repeat: Infinity, ease: "easeInOut" },
                    scale: { type: "spring", stiffness: 300, damping: 20 }
                }}
                className="relative w-64 h-64 rounded-full bg-white/20 backdrop-blur-2xl border border-white/40 shadow-[0_32px_120px_-16px_rgba(201,240,255,0.4)] flex items-center justify-center overflow-hidden"
            >
                {/* Glowing Core */}
                <div className="absolute inset-0 bg-gradient-to-br from-brand-sky/40 via-white/10 to-brand-lavender/30 mix-blend-overlay" />

                {/* Parallax Face Container */}
                <div
                    className="relative z-10 flex flex-col items-center gap-6 transition-transform duration-300"
                    style={{ transform: `translate(${mousePos.x}px, ${mousePos.y}px)` }}
                >
                    {/* Eyes */}
                    <div className="flex gap-10">
                        <motion.div
                            animate={{ scaleY: [1, 1, 0.1, 1, 1] }}
                            transition={{ duration: 3, repeat: Infinity, repeatDelay: 5 }}
                            className="w-2.5 h-2.5 bg-gray-900 rounded-full"
                        />
                        <motion.div
                            animate={{ scaleY: [1, 1, 0.1, 1, 1] }}
                            transition={{ duration: 3, repeat: Infinity, repeatDelay: 5 }}
                            className="w-2.5 h-2.5 bg-gray-900 rounded-full"
                        />
                    </div>

                    {/* Mouth / Waveform */}
                    <div className="flex items-end gap-1 h-6">
                        {[0.4, 0.7, 1, 0.7, 0.4].map((h, i) => (
                            <motion.div
                                key={i}
                                animate={{
                                    height: isSpeaking || isListening ? (h * 100 * volume + 4) : 2,
                                    opacity: isSpeaking || isListening ? 1 : 0.3
                                }}
                                className="w-1 bg-gray-900 rounded-full"
                            />
                        ))}
                    </div>
                </div>

                {/* Glass Reflection */}
                <div className="absolute top-[10%] left-[20%] w-[40%] h-[20%] bg-white/40 blur-xl rounded-full -rotate-45" />
            </motion.div>

            {/* Status Text (Floating below) */}
            <div className="absolute bottom-10 flex flex-col items-center gap-2">
                <AnimatePresence mode="wait">
                    <motion.span
                        key={isSpeaking ? "maya" : isListening ? "user" : "waiting"}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="text-xs font-bold uppercase tracking-widest text-gray-400"
                    >
                        {isSpeaking ? "Maya is speaking" : isListening ? "Listening to you" : "Maya is ready"}
                    </motion.span>
                </AnimatePresence>
            </div>
        </div>
    );
};
