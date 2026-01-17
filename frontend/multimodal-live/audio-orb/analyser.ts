export class AudioAnalyser {
    private analyser: AnalyserNode | null = null;
    private bufferLength: number = 0;
    private dataArray: Uint8Array<ArrayBufferLike> | null = null;

    constructor() {
        if (typeof window !== "undefined") {
            // Basic dummy initialization
        }
    }

    getByteFrequencyData(array: Uint8Array<ArrayBufferLike>): void {
        if (this.analyser) {
            // DOM API expects Uint8Array<ArrayBuffer>; ArrayBufferLike is safe to pass.
            this.analyser.getByteFrequencyData(array as Uint8Array);
        } else {
            // Fill with zeros if no analyser
            array.fill(0);
        }
    }
}
