"use client";

import React from "react";
import { Mic, MicOff, PhoneOff } from "lucide-react";
import { motion } from "framer-motion";
import cn from "classnames";

interface MayaControlsProps {
    isMuted: boolean;
    onToggleMute: () => void;
    onEndCall: () => void;
}

export const MayaControls = ({ isMuted, onToggleMute, onEndCall }: MayaControlsProps) => {
    return (
        <div className="flex items-center justify-center p-8 z-50">
            <div className="bg-white/40 backdrop-blur-xl border border-white/60 p-2 rounded-[28px] shadow-2xl flex items-center gap-3">
                {/* Mute Button */}
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={onToggleMute}
                    className={cn(
                        "w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300",
                        isMuted
                            ? "bg-status-ruby text-white shadow-lg shadow-red-200/50"
                            : "bg-white hover:bg-gray-50 text-gray-900 shadow-sm"
                    )}
                >
                    {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
                </motion.button>

                {/* End Call Button */}
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={onEndCall}
                    className="w-14 h-14 rounded-2xl bg-gray-900 text-white flex items-center justify-center shadow-xl shadow-gray-300/50 hover:bg-black transition-all"
                >
                    <PhoneOff size={24} />
                </motion.button>
            </div>
        </div>
    );
};
