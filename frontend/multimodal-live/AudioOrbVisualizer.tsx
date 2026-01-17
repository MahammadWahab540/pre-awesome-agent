import { useEffect, useRef } from 'react';
import '@/multimodal-live/audio-orb/visual-3d';

interface AudioOrbVisualizerProps {
    inputNode: AudioNode | undefined;
    outputNode: AudioNode | undefined;
}

export const AudioOrbVisualizer: React.FC<AudioOrbVisualizerProps> = ({ inputNode, outputNode }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const visualizerRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
        if (!containerRef.current) return;

        // Create the custom element if it doesn't exist
        if (!visualizerRef.current) {
            const visualizer = document.createElement('gdm-live-audio-visuals-3d');
            visualizer.style.width = '100%';
            visualizer.style.height = '100%';
            visualizer.style.position = 'absolute';
            visualizer.style.inset = '0';
            containerRef.current.appendChild(visualizer);
            visualizerRef.current = visualizer;
        }

        // Update properties
        const visualizer = visualizerRef.current as any;
        if (inputNode) {
            visualizer.inputNode = inputNode;
        }
        if (outputNode) {
            visualizer.outputNode = outputNode;
        }

        return () => {
            // Cleanup if needed, though we might want to keep it around if unmounting/remounting is frequent
            // For now, let's keep it simple and not remove it to avoid re-initialization cost if it's just a re-render
        };
    }, [inputNode, outputNode]);

    return (
        <div className="relative w-full h-full bg-[#0B0F17] overflow-hidden">
            <div ref={containerRef} className="absolute inset-0 w-full h-full" />
        </div>
    );
};
