export type RetropcRenderMode =
  | "characters" | "dither" | "mosaic" | "pixel" | "dots" | "cross" | "diamond" | "voxel" | "lego" | "mixed"
  | "lines" | "diagonal" | "braille" | "disco" | "hexdump" | "matrix" | "rings" | "hearts" | "stars"
  | "hexagons" | "triangles" | "bubbles" | "hatch" | "contour" | "halfblocks";

export type RetropcConfig = {
  renderMode: RetropcRenderMode;
  bgMode: "blurred" | "solid" | "original" | "none";
  bgBlur: number;
  bgOpacity: number;
  cellSize: number;
  coverage: number;
  invert: boolean;
  styleBlend: GlobalCompositeOperation;
  charSet: "binary" | "ascii" | "custom";
  customChars: string;
  brightness: number;
  contrast: number;
  edgeEmphasis: number;
  density: number;
  toneCurve: Array<{ x: number; y: number }>;
  tint: string;
  tintOpacity: number;
  overlayBlend: GlobalCompositeOperation;
  saturation: number;
  grayscale: number;
  blurType: "off" | "gaussian" | "directional" | "tilt" | "lens" | "progressive";
  blurAmount: number;
  blurAngle: number;
  directionalBothSides: boolean;
  tiltFocus: number;
  tiltPosition: number;
  tiltFeather: number;
  lensFocus: number;
  blurCenterX: number;
  blurCenterY: number;
  progressivePosition: number;
  progressiveReverse: boolean;
  pfx: Record<string, { enabled: boolean; intensity: number }>;
  animated: boolean;
  animStyle: "wave" | "pulse" | "shimmer" | "ripple" | "flicker";
  animSpeed: { enabled: boolean; intensity: number };
  animIntensity: { enabled: boolean; intensity: number };
  lights: { enabled: boolean; points: Array<{ x: number; y: number; radius: number; intensity: number }> };
  mask: { enabled: boolean; tool: "freehand" | "shape"; brushSize: number; showOverlay: boolean; invert: boolean; dataUrl: string | null; shapes: unknown[] };
};

const pfx = {
  vignette: { enabled: true, intensity: 72 }, scanLines: { enabled: false, intensity: 28 }, chromatic: { enabled: false, intensity: 15 },
  bloom: { enabled: false, intensity: 25 }, filmGrain: { enabled: false, intensity: 40 }, glitch: { enabled: false, intensity: 20 },
  pixelate: { enabled: false, intensity: 15 }, halftone: { enabled: false, intensity: 20 }, filmDust: { enabled: false, intensity: 20 },
};

export const RETROPC_DEFAULT_CONFIG: RetropcConfig = {
  renderMode: "lego", bgMode: "original", bgBlur: 11, bgOpacity: 100, cellSize: 9, coverage: 100, invert: false,
  styleBlend: "source-over", charSet: "binary", customChars: "", brightness: 0, contrast: 115, edgeEmphasis: 40,
  density: 0, toneCurve: [{ x: 0, y: 0 }, { x: 1, y: 1 }], tint: "#00ff66", tintOpacity: 45, overlayBlend: "overlay",
  saturation: 100, grayscale: 0, blurType: "off", blurAmount: 35, blurAngle: 0, directionalBothSides: false, tiltFocus: 35,
  tiltPosition: 50, tiltFeather: 15, lensFocus: 40, blurCenterX: 50, blurCenterY: 50, progressivePosition: 55,
  progressiveReverse: false, pfx, animated: true, animStyle: "flicker", animSpeed: { enabled: true, intensity: 100 },
  animIntensity: { enabled: true, intensity: 60 }, lights: { enabled: false, points: [] },
  mask: { enabled: false, tool: "freehand", brushSize: 30, showOverlay: false, invert: false, dataUrl: null, shapes: [] },
};

export function normalizeRetropcConfig(overrides: Partial<RetropcConfig> = {}): RetropcConfig {
  return {
    ...RETROPC_DEFAULT_CONFIG,
    ...overrides,
    cellSize: Math.max(1, Math.round(overrides.cellSize ?? RETROPC_DEFAULT_CONFIG.cellSize)),
    coverage: Math.max(0, Math.min(100, overrides.coverage ?? RETROPC_DEFAULT_CONFIG.coverage)),
    pfx: { ...RETROPC_DEFAULT_CONFIG.pfx, ...(overrides.pfx ?? {}) },
    animSpeed: { ...RETROPC_DEFAULT_CONFIG.animSpeed, ...(overrides.animSpeed ?? {}) },
    animIntensity: { ...RETROPC_DEFAULT_CONFIG.animIntensity, ...(overrides.animIntensity ?? {}) },
    lights: { ...RETROPC_DEFAULT_CONFIG.lights, ...(overrides.lights ?? {}) },
    mask: { ...RETROPC_DEFAULT_CONFIG.mask, ...(overrides.mask ?? {}) },
  };
}

