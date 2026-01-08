"use client";

import React, { useMemo } from "react";
import * as THREE from "three";
import { useBounds } from "@react-three/drei";
import type { BrickPlacement } from "@/lib/types";

// ============================================================================
// LEGO Color Palette
// ============================================================================

const LEGO_COLORS: Record<string, string> = {
    red: "#C4281B",
    blue: "#0D69AB",
    yellow: "#F5CD2F",
    green: "#287F46",
    white: "#F2F3F2",
    black: "#1B2A34",
    brown: "#583927",
    tan: "#E4CD9E",
    gray: "#A1A5A2",
    orange: "#FE8A18",
    pink: "#FC97AC",
    purple: "#81007B",
    lime: "#BBE90B",
    // Fallback
    default: "#0066CC",
};

// ============================================================================
// Brick Size Parser
// ============================================================================

function parseBrickSize(brick: string): [number, number] {
    // Parse "2x4" -> [2, 4]
    const match = brick.match(/(\d+)x(\d+)/i);
    if (match) {
        return [parseInt(match[1], 10), parseInt(match[2], 10)];
    }
    // Default to 2x2 if parsing fails
    return [2, 2];
}

function getLegoColor(colorName: string): string {
    const normalized = colorName.toLowerCase().trim();
    return LEGO_COLORS[normalized] || LEGO_COLORS.default;
}

// ============================================================================
// LegoBrick Component - Single brick with studs
// ============================================================================

interface LegoBrickProps {
    brick: string;
    position: { x: number; y: number; z: number };
    color: string;
}

function LegoBrick({ brick, position, color }: LegoBrickProps): React.JSX.Element {
    const [widthStuds, lengthStuds] = parseBrickSize(brick);
    const hexColor = getLegoColor(color);

    // LEGO dimensions in mm
    const studSpacing = 8;
    const brickHeight = 9.6;
    const studRadius = 2.4;
    const studHeight = 1.8;
    const gap = 0.2; // Gap for visible edges

    const baseWidth = widthStuds * studSpacing - gap;
    const baseLength = lengthStuds * studSpacing - gap;

    // Generate stud positions
    const studs = useMemo(() => {
        const positions: [number, number, number][] = [];
        for (let x = 0; x < widthStuds; x++) {
            for (let y = 0; y < lengthStuds; y++) {
                // Stud centered on each grid cell, on top of brick
                const studX = (x - (widthStuds - 1) / 2) * studSpacing;
                const studY = (y - (lengthStuds - 1) / 2) * studSpacing;
                const studZ = brickHeight / 2 + studHeight / 2;
                positions.push([studX, studZ, studY]);
            }
        }
        return positions;
    }, [widthStuds, lengthStuds]);

    // Position the brick group - note: Three.js uses Y-up, LEGO uses Z-up
    // So we swap Y and Z: LEGO(x, y, z) -> Three.js(x, z, y)
    const groupPosition: [number, number, number] = [
        position.x,
        position.z + brickHeight / 2, // Center the brick at this height
        position.y,
    ];

    return (
        <group position={groupPosition}>
            {/* Base brick block */}
            <mesh castShadow receiveShadow>
                <boxGeometry args={[baseWidth, brickHeight, baseLength]} />
                <meshStandardMaterial color={hexColor} roughness={0.3} metalness={0.1} />
            </mesh>

            {/* Studs on top */}
            {studs.map((pos, i) => (
                <mesh key={i} position={pos} castShadow>
                    <cylinderGeometry args={[studRadius, studRadius, studHeight, 16]} />
                    <meshStandardMaterial color={hexColor} roughness={0.3} metalness={0.1} />
                </mesh>
            ))}
        </group>
    );
}

// ============================================================================
// LegoBrickScene Component - Renders all bricks from build sequence
// ============================================================================

interface LegoBrickSceneProps {
    buildSequence: BrickPlacement[];
}

export function LegoBrickScene({ buildSequence }: LegoBrickSceneProps): React.JSX.Element {
    const bounds = useBounds();

    // Auto-frame the model after initial render
    React.useEffect(() => {
        if (bounds && buildSequence.length > 0) {
            const timeout = setTimeout(() => {
                bounds.refresh().fit().clip();
            }, 100);
            return () => clearTimeout(timeout);
        }
        return undefined;
    }, [bounds, buildSequence.length]);

    // Calculate model center for proper centering
    const modelCenter = useMemo(() => {
        if (buildSequence.length === 0) return { x: 0, y: 0, z: 0 };

        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;
        let minZ = Infinity, maxZ = -Infinity;

        for (const brick of buildSequence) {
            const [w, l] = parseBrickSize(brick.brick);
            const halfW = (w * 8) / 2;
            const halfL = (l * 8) / 2;

            minX = Math.min(minX, brick.position.x - halfW);
            maxX = Math.max(maxX, brick.position.x + halfW);
            minY = Math.min(minY, brick.position.y - halfL);
            maxY = Math.max(maxY, brick.position.y + halfL);
            minZ = Math.min(minZ, brick.position.z);
            maxZ = Math.max(maxZ, brick.position.z + 9.6);
        }

        return {
            x: (minX + maxX) / 2,
            y: (minY + maxY) / 2,
            z: (minZ + maxZ) / 2,
        };
    }, [buildSequence]);

    return (
        <group position={[-modelCenter.x, -modelCenter.z, -modelCenter.y]}>
            {buildSequence.map((placement, index) => (
                <LegoBrick
                    key={`brick-${index}-${placement.step}`}
                    brick={placement.brick}
                    position={placement.position}
                    color={placement.color}
                />
            ))}
        </group>
    );
}

export default LegoBrickScene;
