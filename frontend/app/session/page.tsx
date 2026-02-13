"use client";

import MultimodalLiveApp from "@/multimodal-live/MultimodalLiveApp";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function VoiceAgentContent() {
    const searchParams = useSearchParams();

    // Get all parameters from query strings to support static export
    const mobileNumber = searchParams.get("mobile_number") || "";
    const sessionId = searchParams.get("session_id") || "";
    const name = searchParams.get("name") || "";
    const language = searchParams.get("lang") || "English";

    if (!mobileNumber || !sessionId) {
        return (
            <div style={{ padding: "20px", textAlign: "center", color: "white" }}>
                <h1>Invalid Session</h1>
                <p>Missing required session parameters.</p>
                <a href="/" style={{ color: "#0070f3", textDecoration: "underline" }}>Return Home</a>
            </div>
        );
    }

    return (
        <main className="App">
            <MultimodalLiveApp
                mobileNumber={mobileNumber}
                sessionId={sessionId}
                userName={name}
                userLanguage={language}
            />
        </main>
    );
}

export default function VoiceAgentPage() {
    return (
        <Suspense fallback={<div style={{ color: "white", textAlign: "center", padding: "50px" }}>Loading Session...</div>}>
            <VoiceAgentContent />
        </Suspense>
    );
}
