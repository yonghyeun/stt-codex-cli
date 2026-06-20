export function hasMeaningfulText(text: string): boolean {
  return Array.from(text).some((character) => /[\p{L}\p{N}]/u.test(character));
}
