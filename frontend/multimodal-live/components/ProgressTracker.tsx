"use client";

import React from "react";
import { Check, Circle, ExternalLink, ShieldCheck, CreditCard, Layout, Users, FileCheck, HelpCircle } from "lucide-react";
import cn from "classnames";
import { motion } from "framer-motion";

const ICON_MAP: Record<string, any> = {
    ExternalLink,
    CreditCard,
    ShieldCheck,
    Users,
    FileCheck,
    Layout
};

interface ProgressTrackerProps {
    currentStage: number;
    stages: any[];
}

export const ProgressTracker = ({ currentStage, stages }: ProgressTrackerProps) => {
    const displayStages = stages.length > 0 ? stages : [
        { id: 0, label: "Introduction", icon: "Layout" },
        { id: 1, label: "Program Value", icon: "ExternalLink" },
        { id: 2, label: "Payment Structure", icon: "CreditCard" },
    ];
    return (
        <div className="flex flex-col gap-6 py-4">
            <div className="flex items-center gap-2 px-2">
                <div className="w-1.5 h-1.5 rounded-full bg-status-emerald animate-pulse" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
                    Application Journey
                </span>
            </div>

            <div className="space-y-1">
                {displayStages.map((stage, idx) => {
                    const Icon = ICON_MAP[stage.icon] || HelpCircle;
                    const isActive = currentStage === idx;
                    const isCompleted = currentStage > idx;

                    return (
                        <motion.div
                            key={stage.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.1 }}
                            className={cn(
                                "relative flex items-center gap-4 p-4 rounded-2xl transition-all duration-300",
                                isActive ? "bg-brand-sky/30 border border-brand-sky/50 shadow-sm" : "opacity-40"
                            )}
                        >
                            <div className={cn(
                                "w-10 h-10 rounded-xl flex items-center justify-center transition-all",
                                isActive ? "bg-white shadow-md text-brand-royal" :
                                    isCompleted ? "bg-status-emerald/10 text-status-emerald" : "bg-gray-100 text-gray-400"
                            )}>
                                {isCompleted ? <Check size={18} /> : <Icon size={18} />}
                            </div>

                            <div className="flex-1">
                                <h4 className={cn(
                                    "text-xs font-semibold tracking-tight",
                                    isActive ? "text-gray-900" : "text-gray-500"
                                )}>
                                    {stage.label}
                                </h4>
                                {isActive && (
                                    <p className="text-[10px] text-brand-royal/80 font-medium">
                                        Active Step
                                    </p>
                                )}
                            </div>

                            {/* Connector Line */}
                            {idx < displayStages.length - 1 && (
                                <div className="absolute left-9 top-14 w-0.5 h-6 bg-gray-100" />
                            )}
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
};
