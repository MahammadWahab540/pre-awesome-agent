"use client";

import React from "react";
import { Shield, WifiOff, RefreshCw } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import cn from "classnames";

interface MayaHeaderProps {
    isConnected: boolean;
    isOffline: boolean;
    userName?: string;
    mobileNumber?: string;
}

export const MayaHeader = ({ isConnected, isOffline, userName, mobileNumber }: MayaHeaderProps) => {
    return (
        <header className="w-full flex flex-col gap-0 z-50">
            {/* Offline Banner */}
            <AnimatePresence>
                {isOffline && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="bg-[#FF4D4D] text-white py-3 px-6 flex items-center justify-between overflow-hidden"
                    >
                        <div className="flex items-center gap-3">
                            <WifiOff size={18} className="animate-pulse" />
                            <span className="text-sm font-semibold tracking-tight">
                                Connection unstable. Trying to reconnect...
                            </span>
                        </div>
                        <button className="flex items-center gap-2 bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-95">
                            <RefreshCw size={14} />
                            Retry
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className="flex items-center justify-between p-6 bg-white/30 backdrop-blur-md border-b border-white/40">
                {/* Branding & Status */}
                <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-gray-900 rounded-xl flex items-center justify-center">
                        <span className="text-white font-bold text-xl">N</span>
                    </div>
                    <div className="flex flex-col">
                        <h2 className="text-sm font-bold text-gray-900 leading-none mb-1.5">Maya AI</h2>
                        <div className="flex items-center gap-2">
                            <div className={cn(
                                "w-1.5 h-1.5 rounded-full",
                                isConnected ? "bg-status-emerald shadow-[0_0_8px_#10B981]" : "bg-status-ruby"
                            )} />
                            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                                {isConnected ? "Live Session" : "Disconnected"}
                            </span>
                        </div>
                    </div>
                </div>

                {/* User Info & Status Pill */}
                <div className="flex items-center gap-6">
                    <div className="hidden md:flex flex-col items-end gap-0.5">
                        <span className="text-xs font-bold text-gray-900">{userName || "User"}</span>
                        <span className="text-[10px] font-medium text-gray-400">ID: {mobileNumber || "9999999999"}</span>
                    </div>
                    <div className="h-8 w-px bg-gray-200 hidden md:block" />
                    <div className="bg-white/60 border border-white/80 px-4 py-2 rounded-full flex items-center gap-2 shadow-sm">
                        <Shield size={14} className="text-brand-royal" />
                        <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-gray-800">
                            Verified
                        </span>
                    </div>
                </div>
            </div>
        </header>
    );
};
