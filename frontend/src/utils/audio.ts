/** 浏览器录音与 WAV 编码工具（移植自语音问答项目） */

export function pickRecorderMimeType(): string {
  if (typeof MediaRecorder === 'undefined') return '';
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
  ];
  for (const type of candidates) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return '';
}

function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
}

export function downsampleToMono(audioBuffer: AudioBuffer, targetRate: number): Float32Array {
  const numChannels = audioBuffer.numberOfChannels;
  const srcRate = audioBuffer.sampleRate;
  const length = audioBuffer.length;
  const mono = new Float32Array(length);
  for (let ch = 0; ch < numChannels; ch++) {
    const data = audioBuffer.getChannelData(ch);
    for (let i = 0; i < length; i++) mono[i] += data[i] / numChannels;
  }
  if (srcRate === targetRate) return mono;
  const ratio = srcRate / targetRate;
  const newLen = Math.max(1, Math.round(mono.length / ratio));
  const result = new Float32Array(newLen);
  for (let i = 0; i < newLen; i++) {
    const idx = Math.min(mono.length - 1, Math.floor(i * ratio));
    result[i] = mono[idx];
  }
  return result;
}

export function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buffer], { type: 'audio/wav' });
}

export async function blobToWav16k(blob: Blob): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer();
  const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
  const audioCtx = new AudioCtx();
  try {
    const decoded = await audioCtx.decodeAudioData(arrayBuffer.slice(0));
    const samples = downsampleToMono(decoded, 16000);
    return encodeWav(samples, 16000);
  } finally {
    await audioCtx.close();
  }
}
