const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

import type { Template } from "@/lib/types";

// --- A2A Models ---

export enum TaskState {
  UNSPECIFIED = "TASK_STATE_UNSPECIFIED",
  SUBMITTED = "TASK_STATE_SUBMITTED",
  WORKING = "TASK_STATE_WORKING",
  COMPLETED = "TASK_STATE_COMPLETED",
  FAILED = "TASK_STATE_FAILED",
  CANCELLED = "TASK_STATE_CANCELLED",
  INPUT_REQUIRED = "TASK_STATE_INPUT_REQUIRED",
  REJECTED = "TASK_STATE_REJECTED",
  AUTH_REQUIRED = "TASK_STATE_AUTH_REQUIRED",
}

export enum Role {
  UNSPECIFIED = "ROLE_UNSPECIFIED",
  USER = "ROLE_USER",
  AGENT = "ROLE_AGENT",
}

export interface FilePart {
  fileWithUri?: string;
  fileWithBytes?: string; // base64 encoded
  mediaType?: string;
  name?: string;
}

export interface Part {
  text?: string;
  file?: FilePart;
  data?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface Message {
  messageId?: string;
  contextId?: string;
  taskId?: string;
  role: Role;
  parts: Part[];
  metadata?: Record<string, unknown>;
  extensions?: string;
  referenceTaskIds?: string;
}

export interface TaskStatus {
  state: TaskState;
  message?: Message;
  timestamp?: string;
}

export interface Artifact {
  parts: Part[];
}

export interface Task {
  id: string;
  contextId?: string;
  status: TaskStatus;
  artifacts?: Artifact;
  history: Message[];
  metadata?: Record<string, unknown>;
}

export interface SendMessageRequest {
  message: Message;
  configuration?: {
    acceptedOutputModes?: string[];
  };
}

export interface SendMessageResponse {
  task: Task;
}

export interface GetTaskResponse {
  task: Task;
}

// --- API Functions ---

/**
 * Sends a message to the agent to start a task.
 *
 * @param prompt - The text prompt for the agent.
 * @param contextId - Optional context ID for the conversation.
 * @returns A promise that resolves to the created task.
 */
export async function sendMessage(prompt: string, contextId?: string): Promise<Task> {
  const message: Message = {
    role: Role.USER,
    contextId: contextId || crypto.randomUUID(),
    parts: [{ text: prompt }],
  };

  const requestBody: SendMessageRequest = {
    message,
  };

  const response = await fetch(`${API_BASE_URL}/v1/message:send`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to send message");
  }

  const data: SendMessageResponse = await response.json();
  return data.task;
}

/**
 * Retrieves the current status of a task.
 *
 * @param taskId - The ID of the task to retrieve.
 * @returns A promise that resolves to the task object.
 */
export async function getTask(taskId: string): Promise<Task> {
  const response = await fetch(`${API_BASE_URL}/v1/tasks/${taskId}`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to get task");
  }

  const data: GetTaskResponse = await response.json();
  return data.task;
}

/**
 * Polls a task until it reaches a terminal state (COMPLETED, FAILED, CANCELLED, REJECTED).
 *
 * @param taskId - The ID of the task to poll.
 * @param intervalMs - The polling interval in milliseconds.
 * @returns A promise that resolves to the completed task.
 */
export async function pollTask(taskId: string, intervalMs: number = 1000): Promise<Task> {
  while (true) {
    const task = await getTask(taskId);
    const state = task.status.state;

    if (
      state === TaskState.COMPLETED ||
      state === TaskState.FAILED ||
      state === TaskState.CANCELLED ||
      state === TaskState.REJECTED
    ) {
      return task;
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

/**
 * Helper to construct a full URL for a file path returned by the API.
 */
export function getFileUrl(path: string | undefined): string | undefined {
  if (!path) return undefined;
  if (path.startsWith("http")) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

// ===============================================
// LEGO-SPECIFIC API FUNCTIONS
// ===============================================

import type {
  Brick,
  GenerateOptions,
  GeneratedModel,
  ScanOptions,
  ScannedBricks,
  TemplateList,
  StructuralAnalysis,
  StructuralIssue,
  BuildabilityMetadata,
  BrickPlacement,
} from "@/lib/types";

// ===============================================
// HELPER FUNCTIONS
// ===============================================

/**
 * Raw structural analysis from backend (snake_case).
 */
interface RawStructuralAnalysis {
  buildability_score?: number;
  issues?: Array<{
    type: string;
    severity: string;
    description: string;
    location?: string;
  }>;
  recommendations?: string[];
}

/**
 * Parses structural analysis from backend response (snake_case to camelCase).
 * Returns undefined if no structural analysis found.
 */
function parseStructuralAnalysis(
  metadata?: Record<string, unknown>,
  artifactParts?: Part[]
): StructuralAnalysis | undefined {
  // Try metadata first (primary source)
  let rawAnalysis: RawStructuralAnalysis | undefined = metadata?.structural_analysis as RawStructuralAnalysis | undefined;

  // Try artifact data parts if not in metadata
  if (!rawAnalysis && artifactParts) {
    const dataPart = artifactParts.find(
      (p) => p.data && (p.data as Record<string, unknown>).structural_analysis
    );
    if (dataPart?.data) {
      rawAnalysis = (dataPart.data as Record<string, unknown>).structural_analysis as RawStructuralAnalysis;
    }
  }

  // If no raw analysis found, return undefined
  if (!rawAnalysis || typeof rawAnalysis.buildability_score !== "number") {
    return undefined;
  }

  // Convert snake_case to camelCase
  return {
    buildabilityScore: rawAnalysis.buildability_score,
    issues: (rawAnalysis.issues || []).map((issue) => ({
      type: issue.type as StructuralIssue["type"],
      severity: issue.severity as StructuralIssue["severity"],
      description: issue.description,
      location: issue.location,
    })),
    recommendations: rawAnalysis.recommendations || [],
  };
}

/**
 * Raw buildability data from backend (snake_case).
 */
interface RawBuildability {
  score?: number;
  valid?: boolean;
  layer_count?: number;
  issues?: string[];
  recommendations?: string[];
  estimated_build_time_minutes?: number;
  build_sequence?: Array<{
    step: number;
    brick: string;
    color: string;
    position: { x: number; y: number; z: number };
  }>;
}

/**
 * Parses buildability metadata from backend response (snake_case to camelCase).
 * Returns undefined if no buildability data found.
 */
function parseBuildability(
  metadata?: Record<string, unknown>,
  artifactParts?: Part[]
): BuildabilityMetadata | undefined {
  // Try metadata first (primary source)
  let raw: RawBuildability | undefined = metadata?.buildability as RawBuildability | undefined;

  // Try artifact data parts if not in metadata
  if (!raw && artifactParts) {
    const dataPart = artifactParts.find(
      (p) => p.data && (p.data as Record<string, unknown>).buildability
    );
    if (dataPart?.data) {
      raw = (dataPart.data as Record<string, unknown>).buildability as RawBuildability;
    }

    // Also try build_sequence directly in data parts
    if (!raw) {
      const seqPart = artifactParts.find(
        (p) => p.data && (p.data as Record<string, unknown>).build_sequence
      );
      if (seqPart?.data) {
        const data = seqPart.data as Record<string, unknown>;
        raw = {
          score: data.score as number | undefined,
          valid: data.valid as boolean | undefined,
          layer_count: data.layer_count as number | undefined,
          issues: data.issues as string[] | undefined,
          recommendations: data.recommendations as string[] | undefined,
          estimated_build_time_minutes: data.estimated_build_time_minutes as number | undefined,
          build_sequence: data.build_sequence as RawBuildability["build_sequence"],
        };
      }
    }
  }

  // If no raw data found, return undefined
  if (!raw || !raw.build_sequence || raw.build_sequence.length === 0) {
    return undefined;
  }

  // Convert snake_case to camelCase
  return {
    score: raw.score ?? 0,
    valid: raw.valid ?? false,
    layerCount: raw.layer_count ?? 0,
    issues: raw.issues ?? [],
    recommendations: raw.recommendations ?? [],
    estimatedBuildTimeMinutes: raw.estimated_build_time_minutes ?? 0,
    buildSequence: raw.build_sequence.map((b) => ({
      step: b.step,
      brick: b.brick,
      color: b.color,
      position: b.position,
    })),
  };
}

/**
 * Sends a message with images using multipart/form-data.
 * Used for image-to-model generation.
 *
 * @param prompt - The text prompt for the agent.
 * @param images - Array of image files to include.
 * @param inventory - User's brick inventory (optional).
 * @param options - Generation options.
 * @returns A promise that resolves to the created task.
 */
async function sendMessageWithImages(
  prompt: string,
  images: File[],
  inventory: Brick[] = [],
  options?: GenerateOptions
): Promise<Task> {
  const formData = new FormData();
  formData.append("type", "image");
  formData.append("prompt", prompt);

  // Add images with indexed keys
  images.forEach((img, i) => formData.append(`image_${i}`, img));

  // Add inventory and options as JSON
  formData.append("inventory", JSON.stringify(inventory));
  if (options) {
    formData.append("options", JSON.stringify(options));
  }

  // Add context ID for tracking
  formData.append("contextId", crypto.randomUUID());

  // Send multipart request (browser sets Content-Type with boundary)
  const response = await fetch(`${API_BASE_URL}/v1/message:send`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to send message with images");
  }

  const data: SendMessageResponse = await response.json();
  return data.task;
}

/**
 * Generates a LEGO model using AI based on text prompt or images.
 * Follows A2A protocol: sendMessage → pollTask → extract artifacts.
 *
 * @param type - Generation type: 'text' for text-to-model, 'image' for image-to-model
 * @param prompt - User prompt describing the desired model
 * @param images - Array of image files for image-to-model (empty for text-to-model)
 * @param inventory - User's brick inventory (optional, for inventory-matching)
 * @param options - Additional generation options (complexity, size, etc.)
 * @returns Promise resolving to generated model with STL URL and metadata
 */
export async function generateLegoModel(
  type: "text" | "image",
  prompt: string,
  images: File[] = [],
  inventory: Brick[] = [],
  options?: GenerateOptions
): Promise<GeneratedModel> {
  let task: Task;

  // Choose request method based on type
  if (type === "image" && images.length > 0) {
    // Use FormData multipart request for images
    task = await sendMessageWithImages(prompt, images, inventory, options);
  } else {
    // Use JSON request for text-only
    // Build prompt message including inventory info if provided
    let fullPrompt = prompt;
    if (inventory.length > 0 && options?.useInventory) {
      const inventorySummary = inventory
        .map((b) => `${b.quantity}x ${b.color} ${b.type}`)
        .join(", ");
      fullPrompt += `\n\nUser's brick inventory: ${inventorySummary}`;
    }

    // Add options to prompt
    if (options) {
      fullPrompt += `\n\nGeneration options: ${JSON.stringify(options)}`;
    }

    // Send message to start generation task
    task = await sendMessage(fullPrompt);
  }

  // Poll until task completes
  const completedTask = await pollTask(task.id);

  // Check task state
  if (completedTask.status.state !== TaskState.COMPLETED) {
    throw new Error(`LEGO model generation failed: ${completedTask.status.state}`);
  }

  // Extract STL file from task artifacts
  const stlPart = completedTask.artifacts?.parts?.find(
    (p) => p.file?.mediaType === "model/stl" || p.file?.fileWithUri?.endsWith(".stl")
  );

  if (!stlPart?.file?.fileWithUri) {
    throw new Error("No STL file found in generation response");
  }

  const modelUrl = getFileUrl(stlPart.file.fileWithUri)!;

  // Extract brick count from metadata if available
  const brickCount = completedTask.metadata?.brickCount as number | undefined;

  // Parse structural analysis from metadata or artifact data parts
  const structuralAnalysis = parseStructuralAnalysis(
    completedTask.metadata as Record<string, unknown> | undefined,
    completedTask.artifacts?.parts
  );

  // Parse buildability metadata (for colored brick rendering)
  const buildability = parseBuildability(
    completedTask.metadata as Record<string, unknown> | undefined,
    completedTask.artifacts?.parts
  );

  return {
    taskId: completedTask.id,
    modelUrl,
    brickCount,
    structuralAnalysis,
    buildability,
  };
}

/**
 * Scans an image to detect and identify LEGO bricks using AI vision.
 * Follows A2A protocol: sendMessage → pollTask → extract brick list.
 *
 * @param imageFile - Image file containing LEGO bricks to scan
 * @param options - Scan options (auto-detect, color correction, etc.)
 * @returns Promise resolving to detected bricks with confidence score
 */
export async function scanBricks(
  imageFile: File,
  options?: ScanOptions
): Promise<ScannedBricks> {
  // TODO: Implement image upload and scanning
  // For MVP, this is a placeholder following A2A pattern
  const prompt = `Scan this image and identify LEGO bricks. ${JSON.stringify(options || {})}`;

  // Send message to start scanning task
  const task = await sendMessage(prompt);

  // Poll until task completes
  const completedTask = await pollTask(task.id);

  // Check task state
  if (completedTask.status.state !== TaskState.COMPLETED) {
    throw new Error(`Brick scanning failed: ${completedTask.status.state}`);
  }

  // Extract brick data from response (format TBD by backend)
  const brickData = completedTask.metadata?.bricks as Brick[] | undefined;
  const confidence = (completedTask.metadata?.confidence as number) || 0.0;

  return {
    taskId: completedTask.id,
    bricks: brickData || [],
    confidence,
  };
}

/**
 * Fetches pre-built LEGO templates from the backend.
 * Follows A2A protocol: sendMessage → pollTask → extract template list.
 *
 * @param category - Template category filter (e.g., 'animals', 'vehicles', 'buildings')
 * @returns Promise resolving to list of templates
 */
export async function getTemplates(category?: string): Promise<TemplateList> {
  // Build prompt for template fetching
  const prompt = category
    ? `Get LEGO templates for category: ${category}`
    : "Get all available LEGO templates";

  // Send message to start template fetch task
  const task = await sendMessage(prompt);

  // Poll until task completes
  const completedTask = await pollTask(task.id);

  // Check task state
  if (completedTask.status.state !== TaskState.COMPLETED) {
    throw new Error(`Template fetching failed: ${completedTask.status.state}`);
  }

  // Extract template data from response (format TBD by backend)
  const templates = (completedTask.metadata?.templates as Template[]) || [];
  const totalCount = (completedTask.metadata?.totalCount as number) || templates.length;

  return {
    templates,
    totalCount,
  };
}
