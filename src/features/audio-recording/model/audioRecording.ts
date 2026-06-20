import { mkdir } from "node:fs/promises";
import { join } from "node:path";

import { runCommand } from "@/shared/process";

export interface RecordingConfig {
  device: string;
  format: string;
  rate: string;
  channels: string;
}

export interface RecordingRequest {
  duration: number;
  outputFile: string;
  config: RecordingConfig;
}

export function defaultRecordingConfig(
  env: NodeJS.ProcessEnv = process.env,
): RecordingConfig {
  return {
    device: env.STT_RECORD_DEVICE ?? "default",
    format: env.STT_RECORD_FORMAT ?? "S16_LE",
    rate: env.STT_RECORD_RATE ?? "16000",
    channels: env.STT_RECORD_CHANNELS ?? "1",
  };
}

export function recordingFileName(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  const second = String(date.getSeconds()).padStart(2, "0");
  return `recording-${year}${month}${day}-${hour}${minute}${second}.wav`;
}

export function buildArecordArgs(request: RecordingRequest): string[] {
  return [
    "-D",
    request.config.device,
    "-f",
    request.config.format,
    "-r",
    request.config.rate,
    "-c",
    request.config.channels,
    "-d",
    String(request.duration),
    request.outputFile,
  ];
}

export function parsePositiveInteger(value: string, label: string): number {
  if (!/^[1-9][0-9]*$/u.test(value)) {
    throw new Error(`${label} must be a positive integer: ${value}`);
  }
  return Number(value);
}

export async function recordAudio(
  duration: number,
  outputDir: string,
  env: NodeJS.ProcessEnv = process.env,
): Promise<string> {
  await mkdir(outputDir, { recursive: true });
  const outputFile = join(outputDir, recordingFileName());
  const result = await runCommand(
    "arecord",
    buildArecordArgs({
      duration,
      outputFile,
      config: defaultRecordingConfig(env),
    }),
  );
  if (result.code !== 0) {
    throw new Error(
      result.stderr.trim() || `arecord failed with exit code ${result.code}`,
    );
  }
  return outputFile;
}
