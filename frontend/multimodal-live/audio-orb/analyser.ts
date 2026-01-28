export class AudioAnalyser {
    private analyser: AnalyserNode | null = null;
    private bufferLength: number = 0;
    private dataArray: Uint8Array<ArrayBufferLike> | null = null;

    constructor() {
        // Initialization is deferred to the connect method, or via setter injection
    }

    /**
     * Initializes the analyser with an AudioContext and SourceNode.
     * @param audioContext The AudioContext to use.
     * @param sourceNode The MediaStreamAudioSourceNode to connect to.
     */
    connect(audioContext: AudioContext, sourceNode: MediaStreamAudioSourceNode): void {
        this.analyser = audioContext.createAnalyser();
        this.analyser.fftSize = 2048; // Default FFT size
        this.bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(this.bufferLength);

        sourceNode.connect(this.analyser);
    }

    getByteFrequencyData(array: Uint8Array<ArrayBufferLike>): void {
        if (this.analyser) {
            // DOM API expects Uint8Array<ArrayBuffer>; ArrayBufferLike is safe to pass.
            this.analyser.getByteFrequencyData(array as Uint8Array<ArrayBuffer>);
        } else {
            // Fill with zeros if no analyser
            array.fill(0);
        }
    }

    disconnect(): void {
        if (this.analyser) {
            this.analyser.disconnect();
            this.analyser = null;
        }
    }
}
