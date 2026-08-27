import assert from "node:assert/strict";
import { RETROPC_DEFAULT_CONFIG, normalizeRetropcConfig, primitiveRenderers } from "./retropc";

assert.equal(RETROPC_DEFAULT_CONFIG.renderMode, "lego");
assert.equal(RETROPC_DEFAULT_CONFIG.bgMode, "original");
assert.equal(RETROPC_DEFAULT_CONFIG.tint, "#00ff66");
assert.equal(RETROPC_DEFAULT_CONFIG.pfx.vignette.intensity, 72);
assert.equal(RETROPC_DEFAULT_CONFIG.animStyle, "flicker");
assert.equal(normalizeRetropcConfig({ cellSize: 0 }).cellSize, 1);
assert.equal(normalizeRetropcConfig({ coverage: 140 }).coverage, 100);
assert.deepEqual(Object.keys(primitiveRenderers).sort(), [
  "braille", "bubbles", "characters", "contour", "cross", "diagonal", "diamond", "disco", "dither", "dots", "hearts", "hatch", "hexdump", "hexagons", "halfblocks", "lego", "lines", "matrix", "mixed", "mosaic", "pixel", "rings", "stars", "triangles", "voxel",
].sort());

console.log("retropc tests passed");
