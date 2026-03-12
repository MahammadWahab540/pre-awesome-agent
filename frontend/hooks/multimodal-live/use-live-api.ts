/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  Dispatch,
  SetStateAction,
} from "react";
import {
  MultimodalLiveClient,
  LiveSessionConfig,
  SessionErrorPayload,
} from "@/utils/multimodal-live/multimodal-live-client";
import { AudioStreamer } from "@/utils/multimodal-live/audio-streamer";
import { audioContext } from "@/utils/multimodal-live/utils";
import VolMeterWorket from "@/utils/multimodal-live/worklets/vol-meter";

/**
 * Turn state machine:
 *   IDLE       -> no active session
 *   LISTENING  -> user's turn (mic active, awaiting speech)
 *   PROCESSING -> user turn ended, waiting for agent response
 *   SPEAKING   -> agent audio is playing
 */
export type TurnState = "IDLE" | "LISTENING" | "PROCESSING" | "SPEAKING";

export type UseLiveAPIResults = {
  client: MultimodalLiveClient;
  connected: boolean;
  wsReady: boolean;
  connect: (config?: LiveSessionConfig) => Promise<void>;
  disconnect: () => Promise<void>;
  volume: number;
  turnState: TurnState;
  audioStreamerRef: React.MutableRefObject<AudioStreamer | null>;
};

export type UseLiveAPIProps = {
  url?: string;
  userId?: string;
  projectId?: string | null;
  onRunIdChange?: Dispatch<SetStateAction<string>>;
};

const HANDSHAKE_TIMEOUT_MS = 10000;
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;
// Reconnect only on unexpected server-side closures (OOM kill = 1006, server errors = 1011/1012/1013)
const RECONNECTABLE_CLOSE_CODES = new Set([1006, 1011, 1012, 1013]);