export type PrimitiveRenderer = (ctx: CanvasRenderingContext2D, x: number, y: number, size: number, luminance: number, color: string, phase: number) => void;

function polygon(ctx: CanvasRenderingContext2D, points: Array<[number, number]>) {
  ctx.beginPath();
  points.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
  ctx.closePath();
  ctx.fill();
}

const drawBasic: PrimitiveRenderer = (ctx, x, y, size, luminance, color, phase) => {
  ctx.fillStyle = color;
  ctx.fillRect(x - size / 2, y - size / 2, size * (0.25 + luminance * 0.75), size * (0.25 + luminance * 0.75));
  void phase;
};

export const primitiveRenderers: Record<RetropcRenderMode, PrimitiveRenderer> = {
  characters: drawBasic,
  dither: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; const dots = luminance > 0.5 ? 4 : 2; for (let i = 0; i < dots; i += 1) ctx.fillRect(x - size / 3 + (i % 2) * size / 2, y - size / 3 + Math.floor(i / 2) * size / 2, size / 5, size / 5); },
  mosaic: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; ctx.fillRect(x - size / 2, y - size / 2, size, size * luminance); },
  pixel: (ctx, x, y, size, _luminance, color) => { ctx.fillStyle = color; ctx.fillRect(x - size / 2, y - size / 2, size, size); },
  dots: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, Math.max(1, size * luminance * 0.45), 0, Math.PI * 2); ctx.fill(); },
  cross: (ctx, x, y, size, _luminance, color) => { ctx.strokeStyle = color; ctx.lineWidth = Math.max(1, size / 5); ctx.beginPath(); ctx.moveTo(x - size / 2, y); ctx.lineTo(x + size / 2, y); ctx.moveTo(x, y - size / 2); ctx.lineTo(x, y + size / 2); ctx.stroke(); },
  diamond: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; polygon(ctx, [[x, y - size * luminance / 2], [x + size * luminance / 2, y], [x, y + size * luminance / 2], [x - size * luminance / 2, y]]); },
  voxel: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; polygon(ctx, [[x - size / 2, y - size / 3], [x, y - size / 2], [x + size / 2, y - size / 3], [x, y - size / 6]]); ctx.globalAlpha = 0.65; polygon(ctx, [[x - size / 2, y - size / 3], [x, y - size / 6], [x, y + size / 2], [x - size / 2, y + size / 6]]); ctx.globalAlpha = 1; },
  lego: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; ctx.fillRect(x - size * 0.43, y - size * 0.38, size * 0.86, size * 0.76); ctx.fillStyle = "rgba(255,255,255,.35)"; ctx.beginPath(); ctx.arc(x - size * 0.2, y - size * 0.2, size * 0.09, 0, Math.PI * 2); ctx.arc(x + size * 0.2, y - size * 0.2, size * 0.09, 0, Math.PI * 2); ctx.fill(); void luminance; },
  mixed: (ctx, x, y, size, luminance, color, phase) => (phase % 3 < 1 ? primitiveRenderers.dots : phase % 3 < 2 ? primitiveRenderers.diamond : primitiveRenderers.lines)(ctx, x, y, size, luminance, color, phase),
  lines: (ctx, x, y, size, luminance, color) => { ctx.strokeStyle = color; ctx.lineWidth = Math.max(1, size / 7); ctx.beginPath(); ctx.moveTo(x - size / 2, y + size / 3); ctx.lineTo(x + size / 2, y - size * luminance / 2); ctx.stroke(); },
  diagonal: (ctx, x, y, size, _luminance, color) => { ctx.strokeStyle = color; ctx.lineWidth = Math.max(1, size / 6); ctx.beginPath(); ctx.moveTo(x - size / 2, y + size / 2); ctx.lineTo(x + size / 2, y - size / 2); ctx.stroke(); },
  braille: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; for (let i = 0; i < 6; i += 1) if ((i + Math.round(luminance * 5)) % 2 === 0) { ctx.beginPath(); ctx.arc(x + (i % 2 ? size / 5 : -size / 5), y + (Math.floor(i / 2) - 1) * size / 4, size / 10, 0, Math.PI * 2); ctx.fill(); } },
  disco: (ctx, x, y, size, luminance, color, phase) => { ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, size * (0.2 + luminance * 0.25), phase, phase + Math.PI * 1.5); ctx.lineTo(x, y); ctx.fill(); },
  hexdump: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; ctx.font = `${Math.max(8, size * 0.62)}px monospace`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(Math.floor(luminance * 15).toString(16), x, y); },
  matrix: (ctx, x, y, size, luminance, color, phase) => { ctx.fillStyle = color; ctx.font = `${Math.max(8, size * 0.7)}px monospace`; ctx.textAlign = "center"; ctx.fillText(((Math.floor(x / size) + Math.floor(y / size) + Math.floor(phase)) % 2 ? "1" : "0"), x, y + Math.sin(phase + x) * size * 0.2); void luminance; },
  rings: (ctx, x, y, size, luminance, color) => { ctx.strokeStyle = color; ctx.lineWidth = Math.max(1, size / 8); ctx.beginPath(); ctx.arc(x, y, size * (0.15 + luminance * 0.35), 0, Math.PI * 2); ctx.stroke(); },
  hearts: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; ctx.font = `${Math.max(9, size * luminance)}px serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText("♥", x, y); },
  stars: (ctx, x, y, size, luminance, color, phase) => { ctx.fillStyle = color; const points: Array<[number, number]> = []; for (let i = 0; i < 10; i += 1) { const radius = i % 2 ? size * luminance * 0.2 : size * luminance * 0.5; const angle = phase + i * Math.PI / 5; points.push([x + Math.cos(angle) * radius, y + Math.sin(angle) * radius]); } polygon(ctx, points); },
  hexagons: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; const points: Array<[number, number]> = []; for (let i = 0; i < 6; i += 1) points.push([x + Math.cos(i * Math.PI / 3) * size * luminance * 0.45, y + Math.sin(i * Math.PI / 3) * size * luminance * 0.45]); polygon(ctx, points); },
  triangles: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; polygon(ctx, [[x, y - size * luminance / 2], [x + size * luminance / 2, y + size * luminance / 2], [x - size * luminance / 2, y + size * luminance / 2]]); },
  bubbles: (ctx, x, y, size, luminance, color) => { ctx.strokeStyle = color; ctx.lineWidth = Math.max(1, size / 10); ctx.beginPath(); ctx.arc(x, y, size * luminance * 0.4, 0, Math.PI * 2); ctx.stroke(); },
  hatch: (ctx, x, y, size, luminance, color) => { ctx.strokeStyle = color; ctx.lineWidth = Math.max(1, size / 10); for (let i = -1; i <= 1; i += 1) { ctx.beginPath(); ctx.moveTo(x - size / 2, y + i * size / 3); ctx.lineTo(x + size / 2, y + i * size / 3 - size * luminance / 2); ctx.stroke(); } },
  contour: (ctx, x, y, size, luminance, color) => { ctx.strokeStyle = color; ctx.lineWidth = Math.max(1, size / 12); ctx.beginPath(); ctx.arc(x, y, size * (0.15 + luminance * 0.35), 0, Math.PI * 1.7); ctx.stroke(); },
  halfblocks: (ctx, x, y, size, luminance, color) => { ctx.fillStyle = color; ctx.fillRect(x - size / 2, y - size / 2, size, size * luminance / 2); },
};

export function sampleLuminance(data: ImageData, x: number, y: number, width: number, height: number): { r: number; g: number; b: number; luminance: number } {
  const samples = [[x, y], [Math.min(width - 1, x + 1), y], [x, Math.min(height - 1, y + 1)], [Math.min(width - 1, x + 1), Math.min(height - 1, y + 1)]];
  const total = samples.reduce((sum, [sampleX, sampleY]) => {
    const index = (sampleY * width + sampleX) * 4;
    return { r: sum.r + data.data[index], g: sum.g + data.data[index + 1], b: sum.b + data.data[index + 2] };
  }, { r: 0, g: 0, b: 0 });
  const r = total.r / samples.length; const g = total.g / samples.length; const b = total.b / samples.length;
  return { r, g, b, luminance: (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 };
}
