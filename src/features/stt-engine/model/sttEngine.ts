import { existsSync, readFileSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";

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
  vadModel?: string;
}

export const DEFAULT_TRANSCRIBE_OPTIONS: TranscribeOptions = {
  model: "large-v3",
  language: "ko",
  device: "auto",
  computeType: "auto",
  beamSize: 5,
  vadFilter: true,
};

export const DEFAULT_MODEL_DIR = join("output", "models", "whisper.cpp");

export const SUPPORTED_WHISPER_MODELS = [
  "tiny",
  "tiny.en",
  "tiny-q5_1",
  "tiny.en-q5_1",
  "tiny-q8_0",
  "base",
  "base.en",
  "base-q5_1",
  "base.en-q5_1",
  "base-q8_0",
  "small",
  "small.en",
  "small.en-tdrz",
  "small-q5_1",
  "small.en-q5_1",
  "small-q8_0",
  "medium",
  "medium.en",
  "medium-q5_0",
  "medium.en-q5_0",
  "medium-q8_0",
  "large-v1",
  "large-v2",
  "large-v2-q5_0",
  "large-v2-q8_0",
  "large-v3",
  "large-v3-q5_0",
  "large-v3-turbo",
  "large-v3-turbo-q5_0",
  "large-v3-turbo-q8_0",
] as const;

const require = createRequire(import.meta.url);

export function modelFileName(model: string): string {
  assertSupportedModel(model);
  return `ggml-${model}.bin`;
}

export function resolveWhisperModel(model: string, modelDir: string): string {
  return join(modelDir, modelFileName(model));
}

export function buildWhisperCliArgs(
  audioFile: string,
  modelFile: string,
  options: TranscribeOptions,
): string[] {
  const args = [
    "-m",
    modelFile,
    "-f",
    audioFile,
    "-l",
    options.language,
    "-bs",
    String(options.beamSize),
    "-np",
    "-nt",
  ];
  if (options.initialPrompt) {
    args.push("--prompt", options.initialPrompt);
  }
  if (options.device === "cpu") {
    args.push("-ng");
  }
  if (options.vadFilter && options.vadModel) {
    args.push("--vad", "-vm", options.vadModel);
  }
  return args;
}

export function parseWhisperStdout(stdout: string): string {
  return stdout
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s*\[[0-9:.]+\s+-->\s+[0-9:.]+\]\s*/, ""))
    .map((line) => line.trim())
    .filter((line) => line !== "")
    .filter((line) => !line.startsWith("whisper_"))
    .filter((line) => !line.startsWith("system_info:"))
    .filter((line) => !line.includes(": processing "))
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

export async function transcribeAudio(
  audioFile: string,
  options: TranscribeOptions,
): Promise<string> {
  const inputAudio = resolve(audioFile);
  if (!existsSync(inputAudio)) {
    throw new Error(`audio file not found: ${audioFile}`);
  }

  const whisperCppRoot = nodejsWhisperCppRoot();
  const modelDir = resolve(repoRoot, options.modelDir ?? DEFAULT_MODEL_DIR);
  const modelFile = resolveWhisperModel(options.model, modelDir);

  await ensureWhisperModel(options.model, modelDir, whisperCppRoot);
  const executable = await ensureWhisperExecutable(
    whisperCppRoot,
    options.device === "cuda",
  );

  const result = await runCommand(
    executable,
    buildWhisperCliArgs(inputAudio, modelFile, options),
    { cwd: repoRoot },
  );
  if (result.stderr.trim()) {
    process.stderr.write(result.stderr);
  }
  if (result.code !== 0) {
    throw new Error(`STT failed with exit code ${result.code}`);
  }

  const transcript = parseWhisperStdout(result.stdout);
  if (options.output) {
    await writeFile(options.output, `${transcript}\n`, "utf8");
  }
  return transcript;
}

function assertSupportedModel(model: string): void {
  if (!SUPPORTED_WHISPER_MODELS.includes(model as never)) {
    throw new Error(
      `unsupported STT model: ${model}. Supported models: ${SUPPORTED_WHISPER_MODELS.join(", ")}`,
    );
  }
}

function nodejsWhisperPackageRoot(): string {
  return dirname(require.resolve("nodejs-whisper/package.json"));
}

function nodejsWhisperCppRoot(): string {
  return join(nodejsWhisperPackageRoot(), "cpp", "whisper.cpp");
}

async function ensureWhisperModel(
  model: string,
  modelDir: string,
  whisperCppRoot: string,
): Promise<void> {
  const modelFile = resolveWhisperModel(model, modelDir);
  if (existsSync(modelFile)) {
    return;
  }

  await mkdir(modelDir, { recursive: true });
  const script = join(whisperCppRoot, "models", "download-ggml-model.sh");
  const result = await runCommand("sh", [script, model, modelDir], {
    cwd: repoRoot,
  });
  if (result.code !== 0) {
    throw new Error(
      [
        `model download failed with exit code ${result.code}`,
        result.stderr.trim(),
        result.stdout.trim(),
      ]
        .filter((line) => line !== "")
        .join("\n"),
    );
  }
}

async function ensureWhisperExecutable(
  whisperCppRoot: string,
  requireCuda: boolean,
): Promise<string> {
  const existing = whisperExecutable(whisperCppRoot);
  if (existing && (!requireCuda || cmakeCacheHasCuda(whisperCppRoot))) {
    return existing;
  }

  const configureArgs = ["-B", "build"];
  if (requireCuda) {
    configureArgs.push("-DGGML_CUDA=1");
  }
  const configure = await runCommand("cmake", configureArgs, {
    cwd: whisperCppRoot,
  });
  if (configure.code !== 0) {
    throw new Error(
      `whisper.cpp CMake configure failed with exit code ${configure.code}\n${configure.stderr.trim()}`,
    );
  }

  const build = await runCommand(
    "cmake",
    ["--build", "build", "--config", "Release"],
    { cwd: whisperCppRoot },
  );
  if (build.code !== 0) {
    throw new Error(
      `whisper.cpp build failed with exit code ${build.code}\n${build.stderr.trim()}`,
    );
  }

  const built = whisperExecutable(whisperCppRoot);
  if (!built) {
    throw new Error("whisper.cpp build finished but whisper-cli was not found");
  }
  return built;
}

function whisperExecutable(whisperCppRoot: string): string | undefined {
  const executable =
    process.platform === "win32" ? "whisper-cli.exe" : "whisper-cli";
  return [
    join(whisperCppRoot, "build", "bin", executable),
    join(whisperCppRoot, "build", "bin", "Release", executable),
    join(whisperCppRoot, "build", "bin", "Debug", executable),
    join(whisperCppRoot, "build", executable),
    join(whisperCppRoot, executable),
  ].find((candidate) => existsSync(candidate));
}

function cmakeCacheHasCuda(whisperCppRoot: string): boolean {
  const cachePath = join(whisperCppRoot, "build", "CMakeCache.txt");
  if (!existsSync(cachePath)) {
    return false;
  }
  const cache = readFileSync(cachePath, "utf8");
  return /GGML_CUDA:BOOL=(ON|1|TRUE)/.test(cache);
}
