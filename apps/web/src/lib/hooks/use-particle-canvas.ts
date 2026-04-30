"use client";

import { useEffect, useRef } from "react";

type Particle = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
};

type ParticleConfig = {
  maxParticles?: number;
  spawnChance?: number;
  speed?: number;
  minLife?: number;
  maxLife?: number;
  minSize?: number;
  maxSize?: number;
  alpha?: number;
  fadeInFrames?: number;
  fadeOutFrames?: number;
};

const defaults: Required<ParticleConfig> = {
  maxParticles: 40,
  spawnChance: 0.04,
  speed: 0.1,
  minLife: 600,
  maxLife: 800,
  minSize: 0.3,
  maxSize: 1.0,
  alpha: 0.18,
  fadeInFrames: 120,
  fadeOutFrames: 200,
};

export function useParticleCanvas(config?: ParticleConfig) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cfg = { ...defaults, ...config };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let particles: Particle[] = [];

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = canvas.offsetWidth * dpr;
      canvas.height = canvas.offsetHeight * dpr;
      ctx.scale(dpr, dpr);
    };

    resize();
    window.addEventListener("resize", resize);

    const spawnParticle = () => {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * cfg.speed,
        vy: (Math.random() - 0.5) * cfg.speed,
        life: 0,
        maxLife: cfg.minLife + Math.random() * cfg.maxLife,
        size: cfg.minSize + Math.random() * cfg.maxSize,
      });
    };

    const animate = () => {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;
      ctx.clearRect(0, 0, w, h);

      if (particles.length < cfg.maxParticles && Math.random() < cfg.spawnChance) {
        spawnParticle();
      }

      particles = particles.filter((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.life++;

        if (p.life > p.maxLife) return false;

        const alpha =
          p.life < cfg.fadeInFrames
            ? p.life / cfg.fadeInFrames
            : p.life > p.maxLife - cfg.fadeOutFrames
              ? (p.maxLife - p.life) / cfg.fadeOutFrames
              : 1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(160, 150, 130, ${alpha * cfg.alpha})`;
        ctx.fill();

        return true;
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animationId);
    };
  }, [cfg]);

  return canvasRef;
}
