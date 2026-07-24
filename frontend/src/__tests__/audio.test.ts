import { describe, expect, it } from 'vitest';
import { downsampleToMono, encodeWav, pickRecorderMimeType } from '../utils/audio';

describe('audio utils', () => {
  it('pickRecorderMimeType returns string in jsdom', () => {
    expect(typeof pickRecorderMimeType()).toBe('string');
  });

  it('encodeWav produces wav header', async () => {
    const samples = new Float32Array([0, 0.5, -0.5, 1]);
    const blob = encodeWav(samples, 16000);
    expect(blob.type).toBe('audio/wav');
    const buf = await blob.arrayBuffer();
    const header = String.fromCharCode(...new Uint8Array(buf.slice(0, 4)));
    expect(header).toBe('RIFF');
  });

  it('downsampleToMono averages channels', () => {
    const length = 4;
    const buffer = {
      numberOfChannels: 2,
      sampleRate: 16000,
      length,
      getChannelData: (ch: number) => {
        const data = new Float32Array(length);
        data.fill(ch === 0 ? 1 : -1);
        return data;
      },
    } as unknown as AudioBuffer;

    const mono = downsampleToMono(buffer, 16000);
    expect(mono.length).toBe(4);
    expect([...mono]).toEqual([0, 0, 0, 0]);
  });
});
