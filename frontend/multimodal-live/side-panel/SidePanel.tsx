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

import cn from "classnames";
import { memo, useState } from "react";
import { RiSidebarFoldLine, RiSidebarUnfoldLine } from "react-icons/ri";
import { useLiveAPIContext } from "@/contexts/multimodal-live/LiveAPIContext";
import BRDProgress from "../brd-progress/BRDProgress";
import TranscriptionPreview from "../transcription-preview/TranscriptionPreview";
import "./side-panel.scss";

export type SidePanelProps = {
  // No props needed for now as it uses context
};

function SidePanel() {
  const { client } = useLiveAPIContext();
  const [open, setOpen] = useState(false);
  // BRD Progress state
  const [currentStage, setCurrentStage] = useState(0);
  const [completedStages, setCompletedStages] = useState<boolean[]>(new Array(7).fill(false));

  // Listen for stage updates from WebSocket events (using content event)
  // ... (Keep existing stage update logic) ...

  return (
    <div className={`console-container ${open ? "open" : ""}`}>
      {/* Header */}
      <div className="console-header">
        <h2>Live Transcription</h2>
        <button className="toggle-button" onClick={() => setOpen(!open)}>
          {open ? <RiSidebarFoldLine color="#b4b8bb" /> : <RiSidebarUnfoldLine color="#b4b8bb" />}
        </button>
      </div>

      {/* Floating hint when closed */}
      {!open && (
        <div className="transcript-hint">
          <div className="hint-content">
            <svg className="hint-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            <span className="hint-text">Click to view transcript</span>
          </div>
        </div>
      )}

      {/* Transcription Content - Always rendered to track transcriptions, but hidden when closed */}
      <div style={{ 
        flex: 1, 
        minHeight: 0, 
        overflow: 'hidden', 
        display: open ? 'flex' : 'none',
        flexDirection: 'column' 
      }}>
        <TranscriptionPreview open={open} />
      </div>
    </div>
  );
}

export default memo(SidePanel);