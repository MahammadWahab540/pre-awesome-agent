"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { v4 as uuidv4 } from "uuid";
import { User, Phone, ArrowRight, Trash2, Clock, MessageSquare, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import cn from "classnames";
import { SessionStore, SessionData } from "@/lib/multimodal-live/session-store";

export default function Home() {
    const [mobileNumber, setMobileNumber] = useState("");
    const [fullName, setFullName] = useState("");
    const [language, setLanguage] = useState("English");
    const [recentSessions, setRecentSessions] = useState<SessionData[]>([]);
    const router = useRouter();

    useEffect(() => {
        if (mobileNumber.length >= 10) {
            setRecentSessions(SessionStore.getSessions(mobileNumber));
        } else {
            setRecentSessions([]);
        }
    }, [mobileNumber]);

    const handleStartNew = () => {
        if (mobileNumber.length < 10 || !fullName) return;
        const sessionId = uuidv4();

        // Save session with user preferences for later resumption
        SessionStore.addSession({
            sessionId,
            mobileNumber,
            currentStage: 0,
            title: `Session with ${fullName}`,
            userName: fullName,
            userLanguage: language
        });

        const query = new URLSearchParams({
            name: fullName,
            lang: language
        }).toString();
        router.push(`/${mobileNumber}/${sessionId}?${query}`);
    };

    const handleResume = (sessionId: string) => {
        // Find the session to get stored user preferences
        const session = recentSessions.find(s => s.sessionId === sessionId);
        if (session?.userName || session?.userLanguage) {
            const query = new URLSearchParams({
                name: session.userName || "",
                lang: session.userLanguage || "English"
            }).toString();
            router.push(`/${mobileNumber}/${sessionId}?${query}`);
        } else {
            router.push(`/${mobileNumber}/${sessionId}`);
        }
    };

    const handleDelete = (e: React.MouseEvent, sessionId: string) => {
        e.stopPropagation();
        SessionStore.deleteSession(mobileNumber, sessionId);
        setRecentSessions(SessionStore.getSessions(mobileNumber));
    };

    return (
        <main className="min-h-screen flex flex-col items-center justify-center p-6 relative overflow-hidden bg-white">
            {/* Ambient Background Blobs */}
            <div className="maya-bg-container">
                <div className="blob-blue animate-pulse-slow" />
                <div className="blob-purple animate-pulse-slow" style={{ animationDelay: '2s' }} />
            </div>

            <div className="w-full max-w-md z-10">
                {/* Login Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white/40 backdrop-blur-xl border border-white/60 rounded-[32px] p-8 shadow-[0_32px_64px_-12px_rgba(0,0,0,0.1)] transition-all duration-500"
                >
                    {/* Logo */}
                    <div className="flex justify-center mb-8">
                        <div className="w-16 h-16 bg-gray-900 rounded-2xl flex items-center justify-center shadow-lg">
                            <span className="text-white font-bold text-2xl">N</span>
                        </div>
                    </div>

                    {/* Header */}
                    <div className="text-center space-y-2 mb-8">
                        <h1 className="text-3xl font-semibold tracking-tight text-gray-900">
                            Welcome to Maya
                        </h1>
                        <p className="text-gray-500 text-sm">
                            Please verify your identity to continue
                        </p>
                    </div>

                    {/* Form */}
                    <div className="space-y-6">
                        {/* Mobile Number Input */}
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-wider text-gray-400 px-1">
                                Mobile Number
                            </label>
                            <div className="relative group">
                                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-brand-royal transition-colors">
                                    <Phone size={18} />
                                </div>
                                <input
                                    type="tel"
                                    value={mobileNumber}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMobileNumber(e.target.value.replace(/\D/g, '').slice(0, 10))}
                                    placeholder="Enter your number"
                                    className="w-full bg-white/50 border border-transparent focus:border-white/80 rounded-2xl pl-12 pr-4 py-4 text-gray-900 placeholder:text-gray-400 outline-none focus:ring-4 focus:ring-blue-100/50 transition-all font-medium"
                                />
                                {mobileNumber.length > 0 && (
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-bold text-gray-300">
                                        {mobileNumber.length}/10
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Full Name Input */}
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-wider text-gray-400 px-1">
                                Full Name
                            </label>
                            <div className="relative group">
                                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-brand-royal transition-colors">
                                    <User size={18} />
                                </div>
                                <input
                                    type="text"
                                    value={fullName}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFullName(e.target.value)}
                                    placeholder="Enter your name"
                                    className="w-full bg-white/50 border border-transparent focus:border-white/80 rounded-2xl pl-12 pr-4 py-4 text-gray-900 placeholder:text-gray-400 outline-none focus:ring-4 focus:ring-blue-100/50 transition-all font-medium"
                                />
                            </div>
                        </div>

                        {/* Language Selection */}
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-wider text-gray-400 px-1">
                                Preferred Language
                            </label>
                            <select
                                value={language}
                                onChange={(e) => setLanguage(e.target.value)}
                                className="w-full bg-white/50 border border-transparent focus:border-white/80 rounded-2xl px-4 py-4 text-gray-900 outline-none focus:ring-4 focus:ring-blue-100/50 transition-all font-medium appearance-none"
                            >
                                <option value="English">English</option>
                                <option value="Hindi">Hindi</option>
                                <option value="Telugu">Telugu</option>
                                <option value="Tamil">Tamil</option>
                                <option value="Kannada">Kannada</option>
                                <option value="Malayalam">Malayalam</option>
                            </select>
                        </div>

                        {/* Submit Button */}
                        <motion.button
                            whileTap={{ scale: 0.96 }}
                            disabled={mobileNumber.length < 10 || !fullName}
                            onClick={handleStartNew}
                            className={cn(
                                "w-full py-4 rounded-2xl font-semibold text-white flex items-center justify-center gap-2 transition-all duration-300 shadow-xl",
                                (mobileNumber.length < 10 || !fullName)
                                    ? "bg-gray-200 text-gray-400 cursor-not-allowed shadow-none"
                                    : "bg-gray-900 hover:bg-gray-800 active:bg-black shadow-gray-200 hover:shadow-gray-300"
                            )}
                        >
                            <span>Start Session</span>
                            <ArrowRight size={18} className={(mobileNumber.length === 10 && fullName) ? "animate-bounce-x" : ""} />
                        </motion.button>
                    </div>

                    {/* Recent Sessions */}
                    <AnimatePresence>
                        {recentSessions.length > 0 && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: "auto" }}
                                exit={{ opacity: 0, height: 0 }}
                                className="mt-8 pt-6 border-t border-white/40 space-y-4"
                            >
                                <div className="flex items-center gap-2 px-1">
                                    <Clock size={14} className="text-gray-400" />
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                                        Recent Sessions
                                    </span>
                                </div>
                                <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                                    {recentSessions.map((session) => (
                                        <div
                                            key={session.sessionId}
                                            onClick={() => handleResume(session.sessionId)}
                                            className="group flex items-center justify-between p-3 bg-white/20 hover:bg-white/40 border border-white/40 rounded-xl cursor-pointer transition-all active:scale-[0.98]"
                                        >
                                            <div className="flex-1 min-w-0">
                                                <h4 className="text-xs font-semibold text-gray-900 truncate">
                                                    {session.title || "Consultation Session"}
                                                </h4>
                                                <p className="text-[10px] text-gray-500">
                                                    Stage {session.currentStage + 1} • {new Date(session.timestamp).toLocaleDateString()}
                                                </p>
                                            </div>
                                            <button
                                                onClick={(e: React.MouseEvent) => handleDelete(e, session.sessionId)}
                                                className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>

                {/* Footer */}
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1 }}
                    className="mt-8 text-center text-[10px] font-medium text-gray-400 uppercase tracking-widest"
                >
                    SECURE MULTIMODAL INTERFACE • NEXWAVE
                </motion.p>
            </div>

            <style jsx global>{`
                @keyframes bounce-x {
                    0%, 100% { transform: translateX(0); }
                    50% { transform: translateX(4px); }
                }
                .animate-bounce-x {
                    animation: bounce-x 1s infinite;
                }
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
                .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: rgba(0, 0, 0, 0.1);
                }
            `}</style>
        </main>
    );
}