export function useLiveAPI({
  url,
  userId,
  projectId,
}: UseLiveAPIProps): UseLiveAPIResults {
  const client = useMemo(
    () => new MultimodalLiveClient({ url, userId, projectId }),
    [url, userId, projectId],
  );
  const audioStreamerRef = useRef<AudioStreamer | null>(null);
  const handshakeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isUserDisconnectRef = useRef<boolean>(false);
  const lastSessionConfigRef = useRef<LiveSessionConfig | undefined>(undefined);

  const [connected, setConnected] = useState(false);
  const [wsReady, setWsReady] = useState(false);
  const [volume, setVolume] = useState(0);
  const [turnState, setTurnState] = useState<TurnState>("IDLE");

  const clearHandshakeTimeout = useCallback(() => {
    if (handshakeTimeoutRef.current) {
      clearTimeout(handshakeTimeoutRef.current);
      handshakeTimeoutRef.current = null;
    }
  }, []);

  // Register audio for streaming server -> speakers.
  useEffect(() => {
    if (!audioStreamerRef.current) {
      audioContext({ id: "audio-out" }).then((audioCtx: AudioContext) => {
        audioStreamerRef.current = new AudioStreamer(audioCtx);
        audioStreamerRef.current
          .addWorklet<any>("vumeter-out", VolMeterWorket, (ev: any) => {
            setVolume(ev.data.volume);
          })
          .then(() => {
            // Successfully added worklet.
          });
      });
    }
  }, [audioStreamerRef]);

  useEffect(() => {
    const onOpen = () => {
      setWsReady(true);
    };

    const onClose = (ev: CloseEvent) => {
      clearHandshakeTimeout();
      setConnected(false);
      setTurnState("IDLE");

      // Auto-reconnect on unexpected server-side disconnects (e.g. OOM kill = code 1006)
      if (
        !isUserDisconnectRef.current &&
        RECONNECTABLE_CLOSE_CODES.has(ev.code) &&
        reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS
      ) {
        const attempt = reconnectAttemptsRef.current;
        reconnectAttemptsRef.current += 1;
        const delay = Math.min(
          BASE_RECONNECT_DELAY_MS * Math.pow(2, attempt),
          MAX_RECONNECT_DELAY_MS,
        );
        console.warn(
          `[LiveAPI] Unexpected disconnect (code=${ev.code}). Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`,
        );
        reconnectTimeoutRef.current = setTimeout(async () => {
          reconnectTimeoutRef.current = null;
          if (isUserDisconnectRef.current) return;
          handshakeTimeoutRef.current = setTimeout(() => {
            setConnected(false);
            setTurnState("IDLE");
            client.disconnect();
          }, HANDSHAKE_TIMEOUT_MS);
          try {
            await client.connect(lastSessionConfigRef.current);
          } catch {
            clearHandshakeTimeout();
          }
        }, delay);
      }
    };

    const onSetupComplete = () => {
      // Wait for explicit session confirmation before setting connected/processing state.
    };

    const onSessionConfirmed = () => {
      clearHandshakeTimeout();
      setConnected(true);
      // After session confirmation, agent may greet, so enter processing state.
      setTurnState("PROCESSING");
    };

    const onSessionError = (payload: SessionErrorPayload) => {
      clearHandshakeTimeout();
      console.error("[LiveAPI] Session initialization failed:", payload);
      setConnected(false);
      setTurnState("IDLE");
      client.disconnect();
    };

    const onSessionReset = () => {
      clearHandshakeTimeout();
      setConnected(false);
      setTurnState("IDLE");
      client.disconnect();
    };

    const stopAudioStreamer = () => {
      audioStreamerRef.current?.stop();
      // Interrupted = user barged in -> back to listening.
      setTurnState("LISTENING");
    };

    const onAudio = (data: ArrayBuffer) => {
      audioStreamerRef.current?.addPCM16(new Uint8Array(data));
      // First audio chunk -> agent is now speaking.
      setTurnState((prev) => (prev !== "SPEAKING" ? "SPEAKING" : prev));
    };

    const onTurnComplete = () => {
      audioStreamerRef.current?.complete();
      // Agent finished speaking -> user's turn.
      setTurnState("LISTENING");
    };

    const onInputTranscription = () => {
      // User speech detected by server VAD -> confirm listening state.
      setTurnState((prev) => (prev === "SPEAKING" ? "LISTENING" : prev));
    };

    const onOutputTranscription = () => {
      // Agent output detected -> confirm speaking state.
      setTurnState((prev) => (prev !== "SPEAKING" ? "SPEAKING" : prev));
    };

    client
      .on("open", onOpen)
      .on("close", onClose)
      .on("setupcomplete", onSetupComplete)
      .on("sessionconfirmed", onSessionConfirmed)
      .on("sessionerror", onSessionError)
      .on("sessionreset", onSessionReset)
      .on("interrupted", stopAudioStreamer)
      .on("turncomplete", onTurnComplete)
      .on("audio", onAudio)
      .on("inputtranscription", onInputTranscription)
      .on("outputtranscription", onOutputTranscription);

    return () => {
      client
        .off("open", onOpen)
        .off("close", onClose)
        .off("setupcomplete", onSetupComplete)
        .off("sessionconfirmed", onSessionConfirmed)
        .off("sessionerror", onSessionError)
        .off("sessionreset", onSessionReset)
        .off("interrupted", stopAudioStreamer)
        .off("turncomplete", onTurnComplete)
        .off("audio", onAudio)
        .off("inputtranscription", onInputTranscription)
        .off("outputtranscription", onOutputTranscription);
    };
  }, [client, clearHandshakeTimeout]);

  useEffect(() => {
    return () => {
      clearHandshakeTimeout();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [clearHandshakeTimeout]);

  // Health check backend on mount (don't start session yet).
  useEffect(() => {
    let mounted = true;
    let retryTimeout: ReturnType<typeof setTimeout> | undefined;
    let requestTimeout: ReturnType<typeof setTimeout> | undefined;
    let inFlightController: AbortController | null = null;
    let timeoutMs = 6000;
    const RETRY_DELAY_MS = 750;
    const MAX_TIMEOUT_MS = 12000;
    const TIMEOUT_BACKOFF_FACTOR = 1.5;

    const getHealthUrl = () => {
      const wsUrl = new URL(client.url);
      return `${wsUrl.protocol === "wss:" ? "https:" : "http:"}//${wsUrl.host}/health`;
    };

    const checkBackendHealth = async () => {
      if (!mounted) {
        return;
      }

      const requestTimeoutMs = timeoutMs;
      inFlightController = new AbortController();

      try {
        requestTimeout = setTimeout(
          () => inFlightController?.abort(),
          requestTimeoutMs,
        );

        const response = await fetch(getHealthUrl(), {
          method: "GET",
          cache: "no-store",
          signal: inFlightController.signal,
        });

        if (!response.ok) {
          throw new Error(`Health check failed with status ${response.status}`);
        }

        const data = await response
          .json()
          .catch(() => ({} as Record<string, unknown>));
        const status =
          typeof data.status === "string" ? data.status.toLowerCase() : "healthy";
        if (status !== "healthy") {
          throw new Error(`Backend returned unhealthy status: ${status}`);
        }

        if (!mounted) {
          return;
        }

        setWsReady(true);
      } catch (error) {
        if (mounted) {
          setWsReady(false);

          const isAbortError =
            error instanceof DOMException && error.name === "AbortError";

          if (isAbortError) {
            console.warn(
              `[Health Check] Request timed out after ${requestTimeoutMs}ms, retrying in ${RETRY_DELAY_MS}ms...`,
            );
          } else {
            console.warn(
              `[Health Check] Backend not available, retrying in ${RETRY_DELAY_MS}ms...`,
              error,
            );
          }

          timeoutMs = Math.min(
            Math.round(timeoutMs * TIMEOUT_BACKOFF_FACTOR),
            MAX_TIMEOUT_MS,
          );
          retryTimeout = setTimeout(checkBackendHealth, RETRY_DELAY_MS);
        }
      } finally {
        if (requestTimeout) {
          clearTimeout(requestTimeout);
          requestTimeout = undefined;
        }
      }
    };

    checkBackendHealth();

    return () => {
      mounted = false;
      if (retryTimeout) {
        clearTimeout(retryTimeout);
      }
      if (requestTimeout) {
        clearTimeout(requestTimeout);
      }
      inFlightController?.abort();
    };
  }, [client.url]);

  const connect = useCallback(
    async (config?: LiveSessionConfig) => {
      clearHandshakeTimeout();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      reconnectAttemptsRef.current = 0;
      isUserDisconnectRef.current = false;
      lastSessionConfigRef.current = config;
      client.disconnect(); // Ensure clean state.
      setConnected(false);
      setTurnState("IDLE");

      handshakeTimeoutRef.current = setTimeout(() => {
        console.error(
          `[LiveAPI] Session confirmation timeout after ${HANDSHAKE_TIMEOUT_MS}ms`,
        );
        setConnected(false);
        setTurnState("IDLE");
        client.disconnect();
      }, HANDSHAKE_TIMEOUT_MS);

      try {
        await client.connect(config);
      } catch (error) {
        clearHandshakeTimeout();
        setConnected(false);
        setTurnState("IDLE");
        throw error;
      }
    },
    [client, clearHandshakeTimeout],
  );

  const disconnect = useCallback(async () => {
    isUserDisconnectRef.current = true;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttemptsRef.current = 0;
    clearHandshakeTimeout();
    client.disconnect();
    setConnected(false);
    setTurnState("IDLE");
  }, [client, clearHandshakeTimeout]);

  return {
    client,
    connected,
    wsReady,
    connect,
    disconnect,
    volume,
    turnState,
    audioStreamerRef,
  };
}
