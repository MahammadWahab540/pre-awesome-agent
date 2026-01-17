import React from 'react';

export function LiveBlueprintVisualization({ currentStage, completedStages, projectTitle, visualizationCode, versions }: any) {
    return (
        <div className="p-8">
            <h2 className="text-xl mb-4">Live Blueprint Visualization</h2>
            <div className="bg-gray-900/50 p-4 rounded border border-white/10 min-h-[300px]">
                {visualizationCode ? (
                    <div dangerouslySetInnerHTML={{ __html: visualizationCode }} />
                ) : (
                    <p className="text-gray-500">Waiting for visualization...</p>
                )}
            </div>
        </div>
    );
}
