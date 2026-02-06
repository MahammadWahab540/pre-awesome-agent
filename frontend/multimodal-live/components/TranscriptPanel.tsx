"use client";

import React, { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import cn from "classnames";

interface Message {
    id: string;
    role: "user" | "model";
    text: string;
    timestamp: number;
}

interface TranscriptPanelProps {
    messages: Message[];
}

export const TranscriptPanel = ({ messages }: TranscriptPanelProps) => {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: "smooth"
            });
        }
    }, [messages]);

    return (
        <div className="relative h-full flex flex-col pt-4 overflow-hidden">
            <div className="flex items-center gap-2 px-6 mb-4">
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
                    Live Transcript
                </span>
            </div>

            {/* Glass Container with Masking */}
            <div className="relative flex-1 overflow-hidden">
                {/* Masking Gradients */}
                <div className="absolute top-0 left-0 right-0 h-10 bg-gradient-to-b from-white/40 to-transparent z-10" />
                <div className="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-white/40 to-transparent z-10" />

                <div
                    ref={scrollRef}
                    className="h-full overflow-y-auto px-6 py-6 space-y-6 custom-scrollbar"
                >
                    <AnimatePresence initial={false}>
                        {messages.map((msg) => (
                            <motion.div
                                key={msg.id}
                                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                className={cn(
                                    "flex flex-col max-w-[85%]",
                                    msg.role === "user" ? "ml-auto items-end" : "items-start"
                                )}
                            >
                                <div className={cn(
                                    "px-5 py-3.5 rounded-[22px] text-sm leading-relaxed",
                                    msg.role === "user"
                                        ? "bg-status-royal text-white shadow-lg shadow-blue-200/50 rounded-tr-none"
                                        : "bg-white/60 backdrop-blur-md border border-white/80 text-gray-800 shadow-sm rounded-tl-none"
                                )}>
                                    {msg.text}
                                </div>
                                <span className="text-[10px] mt-1.5 font-bold text-gray-400 px-1">
                                    {msg.role === "user" ? "You" : "Maya"}
                                </span>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            </div>

            <style jsx>{`
                .custom-scrollbar::-webkit-scrollbar {
                    width: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: rgba(0, 0, 0, 0.05);
                    border-radius: 10px;
                }
            `}</style>
        </div>
    );
};
