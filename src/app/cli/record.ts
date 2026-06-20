import { parsePositiveInteger, recordAudio } from "@/features/audio-recording";

import { isDirectRun } from "./shared/direct-run";

export async function main(argv = process.argv.slice(2)): Promise<number> {
  if (argv[0] === "-h" || argv[0] === "--help") {
    process.stdout.write(`${usage()}\n`);
    return 0;
  }
  try {
    if (argv.length > 1) {
      throw new Error("expected at most one duration argument");
    }
    const duration = parsePositiveInteger(argv[0] ?? "5", "duration_seconds");
    const outputDir = process.env.STT_OUTPUT_DIR ?? "output/recordings";
    process.stderr.write(`recording: ${duration}s -> ${outputDir}\n`);
    const outputFile = await recordAudio(duration, outputDir);
    process.stdout.write(`${outputFile}\n`);
    return 0;
  } catch (error) {
    process.stderr.write(
      `error: ${error instanceof Error ? error.message : String(error)}\n`,
    );
    return 2;
  }
}

function usage(): string {
  return "Usage: npm run record -- [duration_seconds]";
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await main();
}
