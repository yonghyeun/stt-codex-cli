import { existsSync } from "node:fs";
import { basename, dirname, isAbsolute, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

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

export interface PythonRuntime {
  pythonPath: string;
  venvRoot?: string;
}

export function pythonRuntimeCandidates(
  root: string,
  env: NodeJS.ProcessEnv = process.env,
  gitCommonDir = gitCommonDirectory(root),
): PythonRuntime[] {
  const candidates: PythonRuntime[] = [];
  if (env.STT_PYTHON) {
    candidates.push({ pythonPath: env.STT_PYTHON });
  }

  candidates.push({
    pythonPath: join(root, ".venv/bin/python"),
    venvRoot: join(root, ".venv"),
  });

  const mainWorktreeRoot = mainWorktreeRootFromGitCommonDir(root, gitCommonDir);
  if (mainWorktreeRoot && mainWorktreeRoot !== root) {
    candidates.push({
      pythonPath: join(mainWorktreeRoot, ".venv/bin/python"),
      venvRoot: join(mainWorktreeRoot, ".venv"),
    });
  }

  candidates.push({ pythonPath: "python3" });
  return dedupeCandidates(candidates);
}

export function resolvePythonRuntime(
  root = repoRoot,
  env: NodeJS.ProcessEnv = process.env,
): PythonRuntime {
  const candidates = pythonRuntimeCandidates(root, env);
  const runtime = candidates.find((candidate) =>
    candidate.pythonPath === "python3"
      ? commandExists("python3")
      : existsSync(candidate.pythonPath),
  );
  if (runtime) {
    return runtime;
  }

  throw new Error(
    [
      "Python runtime not found.",
      "Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
      "Or set STT_PYTHON=/path/to/python.",
    ].join(" "),
  );
}

export function transcribeEnvironment(
  env: NodeJS.ProcessEnv = process.env,
  venvRoot = join(repoRoot, ".venv"),
): NodeJS.ProcessEnv {
  const sitePackages = join(venvRoot, "lib/python3.12/site-packages");
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
  const runtime = resolvePythonRuntime();
  const result = await runCommand(
    runtime.pythonPath,
    buildTranscribeArgs(audioFile, options),
    {
      cwd: repoRoot,
      env: transcribeEnvironment(process.env, runtime.venvRoot),
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

function gitCommonDirectory(root: string): string | undefined {
  const result = spawnSync(
    "git",
    ["-C", root, "rev-parse", "--git-common-dir"],
    {
      encoding: "utf8",
    },
  );
  if (result.status !== 0) {
    return undefined;
  }
  const value = result.stdout.trim();
  if (!value) {
    return undefined;
  }
  return isAbsolute(value) ? value : resolve(root, value);
}

function mainWorktreeRootFromGitCommonDir(
  root: string,
  gitCommonDir: string | undefined,
): string | undefined {
  if (!gitCommonDir || basename(gitCommonDir) !== ".git") {
    return undefined;
  }
  return dirname(gitCommonDir);
}

function commandExists(command: string): boolean {
  const result = spawnSync("which", [command], { stdio: "ignore" });
  return result.status === 0;
}

function dedupeCandidates(candidates: PythonRuntime[]): PythonRuntime[] {
  const seen = new Set<string>();
  return candidates.filter((candidate) => {
    if (seen.has(candidate.pythonPath)) {
      return false;
    }
    seen.add(candidate.pythonPath);
    return true;
  });
}
