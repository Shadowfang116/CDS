"use client";

import { useEffect, useMemo, useRef } from "react";
import { normalizeRetropcConfig, primitiveRenderers, sampleLuminance, type RetropcConfig } from "@/lib/retropc";

function clamp(value: number, min = 0, max = 1) { return Math.max(min, Math.min(max, value)); }

function seeded(x: number, y: number, frame: number): number {
  const value = Math.sin(x * 12.9898 + y * 78.233 + frame * 0.013) * 43758.5453;
  return value - Math.floor(value);
}

function hexToRgb(hex: string): [number, number, number] {
  const value = hex.replace("#", "");
  return [Number.parseInt(value.slice(0, 2), 16) || 0, Number.parseInt(value.slice(2, 4), 16) || 0, Number.parseInt(value.slice(4, 6), 16) || 0];
}

function toneCurve(value: number, curve: RetropcConfig["toneCurve"]): number {
  const sorted = [...curve].sort((a, b) => a.x - b.x);
  const next = sorted.find((point) => point.x >= value) ?? sorted[sorted.length - 1];
  const previous = sorted.slice().reverse().find((point) => point.x <= value) ?? sorted[0];
  if (!next || !previous || next.x === previous.x) return clamp(next?.y ?? value);
  return clamp(previous.y + ((value - previous.x) / (next.x - previous.x)) * (next.y - previous.y));
}

function adjustedColor(sample: { r: number; g: number; b: number; luminance: number }, config: RetropcConfig, phase: number): string {
  let r = sample.r; let g = sample.g; let b = sample.b;
  const brightness = config.brightness * 2.55;
  r += brightness; g += brightness; b += brightness;
  const contrast = config.contrast / 100;
  r = (r - 128) * contrast + 128; g = (g - 128) * contrast + 128; b = (b - 128) * contrast + 128;
  const gray = (0.2126 * r + 0.7152 * g + 0.0722 * b);
  const saturation = config.saturation / 100;
  r = gray + (r - gray) * saturation; g = gray + (g - gray) * saturation; b = gray + (b - gray) * saturation;
  const grayMix = config.grayscale / 100;
  r = r + (gray - r) * grayMix; g = g + (gray - g) * grayMix; b = b + (gray - b) * grayMix;
  const tint = hexToRgb(config.tint); const tintMix = config.tintOpacity / 100;
  if (config.overlayBlend === "overlay") {
    const overlay = (base: number, layer: number) => base < 128 ? (2 * base * layer) / 255 : 255 - (2 * (255 - base) * (255 - layer)) / 255;
    r = r * (1 - tintMix) + overlay(r, tint[0]) * tintMix; g = g * (1 - tintMix) + overlay(g, tint[1]) * tintMix; b = b * (1 - tintMix) + overlay(b, tint[2]) * tintMix;
  } else { r = r * (1 - tintMix) + tint[0] * tintMix; g = g * (1 - tintMix) + tint[1] * tintMix; b = b * (1 - tintMix) + tint[2] * tintMix; }
  const adjustedLuminance = toneCurve(clamp((0.2126 * r + 0.7152 * g + 0.0722 * b) / 255), config.toneCurve);
  const flicker = config.animated && config.animStyle === "flicker" ? (seeded(r, g, phase) - 0.5) * config.animIntensity.intensity / 100 * 16 : 0;
  return `rgb(${Math.round(clamp(r + flicker, 0, 255))} ${Math.round(clamp(g + flicker, 0, 255))} ${Math.round(clamp(b + flicker, 0, 255))} / ${clamp(adjustedLuminance * 1.4)})`;
}

function animationPhase(config: RetropcConfig, elapsed: number): number {
  const speed = (config.animSpeed.enabled ? config.animSpeed.intensity : 0) / 100;
  if (!config.animated || speed === 0) return 0;
  const t = elapsed * (0.0005 + speed * 0.002);
  if (config.animStyle === "wave") return t;
  if (config.animStyle === "pulse") return Math.sin(t) * 0.5 + 0.5;
  if (config.animStyle === "shimmer") return Math.sin(t * 2.5);
  if (config.animStyle === "ripple") return Math.sin(t + elapsed * 0.0001);
  return Math.floor(t * 12);
}

function drawPostEffects(ctx: CanvasRenderingContext2D, width: number, height: number, config: RetropcConfig, frame: number) {
  const intensity = (name: string) => (config.pfx[name]?.enabled ? config.pfx[name].intensity / 100 : 0);
  const scan = intensity("scanLines");
  if (scan) { ctx.fillStyle = `rgba(0,0,0,${scan * 0.22})`; for (let y = 0; y < height; y += 4) ctx.fillRect(0, y, width, 1); }
  const grain = intensity("filmGrain");
  if (grain) { ctx.fillStyle = `rgba(255,255,255,${grain * 0.08})`; for (let i = 0; i < width * height * grain * 0.002; i += 1) ctx.fillRect(seeded(i, frame, frame) * width, seeded(frame, i, frame + 1) * height, 1, 1); }
  const halftone = intensity("halftone");
  if (halftone) { ctx.fillStyle = `rgba(0,0,0,${halftone * 0.12})`; for (let y = 0; y < height; y += 8) for (let x = 0; x < width; x += 8) ctx.fillRect(x, y, 2, 2); }
  const dust = intensity("filmDust");
  if (dust) { ctx.fillStyle = `rgba(255,255,255,${dust * 0.18})`; for (let i = 0; i < width * dust * 0.01; i += 1) ctx.fillRect(seeded(i, frame, 3) * width, seeded(frame, i, 5) * height, 1, 1); }
  const glitch = intensity("glitch");
  if (glitch) { ctx.fillStyle = `rgba(0,255,180,${glitch * 0.12})`; ctx.fillRect(seeded(frame, 2, 7) * width, seeded(frame, 4, 9) * height, width * glitch * 0.15, 1); }
  const vignette = intensity("vignette");
  if (vignette) { const gradient = ctx.createRadialGradient(width / 2, height / 2, Math.min(width, height) * 0.18, width / 2, height / 2, Math.max(width, height) * 0.75); gradient.addColorStop(0, "transparent"); gradient.addColorStop(1, `rgba(0,0,0,${vignette * 0.72})`); ctx.fillStyle = gradient; ctx.fillRect(0, 0, width, height); }
}

