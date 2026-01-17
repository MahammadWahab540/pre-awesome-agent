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

import { memo, useRef } from "react";
import cn from "classnames";
import { UseMediaStreamResult } from "@/hooks/multimodal-live/use-media-stream-mux";
import AudioPulse from "../audio-pulse/AudioPulse";
import "./control-bar.scss";

export type ControlBarProps = {
    connected: boolean;
    wsReady: boolean;
    onConnect: () => void;
    onDisconnect: () => void;
    muted: boolean;
    onMuteChange: (muted: boolean) => void;
    volume: number;
    videoStreams: UseMediaStreamResult[];
    activeVideoStream: MediaStream | null;
    onVideoStreamChange: (stream: MediaStream | null) => void;
    textInput: string;
    onTextInputChange: (text: string) => void;
    onSubmit: () => void;
    supportsVideo?: boolean;
};

type MediaStreamButtonProps = {
    isStreaming: boolean;
    onIcon: string;
    offIcon: string;
    start: () => Promise<any>;
    stop: () => any;
};

const MediaStreamButton = memo(
    ({ isStreaming, onIcon, offIcon, start, stop }: MediaStreamButtonProps) =>
        isStreaming ? (
            <button className={cn("action-button", { active: isStreaming })} onClick={stop}>
                <span className="material-symbols-outlined">{onIcon}</span>
            </button>
        ) : (
            <button className="action-button" onClick={start}>
                <span className="material-symbols-outlined">{offIcon}</span>
            </button>
        ),
);

function ControlBar({
    connected,
    wsReady,
    onConnect,
    onDisconnect,
    muted,
    onMuteChange,
    volume,
    videoStreams,
    activeVideoStream,
    onVideoStreamChange,
    textInput,
    onTextInputChange,
    onSubmit,
    supportsVideo = true,
}: ControlBarProps) {
    const [webcam, screenCapture] = videoStreams;
    const inputRef = useRef<HTMLTextAreaElement>(null);

    const changeStreams = (next?: UseMediaStreamResult) => async () => {
        if (next) {
            const mediaStream = await next.start();
            if (mediaStream) {
                onVideoStreamChange(mediaStream);
            } else {
                onVideoStreamChange(null);
            }
        } else {
            onVideoStreamChange(null);
        }

        videoStreams.filter((msr) => msr !== next).forEach((msr) => msr.stop());
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            e.stopPropagation();
            onSubmit();
        }
    };

    return (
        <div className="control-bar">
            <div className="controls-container">
                {/* Top Row: Connection Button + Media Controls */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', width: '100%', justifyContent: 'center' }}>
                    {/* Primary Connection Button with Clear CTA */}
                    {/* Primary Connection Toggle Button */}
                    <button
                        className={cn("action-button", { connected: connected })}
                        onClick={connected ? onDisconnect : onConnect}
                        disabled={!wsReady && !connected}
                        style={{
                            background: connected
                                ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
                                : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        }}
                    >
                        {connected ? (
                            <span className="material-symbols-outlined filled">stop</span>
                        ) : !wsReady ? (
                            <span className="material-symbols-outlined filled animate-spin">progress_activity</span>
                        ) : (
                            <span className="material-symbols-outlined filled">play_arrow</span>
                        )}
                    </button>

                    {/* Connection & Media Controls */}
                    <div className="media-controls">
                        <button
                            className={cn("action-button mic-button", { active: !muted })}
                            onClick={() => onMuteChange(!muted)}
                            disabled={!connected}
                        >
                            {!muted ? (
                                <span className="material-symbols-outlined filled">mic</span>
                            ) : (
                                <span className="material-symbols-outlined filled">mic_off</span>
                            )}
                        </button>

                        <div className="action-button no-action outlined">
                            <AudioPulse volume={volume} active={connected} hover={false} />
                        </div>

                        {supportsVideo && (
                            <>
                                <MediaStreamButton
                                    isStreaming={screenCapture.isStreaming}
                                    start={changeStreams(screenCapture)}
                                    stop={changeStreams()}
                                    onIcon="cancel_presentation"
                                    offIcon="present_to_all"
                                />
                                <MediaStreamButton
                                    isStreaming={webcam.isStreaming}
                                    start={changeStreams(webcam)}
                                    stop={changeStreams()}
                                    onIcon="videocam_off"
                                    offIcon="videocam"
                                />
                            </>
                        )}
                    </div>
                </div>

                {/* Text Input - Full Width Below */}
                <div className={cn("input-container", { disabled: !connected })}>
                    <textarea
                        className="input-area"
                        ref={inputRef}
                        onKeyDown={handleKeyDown}
                        onChange={(e) => onTextInputChange(e.target.value)}
                        value={textInput}
                        placeholder={connected ? "Type something..." : "Connect to start chatting..."}
                    />
                    <button
                        className="send-button material-symbols-outlined filled"
                        onClick={onSubmit}
                        disabled={!connected}
                    >
                        send
                    </button>
                </div>
            </div>
        </div>
    );
}

export default memo(ControlBar);
