// Procedural illustration. Coordinates do not represent anatomical landmarks.
const TAU = Math.PI * 2;
const surface = (side, u, v) => {
  const ring = Math.sin(u);
  const folds = 1 + .047 * Math.sin(15 * v + 8 * u) + .035 * Math.cos(23 * u - 7 * v);
  return [
    side * (.57 + .018*Math.sin(3*u) + ring * Math.cos(v) * .61 * folds),
    1.16 * Math.cos(u) + .12 * Math.sin(v) * ring + .035*side*ring,
    ring * Math.sin(v) * .70 * folds - .15 * Math.cos(u) - .07*Math.cos(v)*ring,
  ];
};
export function filaments() {
  const lines = [];
  for (const side of [-1, 1]) {
    for (let n = 1; n <= 57; n++) {
      const u = Math.PI * n / 58;
      lines.push({ side, type: "latitude", points: Array.from({ length: 121 }, (_, i) => {
        const v = TAU * i / 120;
        return surface(side, u + .026 * Math.sin(8 * v + 16 * u), v);
      }) });
    }
    for (let n = 0; n < 34; n++) {
      const v = TAU * n / 34;
      lines.push({ side, type: "longitude", points: Array.from({ length: 67 }, (_, i) => {
        const u = Math.PI * i / 66;
        return surface(side, u, v + .36 * Math.sin(u * 4.7 + v * 3) * Math.sin(u));
      }) });
    }
    for (let n = 0; n < 8; n++) {
      lines.push({side, type: "tract", points: Array.from({length: 91}, (_, i) => {
        const u = .23 + 2.65 * i / 90;
        return surface(side, u, .47 + n * .32 + .43 * Math.sin(4*u + n));
      })});
    }
  }
  return lines;
}