export function RetropcAscii({ config: configOverride }: { config?: Partial<RetropcConfig> }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const config = useMemo(() => normalizeRetropcConfig(configOverride), [configOverride]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;
    const image = new Image();
    image.src = "/retropc-subject.svg";
    let frame = 0; let resizeObserver: ResizeObserver | null = null; let reducedMotion = false; let visible = true;
    const sourceCanvas = document.createElement("canvas"); const sourceCtx = sourceCanvas.getContext("2d");
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onMotion = () => { reducedMotion = media.matches; };
    onMotion(); media.addEventListener?.("change", onMotion);
    const resize = () => { const dpr = Math.min(2, window.devicePixelRatio || 1); const width = Math.max(1, window.innerWidth); const height = Math.max(1, window.innerHeight); canvas.width = width * dpr; canvas.height = height * dpr; canvas.style.width = `${width}px`; canvas.style.height = `${height}px`; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); sourceCanvas.width = width; sourceCanvas.height = height; };
    resize(); resizeObserver = new ResizeObserver(resize); resizeObserver.observe(document.documentElement);
    const draw = (elapsed: number) => {
      const width = window.innerWidth; const height = window.innerHeight; const current = reducedMotion ? 0 : elapsed; const phase = animationPhase(config, current);
      ctx.clearRect(0, 0, width, height);
      if (!image.complete || image.naturalWidth === 0) { ctx.fillStyle = "#07121b"; ctx.fillRect(0, 0, width, height); return; }
      const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight); const drawWidth = image.naturalWidth * scale; const drawHeight = image.naturalHeight * scale; const offsetX = (width - drawWidth) / 2; const offsetY = (height - drawHeight) / 2;
      if (config.bgMode !== "none") { ctx.save(); ctx.globalAlpha = config.bgOpacity / 100; ctx.filter = config.bgMode === "blurred" ? `blur(${config.bgBlur}px)` : "none"; ctx.drawImage(image, offsetX, offsetY, drawWidth, drawHeight); ctx.restore(); }
      if (!sourceCtx) return; sourceCtx.drawImage(image, offsetX, offsetY, drawWidth, drawHeight); const pixels = sourceCtx.getImageData(0, 0, width, height);
      const cell = config.cellSize; ctx.save(); ctx.globalCompositeOperation = config.styleBlend; ctx.shadowColor = config.tint; ctx.shadowBlur = config.pfx.bloom?.enabled ? config.pfx.bloom.intensity / 4 : 0;
      for (let y = 0; y < height; y += cell) for (let x = 0; x < width; x += cell) {
        const sample = sampleLuminance(pixels, x, y, width, height); const luminosity = config.invert ? 1 - sample.luminance : sample.luminance; const density = clamp(luminosity + config.density / 100); if (seeded(x, y, Math.floor(phase)) > config.coverage / 100 || density < 0.04) continue;
        const wobble = config.animStyle === "wave" ? Math.sin(phase + x * 0.03) * cell * 0.12 : config.animStyle === "ripple" ? Math.sin(phase + Math.hypot(x - width / 2, y - height / 2) * 0.03) * cell * 0.1 : 0;
        const color = adjustedColor({ ...sample, luminance: luminosity }, config, phase); primitiveRenderers[config.renderMode](ctx, x + cell / 2, y + cell / 2 + wobble, cell * (0.65 + density * 0.35), luminosity, color, phase + x + y);
      }
      ctx.restore();
      if (config.lights.enabled) config.lights.points.forEach((light) => { const gradient = ctx.createRadialGradient(light.x * width, light.y * height, 0, light.x * width, light.y * height, light.radius); gradient.addColorStop(0, `rgba(72,255,194,${light.intensity / 100})`); gradient.addColorStop(1, "transparent"); ctx.fillStyle = gradient; ctx.fillRect(0, 0, width, height); });
      drawPostEffects(ctx, width, height, config, phase);
      frame = window.requestAnimationFrame(draw);
    };
    const start = () => { if (visible) { window.cancelAnimationFrame(frame); frame = window.requestAnimationFrame(draw); } };
    const onVisibility = () => { visible = document.visibilityState === "visible"; if (visible) start(); else window.cancelAnimationFrame(frame); };
    image.onload = start; document.addEventListener("visibilitychange", onVisibility); start();
    return () => { window.cancelAnimationFrame(frame); resizeObserver?.disconnect(); media.removeEventListener?.("change", onMotion); document.removeEventListener("visibilitychange", onVisibility); };
  }, [config]);

  return <canvas ref={canvasRef} aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 opacity-80" data-testid="retropc-canvas" />;
}
