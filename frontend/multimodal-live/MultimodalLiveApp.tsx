"use client";

import React, { useCallback, useEffect, useState, useMemo } from "react";
import { useLiveAPI } from "@/hooks/multimodal-live/use-live-api";
import { AudioRecorder } from "@/utils/multimodal-live/audio-recorder";
import {
    getBackendHttpBaseUrl,
    resolveBackendWebSocketUrl,
} from "@/utils/multimodal-live/backend-routing";
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
    userName?: string;
    userLanguage?: string;
}

interface Message {
    id: string;
    role: "user" | "model";
    text: string;
    timestamp: number;
}

export default function MultimodalLiveApp({ mobileNumber, sessionId, userName, userLanguage }: MultimodalLiveAppProps) {
    const backendWsUrl = useMemo(
        () => resolveBackendWebSocketUrl(process.env.NEXT_PUBLIC_MY_AWESOME_AGENT_URL),
        []
    );
    const { client, connected, connect, disconnect, volume, wsReady, turnState, audioStreamerRef } = useLiveAPI({
        url: backendWsUrl,
        userId: mobileNumber,
        projectId: sessionId
    });

    const [isMuted, setIsMuted] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [currentStage, setCurrentStage] = useState(0);
    const [showGuidelines, setShowGuidelines] = useState(true);
    const [stages, setStages] = useState<any[]>([]);
    const [sessionError, setSessionError] = useState<string | null>(null);
    const [sessionCompleteNotice, setSessionCompleteNotice] = useState<string | null>(null);

    // Fetch stages config
    useEffect(() => {
        const fetchConfig = async () => {
            try {
                const baseUrl = getBackendHttpBaseUrl(backendWsUrl);
                const response = await fetch(`${baseUrl}/config/stages`);
                const data = await response.json();
                setStages(data);
            } catch (error) {
                console.error("Failed to fetch stages config:", error);
            }
        };
        fetchConfig();
    }, [backendWsUrl]);

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

    useEffect(() => {
        const onSessionReset = () => {
            setSessionCompleteNotice(null);
            setSessionError("Your session was reset. Please wait while we reconnect...");
        };

        const onSessionError = (payload: any) => {
            const isSetupError = payload?.code === "setup_timeout" || payload?.code === "invalid_setup";
            if (isSetupError) {
                // Can't establish session at all — go back to login.
                window.location.href = "/";
            } else {
                // Mid-session error — show message, let auto-reconnect handle it.
                setSessionCompleteNotice(null);
                setSessionError("Connection interrupted. Reconnecting...");
            }
        };

        const onSessionComplete = () => {
            setSessionError(null);
            setSessionCompleteNotice(
                "This conversation has ended. You can review the transcript or tap End Call when you're ready.",
            );
        };

        (client as any)
            .on("sessionreset", onSessionReset)
            .on("sessionerror", onSessionError)
            .on("sessioncomplete", onSessionComplete);

        return () => {
            (client as any)
                .off("sessionreset", onSessionReset)
                .off("sessionerror", onSessionError)
                .off("sessioncomplete", onSessionComplete);
        };
    }, [client]);

    // Clear error banner once successfully reconnected.
    useEffect(() => {
        if (connected && sessionError) {
            setSessionError(null);
        }
        if (connected && sessionCompleteNotice) {
            setSessionCompleteNotice(null);
        }
    }, [connected, sessionError, sessionCompleteNotice]);

    // Manage Audio Recording
    useEffect(() => {
        const handleAudioData = (base64Data: string) => {
            client.sendRealtimeInput([{
                mimeType: "audio/pcm;rate=16000",
                data: base64Data
            }]);
        };

        if (connected && !isMuted) {
            audioRecorder.on("data", handleAudioData);
            audioRecorder.start();
        } else {
            audioRecorder.stop();
            audioRecorder.off("data", handleAudioData);
        }

        return () => {
            audioRecorder.off("data", handleAudioData);
            audioRecorder.stop();
        };
    }, [connected, isMuted, audioRecorder, client]);

    const handleStartSession = async () => {
        try {
            setShowGuidelines(false);
            setSessionError(null);
            setSessionCompleteNotice(null);
            // Explicitly resume audio context on user interaction to satisfy browser policy
            await audioStreamerRef.current?.resume();
            await connect({
                user_name: userName,
                user_language: userLanguage
            });
        } catch (error) {
            console.error("Failed to start session:", error);
            window.location.href = "/";
        }
    };

    const handleEndCall = async () => {
        await disconnect();
        window.location.href = "/";
    };

    return (
        <div className="h-screen bg-white flex flex-col relative overflow-hidden font-sans">
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

            {sessionError && (
                <div className="flex items-center justify-center gap-2 bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-800">
                    <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                    {sessionError}
                </div>
            )}

            {sessionCompleteNotice && (
                <div className="flex items-center justify-center gap-2 bg-emerald-50 border-b border-emerald-200 px-4 py-2 text-sm text-emerald-800">
                    <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
                    {sessionCompleteNotice}
                </div>
            )}

            <main className="flex-1 flex flex-col md:flex-row overflow-hidden">
                {/* Column 1: Progress (Left) */}
                <aside className="w-full md:w-80 border-r border-white/40 bg-white/5 backdrop-blur-sm hidden lg:block overflow-y-auto px-6 py-4">
                    <ProgressTracker currentStage={currentStage} stages={stages} />
                </aside>

                {/* Column 2: Visualizer (Center) */}
                <section className="flex-1 flex flex-col items-center justify-center p-6 relative text-center">
                    <MayaOrbVisualizer
                        isListening={turnState === "LISTENING"}
                        isSpeaking={turnState === "SPEAKING"}
                        isProcessing={turnState === "PROCESSING"}
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
