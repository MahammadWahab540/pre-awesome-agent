"use client";

import MultimodalLiveApp from "@/multimodal-live/MultimodalLiveApp";
import { useParams, useSearchParams } from "next/navigation";

export default function VoiceAgentPage() {
    const params = useParams();
    const searchParams = useSearchParams();
    const mobileNumber = params.mobile_number as string;
    const sessionId = params.session_id as string;
    const name = searchParams.get("name") || "";
    const language = searchParams.get("lang") || "English";

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
