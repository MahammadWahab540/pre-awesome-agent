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
import { MultimodalLiveClient, LiveSessionConfig } from "@/utils/multimodal-live/multimodal-live-client";
import { AudioStreamer } from "@/utils/multimodal-live/audio-streamer";
import { audioContext } from "@/utils/multimodal-live/utils";
import VolMeterWorket from "@/utils/multimodal-live/worklets/vol-meter";

export type UseLiveAPIResults = {
  client: MultimodalLiveClient;
  connected: boolean;
  wsReady: boolean;
  connect: (config?: LiveSessionConfig) => Promise<void>;
  disconnect: () => Promise<void>;
  volume: number;
  audioStreamerRef: React.MutableRefObject<AudioStreamer | null>;
};

export type UseLiveAPIProps = {
  url?: string;
  userId?: string;
  projectId?: string | null;
  onRunIdChange?: Dispatch<SetStateAction<string>>;
};

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

  const [connected, setConnected] = useState(false);
  const [wsReady, setWsReady] = useState(false);
  const [volume, setVolume] = useState(0);

  // register audio for streaming server -> speakers
  useEffect(() => {
    if (!audioStreamerRef.current) {
      audioContext({ id: "audio-out" }).then((audioCtx: AudioContext) => {
        audioStreamerRef.current = new AudioStreamer(audioCtx);
        audioStreamerRef.current
          .addWorklet<any>("vumeter-out", VolMeterWorket, (ev: any) => {
            setVolume(ev.data.volume);
          })
          .then(() => {
            // Successfully added worklet
          });
      });
    }
  }, [audioStreamerRef]);

  useEffect(() => {
    const onOpen = () => {
      setWsReady(true);
      console.log('✅ [WebSocket] Connection established - ready to initialize session');
    };

    const onClose = () => {
      setConnected(false);
      console.log('❌ [WebSocket] Connection closed');
    };

    const onSetupComplete = () => {
      setConnected(true);
      console.log('✅ [Session] Setup complete - session active');
    };

    const stopAudioStreamer = () => audioStreamerRef.current?.stop();

    const onAudio = (data: ArrayBuffer) =>
      audioStreamerRef.current?.addPCM16(new Uint8Array(data));

    client
      .on("open", onOpen)
      .on("close", onClose)
      .on("setupcomplete", onSetupComplete)
      .on("interrupted", stopAudioStreamer)
      .on("audio", onAudio);

    return () => {
      client
        .off("open", onOpen)
        .off("close", onClose)
        .off("setupcomplete", onSetupComplete)
        .off("interrupted", stopAudioStreamer)
        .off("audio", onAudio);
    };
  }, [client]);

  // Health check backend on mount (don't start session yet)
  useEffect(() => {
    let mounted = true;
    let retryTimeout: NodeJS.Timeout;

    const checkBackendHealth = async () => {
      try {
        console.log('🏥 [Health Check] Checking backend availability...');

        // Extract base URL from WebSocket URL
        const wsUrl = new URL(client.url);
        const httpUrl = `${wsUrl.protocol === 'wss:' ? 'https:' : 'http:'}//${wsUrl.host}/health`;

        // Check the health endpoint
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000); // 3s timeout (reduced for faster startup)

        const response = await fetch(httpUrl, {
          method: 'GET',
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (response.ok && mounted) {
          const data = await response.json();
          if (data.status === 'healthy') {
            setWsReady(true);
            console.log('✅ [Health Check] Backend is healthy and ready');
          } else {
            throw new Error('Backend returned unhealthy status');
          }
        }
      } catch (error) {
        if (mounted) {
          console.warn('⚠️ [Health Check] Backend not available, retrying in 2s...', error);
          setWsReady(false);
          // Retry after 2 seconds (reduced for faster startup)
          retryTimeout = setTimeout(checkBackendHealth, 2000);
        }
      }
    };

    checkBackendHealth();

    return () => {
      mounted = false;
      clearTimeout(retryTimeout);
    };
  }, [client.url]);

  const connect = useCallback(async (config?: LiveSessionConfig) => {
    console.log('🚀 [Session] Initializing session...', config);
    client.disconnect(); // Ensure clean state
    await client.connect(config);
    // Session starts when WebSocket connection is established
  }, [client]);

  const disconnect = useCallback(async () => {
    console.log('🛑 [Session] Disconnecting...');
    client.disconnect();
    setConnected(false);
    // Don't set wsReady to false - backend is still available
    // This allows immediate reconnection without showing "Connecting to Backend..."
  }, [client]);

  return {
    client,
    connected,
    wsReady,
    connect,
    disconnect,
    volume,
    audioStreamerRef,
  };
}
