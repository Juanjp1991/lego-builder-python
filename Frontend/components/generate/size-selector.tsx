"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { MODEL_SIZE_SPECS, type ModelSize } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Box, Layers, MousePointer2 } from "lucide-react";

interface SizeSelectorProps {
    selectedSize: ModelSize;
    onSizeChange: (size: ModelSize) => void;
    disabled?: boolean;
}

/**
 * Component for selecting LEGO model size tiers.
 * Displays tiers from 'tiny' to 'epic' with brick and layer counts.
 */
export function SizeSelector({
    selectedSize,
    onSizeChange,
    disabled = false,
}: SizeSelectorProps): React.JSX.Element {
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <Label className="text-sm font-medium flex items-center gap-2">
                    <MousePointer2 className="size-4" />
                    Model Size
                </Label>
                <span className="text-xs text-muted-foreground italic">
                    Affects build time and detail
                </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                {(Object.entries(MODEL_SIZE_SPECS) as [Exclude<ModelSize, "custom">, any][]).map(
                    ([size, spec]) => (
                        <button
                            key={size}
                            type="button"
                            disabled={disabled}
                            onClick={() => onSizeChange(size as ModelSize)}
                            className={cn(
                                "flex flex-col items-center justify-center p-3 rounded-lg border-2 transition-all text-left",
                                selectedSize === size
                                    ? "border-accent bg-accent/5 ring-1 ring-accent"
                                    : "border-muted bg-transparent hover:border-muted-foreground/50",
                                disabled && "opacity-50 cursor-not-allowed"
                            )}
                        >
                            <span className={cn(
                                "text-sm font-bold mb-1",
                                selectedSize === size ? "text-accent" : "text-foreground"
                            )}>
                                {spec.displayName}
                            </span>

                            <div className="flex flex-col gap-1 w-full">
                                <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                                    <Box className="size-3 shrink-0" />
                                    <span>{spec.minBricks}-{spec.maxBricks} bricks</span>
                                </div>
                                <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                                    <Layers className="size-3 shrink-0" />
                                    <span>{spec.minLayers}-{spec.maxLayers} layers</span>
                                </div>
                            </div>
                        </button>
                    )
                )}
            </div>

            {/* Custom size option (to be implemented with dialog/inputs if needed) */}
            {selectedSize === "custom" && (
                <div className="p-3 bg-muted/30 rounded-lg border border-dashed border-muted-foreground/30 text-center">
                    <p className="text-xs text-muted-foreground">
                        Custom size configuration is currently managed in Advanced settings.
                    </p>
                </div>
            )}
        </div>
    );
}
