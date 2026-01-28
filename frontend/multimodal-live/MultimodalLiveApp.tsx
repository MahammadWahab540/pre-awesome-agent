"use client";

import React, { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { useLiveAPI } from "@/hooks/multimodal-live/use-live-api";
import { AudioRecorder } from "@/utils/multimodal-live/audio-recorder";
import { MayaHeader } from "./components/MayaHeader";
import { MayaControls } from "./components/MayaControls";
import { ProgressTracker } from "./components/ProgressTracker";
import { MayaOrbVisualizer } from "./components/MayaOrbVisualizer";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldCheck } from "lucide-react";

interface MultimodalLiveAppProps {
    mobileNumber: string;
    sessionId: string;
}

interface Message {
    id: string;
    role: "user" | "model";
    text: string;
    timestamp: number;
}

export default function MultimodalLiveApp({ mobileNumber, sessionId }: MultimodalLiveAppProps) {
    const { client, connected, connect, disconnect, volume, wsReady } = useLiveAPI({
        url: (process.env as any).NEXT_PUBLIC_MY_AWESOME_AGENT_URL || "ws://localhost:8000/ws",
        userId: mobileNumber,
        projectId: sessionId
    });

    const [isMuted, setIsMuted] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [currentStage, setCurrentStage] = useState(0);
    const [showGuidelines, setShowGuidelines] = useState(true);
    const [isListening, setIsListening] = useState(false);

    const audioRecorder = useMemo(() => new AudioRecorder(), []);

    const appendMessage = useCallback((role: Message["role"], text: string, idBase: string) => {
        const trimmed = text.trim();
        if (!trimmed) {
            return;
        }
        setMessages((prev: Message[]) => [
            ...prev,
            {
                id: `${idBase}-${Date.now()}`,
                role,
                text: trimmed,
                timestamp: Date.now()
            }
        ]);
    }, [setMessages]);

    const getTranscriptionText = useCallback((value: any) => {
        if (!value) {
            return undefined;
        }
        if (typeof value === "string") {
            return value;
        }
        return value.text;
    }, []);

    // Handle Transcript and Stage Updates
    useEffect(() => {
        const onAdkEvent = (event: any) => {
            const payload = event?.adkevent || event?.adkEvent || event?.adk_event || event;
            // Update Transcript
            const inputText = getTranscriptionText(
                payload?.input_transcription || payload?.inputTranscription
            );
            if (inputText) {
                appendMessage("user", inputText, `${payload?.id || "input"}-input`);
            }
            const modelText = getTranscriptionText(
                payload?.model_transcription ||
                payload?.modelTranscription ||
                payload?.output_transcription ||
                payload?.outputTranscription
            );
            if (modelText) {
                appendMessage("model", modelText, `${payload?.id || "model"}-model`);
            }

            // Update Stage
            if (payload?.actions?.state_delta?.current_stage_index !== undefined) {
                setCurrentStage(payload.actions.state_delta.current_stage_index);
            }
        };

        const onContent = (content: any) => {
            if (content?.origin === "adk") {
                return;
            }
            const parts = content?.modelTurn?.parts || content?.model_turn?.parts || [];
            const text = parts
                .map((part: any) => part?.text)
                .filter(Boolean)
                .join("");
            if (text) {
                appendMessage("model", text, "modelturn");
            }
        };

        (client as any).on("adkevent", onAdkEvent).on("content", onContent);
        return () => {
            (client as any).off("adkevent", onAdkEvent).off("content", onContent);
        };
    }, [client, appendMessage, getTranscriptionText]);

    // Manage Audio Recording
    useEffect(() => {
        if (connected && !isMuted) {
            audioRecorder.on("data", (base64Data: string) => {
                client.sendRealtimeInput([{
                    mimeType: "audio/pcm;rate=16000",
                    data: base64Data
                }]);
            });
            audioRecorder.start();
            setIsListening(true);
        } else {
            audioRecorder.stop();
            audioRecorder.removeAllListeners("data");
            setIsListening(false);
        }
    }, [connected, isMuted, audioRecorder, client]);

    const handleStartSession = async () => {
        setShowGuidelines(false);
        await connect();
    };

    const handleEndCall = async () => {
        await disconnect();
        window.location.href = "/";
    };

    return (
        <div className="min-h-screen bg-white flex flex-col relative overflow-hidden font-sans">
            {/* Ambient Background */}
            <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none bg-white">
                <div className="absolute -top-[10%] -right-[10%] w-[70vw] h-[70vw] bg-brand-sky rounded-full blur-[120px] opacity-50 animate-float-slow" />
                <div className="absolute -bottom-[10%] -left-[10%] w-[50vw] h-[50vw] bg-brand-lavender rounded-full blur-[120px] opacity-50 animate-float-slow" style={{ animationDelay: '2s' }} />
            </div>

            <MayaHeader
                isConnected={connected}
                isOffline={!wsReady && connected}
                mobileNumber={mobileNumber}
            />

            <main className="flex-1 flex flex-col md:flex-row overflow-hidden">
                {/* Column 1: Progress (Left) */}
                <aside className="w-full md:w-80 border-r border-white/40 bg-white/5 backdrop-blur-sm hidden lg:block overflow-y-auto px-6 py-4">
                    <ProgressTracker currentStage={currentStage} />
                </aside>

                {/* Column 2: Visualizer (Center) */}
                <section className="flex-1 flex flex-col items-center justify-center p-6 relative text-center">
                    <MayaOrbVisualizer
                        isListening={isListening}
                        isSpeaking={volume > 0.05}
                        volume={volume}
                    />
                </section>

                {/* Column 3: Transcript (Right) */}
                <aside className="w-full md:w-[400px] border-l border-white/40 bg-white/5 backdrop-blur-sm overflow-hidden flex flex-col">
                    <TranscriptPanel messages={messages} />
                </aside>
            </main>

            <MayaControls
                isMuted={isMuted}
                onToggleMute={() => setIsMuted(!isMuted)}
                onEndCall={handleEndCall}
            />

            {/* Guidelines Modal */}
            <AnimatePresence>
                {showGuidelines && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/20 backdrop-blur-sm"
                    >
                        <motion.div
                            initial={{ scale: 0.9, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            className="bg-white/90 backdrop-blur-2xl border border-white/60 p-10 rounded-[40px] max-w-lg w-full shadow-[0_48px_96px_-12px_rgba(0,0,0,0.2)]"
                        >
                            <div className="flex flex-col items-center text-center space-y-6">
                                <div className="w-20 h-20 bg-brand-sky rounded-3xl flex items-center justify-center shadow-inner">
                                    <ShieldCheck size={40} className="text-brand-royal" />
                                </div>
                                <div className="space-y-2">
                                    <h3 className="text-2xl font-semibold text-gray-900">Before we begin</h3>
                                    <p className="text-gray-500 text-sm leading-relaxed">
                                        For the best experience with Maya, please ensure you are in a quiet environment and ready for a voice conversation.
                                    </p>
                                </div>

                                <div className="w-full space-y-3 pt-4">
                                    <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-2xl text-left">
                                        <div className="mt-1 w-2 h-2 rounded-full bg-brand-royal" />
                                        <p className="text-xs font-medium text-gray-700">Maya will guide you through each step of the registration.</p>
                                    </div>
                                    <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-2xl text-left">
                                        <div className="mt-1 w-2 h-2 rounded-full bg-brand-royal" />
                                        <p className="text-xs font-medium text-gray-700">You can mute or end the session at any time using the controls below.</p>
                                    </div>
                                </div>

                                <button
                                    onClick={handleStartSession}
                                    disabled={!wsReady}
                                    className={`w-full py-4 text-white rounded-2xl font-bold transition-all shadow-xl active:scale-[0.98] ${wsReady
                                            ? "bg-gray-900 hover:bg-black"
                                            : "bg-gray-400 cursor-not-allowed"
                                        }`}
                                >
                                    {wsReady ? "I'm Ready" : "Connecting to Server..."}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
