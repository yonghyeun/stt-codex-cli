import { pathToFileURL } from "node:url";

export function isDirectRun(metaUrl: string): boolean {
  const entry = process.argv[1];
  return entry !== undefined && pathToFileURL(entry).href === metaUrl;
}
