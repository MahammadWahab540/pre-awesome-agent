import React from 'react';
import { ArrowLeft } from 'lucide-react';

interface Stage {
    id: number;
    name: string;
    key: string;
    description: string;
    icon: string;
}

interface NorthStarNavProps {
    stages: Stage[];
    currentStage: number;
    completedStages: boolean[];
    projectTitle: string;
    onBack: () => void;
}

export function NorthStarNav({ stages, currentStage, completedStages, projectTitle, onBack }: NorthStarNavProps) {
    return (
        <div className="h-16 shrink-0 border-b border-white/10 flex items-center justify-between px-6 bg-gradient-to-r from-[#0B0F17] via-[#16213e] to-[#0B0F17]">
            {/* Back Button */}
            <button
                onClick={onBack}
                className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors group"
            >
                <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                <span className="text-sm font-medium">Back</span>
            </button>

            {/* Stage Progress Boxes */}
            <div className="flex items-center gap-3">
                {stages.map((stage, index) => {
                    const isCurrent = index === currentStage;
                    const isCompleted = completedStages[index];
                    const isUpcoming = index > currentStage;

                    return (
                        <div
                            key={stage.id}
                            className={`
                relative flex items-center gap-3 px-5 py-2.5 rounded-lg transition-all duration-300
                ${isCurrent
                                    ? 'bg-gradient-to-r from-indigo-600 to-purple-600 shadow-lg shadow-indigo-500/30 scale-105'
                                    : isCompleted
                                        ? 'bg-gradient-to-r from-green-600/80 to-emerald-600/80 opacity-70'
                                        : 'bg-white/5 opacity-50'
                                }
              `}
                        >
                            {/* Stage Number/Icon */}
                            <div className={`
                flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm
                ${isCurrent
                                    ? 'bg-white/20 text-white'
                                    : isCompleted
                                        ? 'bg-white/20 text-white'
                                        : 'bg-white/10 text-gray-400'
                                }
              `}>
                                {isCompleted ? '✓' : index + 1}
                            </div>

                            {/* Stage Info */}
                            <div className="flex flex-col">
                                {isCurrent && (
                                    <span className="text-[9px] font-bold uppercase tracking-widest text-white/60 mb-0.5">
                                        Current Stage
                                    </span>
                                )}
                                <span className={`
                  text-sm font-semibold whitespace-nowrap
                  ${isCurrent ? 'text-white' : isCompleted ? 'text-white/90' : 'text-gray-400'}
                `}>
                                    {stage.name}
                                </span>
                            </div>

                            {/* Pulse animation for current stage */}
                            {isCurrent && (
                                <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg opacity-30 blur-sm animate-pulse" />
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Project Title */}
            <div className="text-sm font-medium text-gray-400 max-w-[200px] truncate">
                {projectTitle}
            </div>
        </div>
    );
}
