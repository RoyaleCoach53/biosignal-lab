const base = new URL(import.meta.env.BASE_URL, document.baseURI);
export const asset = name => new URL(name, base).href;
export async function fetchSynthetic(name, signal) {
  const response = await fetch(asset("scenarios/" + name + ".json"), { signal });
  if (!response.ok) throw new Error("Synthetic data could not be loaded.");
  const data = await response.json();
  if (data.provenance !== "synthetic") throw new Error("Unexpected catalogue data.");
  return data;
}
