"use client";

import MultimodalLiveApp from "@/multimodal-live/MultimodalLiveApp";
import { useParams } from "next/navigation";

export default function VoiceAgentPage() {
    const params = useParams();
    const mobileNumber = params.mobile_number as string;
    const sessionId = params.session_id as string;

    return (
        <main className="App">
            <MultimodalLiveApp
                mobileNumber={mobileNumber}
                sessionId={sessionId}
            />
        </main>
    );
}
