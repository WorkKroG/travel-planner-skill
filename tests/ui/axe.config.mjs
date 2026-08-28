export const axeOptions = {
  runOnly: {
    type: "tag",
    values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
  },
  resultTypes: ["violations"],
};

export const blockingImpacts = new Set(["critical", "serious"]);
