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

const AudioRecordingWorklet = `
class AudioProcessingWorklet extends AudioWorkletProcessor {

  constructor(options) {
    super();
    this.targetSampleRate = Number(
      options?.processorOptions?.targetSampleRate || 16000
    );
    this.inputSampleRate = sampleRate;
    this.downsampleRatio = this.inputSampleRate / this.targetSampleRate;
    this.resampleCursor = 0;
    // Send and clear buffer every 2048 output samples. At 16 kHz this is
    // roughly 8 chunks per second.
    this.buffer = new Int16Array(2048);
    this.bufferWriteIndex = 0;
  }

  /**
   * @param inputs Float32Array[][] [input#][channel#][sample#] so to access first inputs 1st channel inputs[0][0]
   * @param outputs Float32Array[][]
   */
  process(inputs) {
    if (inputs[0].length) {
      const channel0 = inputs[0][0];
      if (channel0 && channel0.length) {
        this.processChunk(channel0);
      }
    }
    return true;
  }

  sendAndClearBuffer(){
    this.port.postMessage({
      event: "chunk",
      data: {
        int16arrayBuffer: this.buffer.slice(0, this.bufferWriteIndex).buffer,
      },
    });
    this.bufferWriteIndex = 0;
  }

  processChunk(float32Array) {
    if (this.inputSampleRate === this.targetSampleRate) {
      for (let i = 0; i < float32Array.length; i++) {
        this.writeSample(float32Array[i]);
      }
      return;
    }

    let cursor = this.resampleCursor;
    while (cursor < float32Array.length) {
      this.writeSample(float32Array[Math.floor(cursor)]);
      cursor += this.downsampleRatio;
    }
    this.resampleCursor = cursor - float32Array.length;
  }

  writeSample(sample) {
    const finiteSample = Number.isFinite(sample) ? sample : 0;
    const clamped = Math.max(-1, Math.min(1, finiteSample));
    // Convert float32 [-1, 1] to signed 16-bit PCM.
    const int16Value = clamped < 0 ? clamped * 32768 : clamped * 32767;
    this.buffer[this.bufferWriteIndex++] = int16Value;
    if (this.bufferWriteIndex >= this.buffer.length) {
      this.sendAndClearBuffer();
    }
  }
}
`;

export default AudioRecordingWorklet;
