import { fetchFixtureCli } from "./shared/fetch-fixture";

process.exitCode = await fetchFixtureCli({
  dataset: "thetaone-ai/HiKE",
  config: "default",
  split: "test",
  sourcePage: "https://huggingface.co/datasets/thetaone-ai/HiKE",
  license: "apache-2.0",
  defaultPrefix: "hike-row",
  expectedField: "text_normalized",
  displayField: "text",
  metadataFields: [
    "text",
    "text_normalized",
    "text_pier_labeled",
    "cs_level",
    "cs_levels_all",
    "category",
    "loanwords",
    "sample_id",
  ],
});
