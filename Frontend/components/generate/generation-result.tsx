"use client";

/**
 * Generation result component for displaying completed LEGO models.
 * Shows 3D viewer placeholder, model metadata, and action buttons.
 */

import React from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useGenerationStore } from "@/lib/stores/useGenerationStore";
import {
  RotateCcw,
  Play,
  Pencil,
  Download,
  ExternalLink,
  Blocks,
} from "lucide-react";

interface GenerationResultProps {
  onRegenerate: () => void;
  onStartBuilding: () => void;
  onModify: () => void;
}

export function GenerationResult({
  onRegenerate,
  onStartBuilding,
  onModify,
}: GenerationResultProps): React.JSX.Element {
  const { model, prompt, retryCount, maxRetries } = useGenerationStore();

  if (!model) {
    return <></>;
  }

  const remainingRetries = maxRetries - retryCount;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full max-w-2xl mx-auto"
    >
      <Card className="overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-heading">Your LEGO Model</CardTitle>
            <span className="text-sm text-muted-foreground">
              &ldquo;{prompt}&rdquo;
            </span>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* 3D Viewer Placeholder - Story 2.3 will implement actual viewer */}
          <div className="relative aspect-square bg-muted rounded-lg overflow-hidden">
            <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
              <Blocks className="size-16 mb-4" />
              <p className="text-sm font-medium">3D Model Preview</p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                (Viewer coming in Story 2.3)
              </p>
            </div>

            {/* Model URL badge */}
            <div className="absolute bottom-3 left-3 right-3">
              <div className="bg-background/90 backdrop-blur-sm rounded-md p-2 text-xs">
                <div className="flex items-center gap-2">
                  <ExternalLink className="size-3 flex-shrink-0" />
                  <span className="truncate font-mono">{model.modelUrl}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Model Metadata */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 rounded-lg bg-muted">
              <p className="text-xs text-muted-foreground">Estimated Bricks</p>
              <p className="text-2xl font-bold font-mono">
                {model.brickCount ?? "—"}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-muted">
              <p className="text-xs text-muted-foreground">Task ID</p>
              <p className="text-sm font-mono truncate" title={model.taskId}>{model.taskId}</p>
            </div>
          </div>

          {/* Download Link - opens in same tab to trigger download */}
          <Button variant="outline" className="w-full" asChild>
            <a
              href={model.modelUrl}
              download="lego-model.stl"
              rel="noopener noreferrer"
              aria-label="Download STL file for your LEGO model"
            >
              <Download className="size-4 mr-2" />
              Download STL File
            </a>
          </Button>
        </CardContent>

        <CardFooter className="flex flex-col gap-3 pt-4 border-t">
          {/* Primary Action */}
          <Button
            onClick={onStartBuilding}
            className="w-full bg-accent text-accent-foreground hover:bg-accent/90"
            size="lg"
            aria-label="Start building your LEGO model with step-by-step instructions"
          >
            <Play className="size-5 mr-2" />
            Start Building
          </Button>

          {/* Secondary Actions */}
          <div className="flex gap-2 w-full">
            <Button
              onClick={onRegenerate}
              variant="outline"
              className="flex-1"
              disabled={remainingRetries <= 0}
              aria-label={remainingRetries > 0 ? `Regenerate model, ${remainingRetries} retries remaining` : "No retries remaining"}
            >
              <RotateCcw className="size-4 mr-2" />
              {remainingRetries > 0 ? (
                <>Regenerate ({remainingRetries} left)</>
              ) : (
                <>No retries left</>
              )}
            </Button>
            <Button
              onClick={onModify}
              variant="outline"
              className="flex-1"
              aria-label="Modify your LEGO model design"
            >
              <Pencil className="size-4 mr-2" />
              Modify
            </Button>
          </div>

          {/* Retry info */}
          {remainingRetries <= 0 && (
            <p className="text-xs text-muted-foreground text-center">
              You&apos;ve used all 3 free retries. Click &quot;Start Fresh&quot; for a new design.
            </p>
          )}
        </CardFooter>
      </Card>
    </motion.div>
  );
}
