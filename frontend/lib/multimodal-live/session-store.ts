export interface SessionData {
    sessionId: string;
    mobileNumber: string;
    timestamp: number;
    title?: string;
    currentStage: number;
}

const STORAGE_KEY = "maya_voice_sessions";

export const SessionStore = {
    getSessions: (mobileNumber?: string): SessionData[] => {
        if (typeof window === "undefined") return [];
        const stored = localStorage.getItem(STORAGE_KEY);
        if (!stored) return [];
        try {
            const allSessions: SessionData[] = JSON.parse(stored);
            if (mobileNumber) {
                return allSessions.filter(s => s.mobileNumber === mobileNumber);
            }
            return allSessions;
        } catch {
            return [];
        }
    },

    addSession: (data: Omit<SessionData, "timestamp">) => {
        if (typeof window === "undefined") return;
        const sessions = SessionStore.getSessions();
        const newSession: SessionData = {
            ...data,
            timestamp: Date.now()
        };
        // Keep unique sessions by sessionId
        const filtered = sessions.filter(s => s.sessionId !== data.sessionId);
        const updated = [newSession, ...filtered].slice(0, 10); // Keep last 10 total
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    },

    deleteSession: (mobileNumber: string, sessionId: string) => {
        if (typeof window === "undefined") return;
        const sessions = SessionStore.getSessions();
        const updated = sessions.filter(s => s.sessionId !== sessionId);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    },

    // Legacy support if needed
    removeSession: (id: string) => {
        if (typeof window === "undefined") return;
        const sessions = SessionStore.getSessions();
        const updated = sessions.filter(s => s.sessionId !== id);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    }
};
