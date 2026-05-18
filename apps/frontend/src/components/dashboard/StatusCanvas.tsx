import { useEffect, useRef } from "react";
import { Card } from "../common/Card";

const bars = [0.35, 0.62, 0.84, 0.5, 0.9, 0.67];

export function StatusCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#050505";
    ctx.fillRect(0, 0, width, height);

    const gradient = ctx.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, "#39ff14");
    gradient.addColorStop(0.5, "#9efc6a");
    gradient.addColorStop(1, "#00c853");

    ctx.strokeStyle = "#39ff14";
    ctx.lineWidth = 1;
    ctx.strokeRect(0.5, 0.5, width - 1, height - 1);

    const step = width / bars.length;
    bars.forEach((value, index) => {
      const barHeight = Math.max(8, height * value);
      const x = index * step + 8;
      const y = height - barHeight - 10;
      ctx.fillStyle = index % 2 === 0 ? gradient : "#0f3";
      ctx.fillRect(x, y, step - 16, barHeight);
    });

    ctx.fillStyle = "#39ff14";
    ctx.font = "bold 12px Tahoma, Verdana, Arial, sans-serif";
    ctx.fillText("IDENTITY LOCK: API KEY", 12, 18);
    ctx.fillText("QUEUE: GREEN / STABLE", 12, 36);
    ctx.fillText("TELEMETRY: CONSENTED", 12, 54);
  }, []);

  return (
    <Card title="Canvas status" className="space-y-3">
      <p className="text-sm text-black">
        Retro process monitor for the current operator session.
      </p>
      <canvas ref={canvasRef} className="status-canvas" aria-label="Operator status graph" />
    </Card>
  );
}
