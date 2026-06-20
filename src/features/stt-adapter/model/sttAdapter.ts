import { existsSync } from "node:fs";
import { join } from "node:path";

import { runCommand } from "@/shared/process";
import { repoRoot } from "@/shared/repo";

export interface TranscribeOptions {
  model: string;
  language: string;
  device: "auto" | "cpu" | "cuda";
  computeType: string;
  beamSize: number;
  initialPrompt?: string;
  modelDir?: string;
  output?: string;
  vadFilter: boolean;
}

export const DEFAULT_TRANSCRIBE_OPTIONS: TranscribeOptions = {
  model: "large-v3",
  language: "ko",
  device: "auto",
  computeType: "auto",
  beamSize: 5,
  vadFilter: true,
};

export function buildTranscribeArgs(
  audioFile: string,
  options: TranscribeOptions,
): string[] {
  const args = [
    join(repoRoot, "scripts/transcribe.py"),
    audioFile,
    "--model",
    options.model,
    "--language",
    options.language,
    "--device",
    options.device,
    "--compute-type",
    options.computeType,
    "--beam-size",
    String(options.beamSize),
  ];
  if (options.initialPrompt) {
    args.push("--initial-prompt", options.initialPrompt);
  }
  if (options.modelDir) {
    args.push("--model-dir", options.modelDir);
  }
  if (options.output) {
    args.push("--output", options.output);
  }
  if (!options.vadFilter) {
    args.push("--no-vad-filter");
  }
  return args;
}

export function pythonVenvPath(): string {
  return join(repoRoot, ".venv/bin/python");
}

export function transcribeEnvironment(
  env: NodeJS.ProcessEnv = process.env,
): NodeJS.ProcessEnv {
  const sitePackages = join(repoRoot, ".venv/lib/python3.12/site-packages");
  const cudaLibDirs = [
    join(sitePackages, "nvidia/cublas/lib"),
    join(sitePackages, "nvidia/cudnn/lib"),
  ].filter((path) => existsSync(path));
  const ldLibraryPath = [
    ...cudaLibDirs,
    ...(env.LD_LIBRARY_PATH ? [env.LD_LIBRARY_PATH] : []),
  ].join(":");

  return {
    ...env,
    ...(ldLibraryPath ? { LD_LIBRARY_PATH: ldLibraryPath } : {}),
  };
}

export async function transcribeAudio(
  audioFile: string,
  options: TranscribeOptions,
): Promise<string> {
  const python = pythonVenvPath();
  if (!existsSync(python)) {
    throw new Error(
      "Python venv not found. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
    );
  }
  const result = await runCommand(
    python,
    buildTranscribeArgs(audioFile, options),
    {
      cwd: repoRoot,
      env: transcribeEnvironment(),
    },
  );
  if (result.stderr.trim()) {
    process.stderr.write(result.stderr);
  }
  if (result.code !== 0) {
    throw new Error(`STT failed with exit code ${result.code}`);
  }
  return result.stdout.trim();
}
