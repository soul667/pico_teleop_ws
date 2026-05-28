class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 4096;
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input && input.length > 0) {
      const channelData = input[0];
      
      for (let i = 0; i < channelData.length; i++) {
        this.buffer[this.bufferIndex] = channelData[i];
        this.bufferIndex++;

        if (this.bufferIndex >= this.bufferSize) {
          // Convert to Int16
          const pcmData = new Int16Array(this.bufferSize);
          for (let j = 0; j < this.bufferSize; j++) {
            const s = Math.max(-1, Math.min(1, this.buffer[j]));
            pcmData[j] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          
          this.port.postMessage(pcmData);
          this.bufferIndex = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);
