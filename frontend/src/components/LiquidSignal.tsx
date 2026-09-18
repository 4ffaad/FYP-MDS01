"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

const POINT_COUNT = 96;

type SignalLine = {
  object: THREE.Line<THREE.BufferGeometry, THREE.LineBasicMaterial>;
  phase: number;
  amplitude: number;
};

function createSignalLine(
  phase: number,
  amplitude: number,
  color: string,
  opacity: number,
): SignalLine {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.BufferAttribute(new Float32Array(POINT_COUNT * 3), 3),
  );
  const material = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity,
  });
  return {
    object: new THREE.Line(geometry, material),
    phase,
    amplitude,
  };
}

function updateSignalLine(line: SignalLine, time: number) {
  const position = line.object.geometry.getAttribute(
    "position",
  ) as THREE.BufferAttribute;
  const values = position.array as Float32Array;
  for (let index = 0; index < POINT_COUNT; index += 1) {
    const progress = index / (POINT_COUNT - 1);
    const x = (progress - 0.5) * 5.8;
    const envelope = 0.6 + Math.sin(progress * Math.PI) * 0.55;
    const y =
      Math.sin(progress * 10.5 + time * 0.8 + line.phase) *
        line.amplitude *
        envelope +
      Math.sin(progress * 23 + time * 0.45 + line.phase) * 0.045;
    values[index * 3] = x;
    values[index * 3 + 1] = y;
    values[index * 3 + 2] = 0;
  }
  position.needsUpdate = true;
}

function disposeSignalLine(line: SignalLine) {
  line.object.geometry.dispose();
  line.object.material.dispose();
}

function SignalCanvas({ reducedMotion }: { reducedMotion: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: "low-power",
      });
    } catch {
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-3.4, 3.4, 1, -1, 0.1, 100);
    camera.position.z = 8;

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.domElement.style.display = "block";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.width = "100%";
    renderer.domElement.setAttribute("aria-hidden", "true");
    container.appendChild(renderer.domElement);

    const lines = [
      createSignalLine(0, 0.34, "#1473e6", 0.78),
      createSignalLine(1.7, 0.2, "#5ac8fa", 0.48),
    ];
    lines.forEach(({ object }) => scene.add(object));

    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(0.13, 18, 18),
      new THREE.MeshPhysicalMaterial({
        color: "#c6e6ff",
        roughness: 0.16,
        metalness: 0.05,
        transmission: 0.72,
        transparent: true,
        opacity: 0.9,
      }),
    );
    sphere.position.set(2.15, 0.08, 0.12);
    scene.add(sphere);

    const timer = new THREE.Timer();
    timer.connect(document);
    let animationFrame: number | undefined;

    const resize = () => {
      const width = Math.max(container.clientWidth, 1);
      const height = Math.max(container.clientHeight, 1);
      const aspect = width / height;
      const halfWidth = 3.4;
      const halfHeight = halfWidth / aspect;
      camera.left = -halfWidth;
      camera.right = halfWidth;
      camera.top = halfHeight;
      camera.bottom = -halfHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };

    const render = () => {
      timer.update();
      const time = timer.getElapsed();
      lines.forEach((line) => updateSignalLine(line, time));
      renderer.render(scene, camera);
      if (!reducedMotion) animationFrame = requestAnimationFrame(render);
    };

    resize();
    const resizeObserver =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    resizeObserver?.observe(container);
    if (!resizeObserver) window.addEventListener("resize", resize);
    render();

    return () => {
      if (animationFrame !== undefined) cancelAnimationFrame(animationFrame);
      resizeObserver?.disconnect();
      if (!resizeObserver) window.removeEventListener("resize", resize);
      timer.disconnect();
      lines.forEach(disposeSignalLine);
      sphere.geometry.dispose();
      sphere.material.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [reducedMotion]);

  return (
    <div ref={containerRef} className="liquid-signal" aria-hidden="true" />
  );
}

export function LiquidSignal() {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  return <SignalCanvas reducedMotion={reducedMotion} />;
}
