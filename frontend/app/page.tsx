"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { v4 as uuidv4 } from "uuid";
import { Phone, Play, RotateCcw, User, Clock, MessageSquare, Briefcase, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import cn from "classnames";
import { SessionStore, SessionData } from "@/lib/multimodal-live/session-store";

export default function Home() {
    const [mobileNumber, setMobileNumber] = useState("");
    const [recentSessions, setRecentSessions] = useState<SessionData[]>([]);
    const [isHovered, setIsHovered] = useState<string | null>(null);
    const router = useRouter();

    useEffect(() => {
        if (mobileNumber.length >= 10) {
            setRecentSessions(SessionStore.getSessions(mobileNumber));
        } else {
            setRecentSessions([]);
        }
    }, [mobileNumber]);

    const handleStartNew = () => {
        if (mobileNumber.length < 10) return;
        const sessionId = uuidv4();
        router.push(`/${mobileNumber}/${sessionId}`);
    };

    const handleResume = (sessionId: string) => {
        router.push(`/${mobileNumber}/${sessionId}`);
    };

    const handleDelete = (e: React.MouseEvent, sessionId: string) => {
        e.stopPropagation();
        SessionStore.deleteSession(mobileNumber, sessionId);
        setRecentSessions(SessionStore.getSessions(mobileNumber));
    };

    return (
        <main className="min-h-screen bg-[#0B0F17] text-white flex flex-col items-center justify-center p-6 relative overflow-hidden">
            {/* Background Orbs */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/20 rounded-full blur-[120px] animate-pulse"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-violet-600/20 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '2s' }}></div>

            <div className="w-full max-w-4xl z-10 space-y-12">
                {/* Header Section */}
                <div className="text-center space-y-4">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-bold uppercase tracking-widest"
                    >
                        <Briefcase className="w-3 h-3" />
                        Next-Gen Consultant Agent
                    </motion.div>
                    <motion.h1
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className="text-5xl md:text-7xl font-bold tracking-tight bg-gradient-to-b from-white to-gray-500 bg-clip-text text-transparent"
                    >
                        AI Business Solutions
                    </motion.h1>
                    <motion.p
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="text-gray-400 text-lg md:text-xl max-w-2xl mx-auto"
                    >
                        Experience the power of multimodal AI. Start a voice consultation or resume your project discovery.
                    </motion.p>
                </div>

                {/* Main Action Card */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3 }}
                    className="grid md:grid-cols-2 gap-8"
                >
                    {/* Input Area */}
                    <div className="bg-white/[0.03] backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-8 flex flex-col justify-between">
                        <div className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-400 flex items-center gap-2">
                                    <Phone className="w-4 h-4" />
                                    Verify Identity
                                </label>
                                <div className="p-4 bg-indigo-500/5 border border-indigo-500/10 rounded-2xl">
                                    <p className="text-xs text-indigo-300/70 mb-3 leading-relaxed">
                                        Enter your mobile number to access your workspace. We store your session history locally for quick resumption.
                                    </p>
                                    <div className="relative group">
                                        <input
                                            type="tel"
                                            value={mobileNumber}
                                            onChange={(e) => setMobileNumber(e.target.value.replace(/\D/g, '').slice(0, 10))}
                                            placeholder="Mobile Number"
                                            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-lg font-mono focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none transition-all placeholder:text-gray-600"
                                        />
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 text-xs">
                                            {mobileNumber.length}/10
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {recentSessions.length === 0 ? (
                            <button
                                disabled={mobileNumber.length < 10}
                                onClick={handleStartNew}
                                className={cn(
                                    "relative w-full overflow-hidden rounded-2xl py-4 font-bold text-lg flex items-center justify-center gap-3 transition-all active:scale-95 group",
                                    mobileNumber.length < 10
                                        ? "bg-gray-800 text-gray-500 cursor-not-allowed border border-white/5"
                                        : "bg-indigo-600 text-white shadow-[0_0_20px_rgba(79,70,229,0.3)] hover:shadow-[0_0_30px_rgba(79,70,229,0.5)] hover:bg-indigo-500"
                                )}
                            >
                                <Play className="w-5 h-5 fill-current" />
                                Start New Session
                                {mobileNumber.length >= 10 && (
                                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]"></div>
                                )}
                            </button>
                        ) : (
                            <div className="p-4 bg-amber-500/5 border border-amber-500/10 rounded-2xl">
                                <p className="text-xs text-amber-300/70 text-center italic">
                                    You have an active session for this number. <br />Delete it to start fresh or resume below.
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Recent Sessions Area */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-2 px-2">
                            <Clock className="w-4 h-4" />
                            Recent Projects
                        </h3>
                        <div className="space-y-3 min-h-[300px]">
                            <AnimatePresence mode="popLayout">
                                {mobileNumber.length < 10 ? (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        className="h-full flex flex-col items-center justify-center text-center p-8 border-2 border-dashed border-white/5 rounded-3xl"
                                    >
                                        <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-4">
                                            <User className="w-6 h-6 text-gray-600" />
                                        </div>
                                        <p className="text-gray-500 text-sm">Enter your number to view<br />previous consultations</p>
                                    </motion.div>
                                ) : recentSessions.length === 0 ? (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        className="h-full flex flex-col items-center justify-center text-center p-8 border-2 border-dashed border-white/5 rounded-3xl"
                                    >
                                        <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-4">
                                            <MessageSquare className="w-6 h-6 text-indigo-500/50" />
                                        </div>
                                        <p className="text-gray-500 text-sm">No sessions found for this number.<br />Start your first project!</p>
                                    </motion.div>
                                ) : (
                                    recentSessions.map((session, idx) => (
                                        <motion.div
                                            key={session.sessionId}
                                            initial={{ opacity: 0, x: 20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                            onMouseEnter={() => setIsHovered(session.sessionId)}
                                            onMouseLeave={() => setIsHovered(null)}
                                            onClick={() => handleResume(session.sessionId)}
                                            className="group relative bg-white/[0.03] hover:bg-white/[0.07] border border-white/10 hover:border-indigo-500/50 rounded-2xl p-4 cursor-pointer transition-all active:scale-[0.98]"
                                        >
                                            <div className="flex items-center justify-between gap-4">
                                                <div className="space-y-1 flex-1">
                                                    <h4 className="font-semibold text-gray-200 group-hover:text-white transition-colors truncate">
                                                        {session.title || 'Untitled Project'}
                                                    </h4>
                                                    <div className="flex items-center gap-3 text-[10px] text-gray-500">
                                                        <span>{new Date(session.timestamp).toLocaleDateString()}</span>
                                                        <span className="w-1 h-1 rounded-full bg-gray-700"></span>
                                                        <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400">Stage {session.currentStage + 1}</span>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <button
                                                        onClick={(e) => handleDelete(e, session.sessionId)}
                                                        className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all"
                                                        title="Delete Session"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                    <div className={cn(
                                                        "px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider flex items-center gap-2 transition-all",
                                                        isHovered === session.sessionId ? "bg-indigo-600 text-white scale-105" : "bg-white/5 text-gray-400"
                                                    )}>
                                                        <RotateCcw className="w-3.5 h-3.5" />
                                                        Resume Session
                                                    </div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))
                                )}
                            </AnimatePresence>
                        </div>
                    </div>
                </motion.div>

                {/* Footer Info */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="text-center text-gray-600 text-sm"
                >
                    All sessions are stored securely in your browser's local cache.
                </motion.div>
            </div>
        </main>
    );
}
