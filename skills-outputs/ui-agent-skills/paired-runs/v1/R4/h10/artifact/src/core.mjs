// Stable, deterministic JSON serialization (keys sorted) used by the driver
// to compare snapshots. Order-independent so the same logical value always
// stringifies identically.

function sortValue(value) {
  if (Array.isArray(value)) {
    return value.map(sortValue);
  }
  if (value !== null && typeof value === 'object') {
    const keys = Object.keys(value).sort();
    const out = {};
    for (const key of keys) out[key] = sortValue(value[key]);
    return out;
  }
  return value;
}

export function stableStringify(value) {
  return JSON.stringify(sortValue(value));
}

export default stableStringify;
