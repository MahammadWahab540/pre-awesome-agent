import React from 'react';

export function BRDViewer({ content, isGenerating }: any) {
    return (
        <div className="p-8">
            <h2 className="text-xl mb-4">BRD Viewer</h2>
            <div className="bg-gray-900/50 p-4 rounded border border-white/10 whitespace-pre-wrap">
                {isGenerating ? "Generating BRD..." : content || "No BRD content yet."}
            </div>
        </div>
    );
}
