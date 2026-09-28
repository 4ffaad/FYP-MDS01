export function highestScoringAttribution<T extends { score: number }>(
  attributions: readonly T[],
): T | null {
  let highest: T | null = null;
  for (const attribution of attributions) {
    if (highest === null || attribution.score > highest.score) {
      highest = attribution;
    }
  }
  return highest;
}
