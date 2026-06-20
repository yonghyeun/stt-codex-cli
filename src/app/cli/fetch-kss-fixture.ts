import { fetchFixtureCli } from "./shared/fetch-fixture";

process.exitCode = await fetchFixtureCli({
  dataset: "Bingsu/KSS_Dataset",
  config: "default",
  split: "train",
  sourcePage: "https://huggingface.co/datasets/Bingsu/KSS_Dataset",
  license: "cc-by-nc-sa-4.0",
  defaultPrefix: "kss-row",
  expectedField: "expanded_script",
  metadataFields: [
    "original_script",
    "expanded_script",
    "duration",
    "english_translation",
  ],
});
