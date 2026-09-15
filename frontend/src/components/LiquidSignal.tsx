"use client";

import { useFrame, Canvas } from "@react-three/fiber";
import { useEffect, useMemo, useState } from "react";
import * as THREE from "three";

const POINT_COUNT = 96;

function SignalLine({
  phase,
  amplitude,
  color,
  opacity,
}: {
  phase: number;
  amplitude: number;
  color: string;
  opacity: number;
}) {
  const line = useMemo(() => {
    const nextGeometry = new THREE.BufferGeometry();
    nextGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(new Float32Array(POINT_COUNT * 3), 3),
    );
    const material = new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity,
    });
    return new THREE.Line(nextGeometry, material);
  }, [color, opacity]);

  useEffect(
    () => () => {
      line.geometry.dispose();
      (line.material as THREE.Material).dispose();
    },
    [line],
  );

  useFrame(({ clock }) => {
    const position = line.geometry.getAttribute(
      "position",
    ) as THREE.BufferAttribute;
    const values = position.array as Float32Array;
    const time = clock.getElapsedTime();
    for (let index = 0; index < POINT_COUNT; index += 1) {
      const progress = index / (POINT_COUNT - 1);
      const x = (progress - 0.5) * 5.8;
      const envelope = 0.6 + Math.sin(progress * Math.PI) * 0.55;
      const y =
        Math.sin(progress * 10.5 + time * 0.8 + phase) * amplitude * envelope +
        Math.sin(progress * 23 + time * 0.45 + phase) * 0.045;
      values[index * 3] = x;
      values[index * 3 + 1] = y;
      values[index * 3 + 2] = 0;
    }
    position.needsUpdate = true;
  });

  return <primitive object={line} />;
}

function SignalScene({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <Canvas
      aria-hidden="true"
      dpr={[1, 1.5]}
      frameloop={reducedMotion ? "never" : "always"}
      orthographic
      camera={{ position: [0, 0, 8], zoom: 34 }}
      gl={{ alpha: true, antialias: true, powerPreference: "low-power" }}
    >
      <SignalLine phase={0} amplitude={0.34} color="#1473e6" opacity={0.78} />
      <SignalLine phase={1.7} amplitude={0.2} color="#5ac8fa" opacity={0.48} />
      <mesh position={[2.15, 0.08, 0.12]}>
        <sphereGeometry args={[0.13, 18, 18]} />
        <meshPhysicalMaterial
          color="#c6e6ff"
          roughness={0.16}
          metalness={0.05}
          transmission={0.72}
          transparent
          opacity={0.9}
        />
      </mesh>
    </Canvas>
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

  return (
    <div className="liquid-signal" aria-hidden="true">
      <SignalScene reducedMotion={reducedMotion} />
    </div>
  );
}
