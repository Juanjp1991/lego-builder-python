/**
 * Unit tests for LEGO-specific API client functions.
 * Mocks A2A protocol functions for testing.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
    generateLegoModel,
    scanBricks,
    getTemplates,
    TaskState,
} from "@/lib/api";
import * as api from "@/lib/api";

// Mock the A2A protocol functions
vi.mock("@/lib/api", async () => {
    const actual = await vi.importActual("@/lib/api");
    return {
        ...actual,
        sendMessage: vi.fn(),
        pollTask: vi.fn(),
        getFileUrl: vi.fn((path) => `http://localhost:8001${path}`),
    };
});

describe("LEGO API Functions", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe("generateLegoModel", () => {
        it("should generate a model from text prompt", async () => {
            const mockTask = { id: "task-123", status: { state: TaskState.WORKING } };
            const mockCompletedTask = {
                id: "task-123",
                status: { state: TaskState.COMPLETED },
                artifacts: {
                    parts: [
                        {
                            file: {
                                fileWithUri: "/download/model.stl",
                                mediaType: "model/stl",
                            },
                        },
                    ],
                },
                metadata: { brickCount: 150 },
            };

            vi.mocked(api.sendMessage).mockResolvedValue(mockTask as Partial<Task> as Task);
            vi.mocked(api.pollTask).mockResolvedValue(mockCompletedTask as Partial<Task> as Task);

            const result = await generateLegoModel("text", "a small dragon", [], [], {
                complexity: "medium",
            });

            expect(api.sendMessage).toHaveBeenCalledWith(
                expect.stringContaining("dragon")
            );
            expect(api.pollTask).toHaveBeenCalledWith("task-123");
            expect(result.taskId).toBe("task-123");
            expect(result.modelUrl).toContain("model.stl");
            expect(result.brickCount).toBe(150);
        });

        it("should include inventory in prompt when provided", async () => {
            const mockTask = { id: "task-456" };
            const mockCompletedTask = {
                id: "task-456",
                status: { state: TaskState.COMPLETED },
                artifacts: {
                    parts: [{ file: { fileWithUri: "/model.stl" } }],
                },
            };

            vi.mocked(api.sendMessage).mockResolvedValue(mockTask as Partial<Task> as Task);
            vi.mocked(api.pollTask).mockResolvedValue(mockCompletedTask as Partial<Task> as Task);

            const inventory = [
                { type: "2x4", color: "red", quantity: 10, createdAt: new Date() },
                { type: "2x2", color: "blue", quantity: 5, createdAt: new Date() },
            ];

            await generateLegoModel("text", "build something", [], inventory, {
                useInventory: true,
            });

            const sentPrompt = vi.mocked(api.sendMessage).mock.calls[0][0];
            expect(sentPrompt).toContain("10x red 2x4");
            expect(sentPrompt).toContain("5x blue 2x2");
        });

        it("should throw error if generation fails", async () => {
            const mockTask = { id: "task-789" };
            const mockFailedTask = {
                id: "task-789",
                status: { state: TaskState.FAILED },
            };

            vi.mocked(api.sendMessage).mockResolvedValue(mockTask as Partial<Task> as Task);
            vi.mocked(api.pollTask).mockResolvedValue(mockFailedTask as Partial<Task> as Task);

            await expect(
                generateLegoModel("text", "test", [], [], {})
            ).rejects.toThrow("generation failed");
        });

        it("should throw error if no STL file in response", async () => {
            const mockTask = { id: "task-999" };
            const mockCompletedTask = {
                id: "task-999",
                status: { state: TaskState.COMPLETED },
                artifacts: { parts: [] }, // No STL file
            };

            vi.mocked(api.sendMessage).mockResolvedValue(mockTask as Partial<Task> as Task);
            vi.mocked(api.pollTask).mockResolvedValue(mockCompletedTask as Partial<Task> as Task);

            await expect(
                generateLegoModel("text", "test", [], [], {})
            ).rejects.toThrow("No STL file found");
        });
    });

    describe("scanBricks", () => {
        it("should scan an image and return detected bricks", async () => {
            const mockTask = { id: "scan-123" };
            const mockCompletedTask = {
                id: "scan-123",
                status: { state: TaskState.COMPLETED },
                metadata: {
                    bricks: [
                        { type: "2x4", color: "red", quantity: 1, createdAt: new Date() },
                        { type: "2x2", color: "blue", quantity: 2, createdAt: new Date() },
                    ],
                    confidence: 0.95,
                },
            };

            vi.mocked(api.sendMessage).mockResolvedValue(mockTask as Partial<Task> as Task);
            vi.mocked(api.pollTask).mockResolvedValue(mockCompletedTask as Partial<Task> as Task);

            const imageFile = new File(["fake"], "bricks.jpg", { type: "image/jpeg" });
            const result = await scanBricks(imageFile, { autoDetect: true });

            expect(result.taskId).toBe("scan-123");
            expect(result.bricks).toHaveLength(2);
            expect(result.confidence).toBe(0.95);
        });
    });

    describe("getTemplates", () => {
        it("should fetch templates without category filter", async () => {
            const mockTask = { id: "template-123" };
            const mockCompletedTask = {
                id: "template-123",
                status: { state: TaskState.COMPLETED },
                metadata: {
                    templates: [
                        { id: 1, category: "animals", name: "Dragon", modelData: "{}" },
                        { id: 2, category: "vehicles", name: "Car", modelData: "{}" },
                    ],
                    totalCount: 2,
                },
            };

            vi.mocked(api.sendMessage).mockResolvedValue(mockTask as Partial<Task> as Task);
            vi.mocked(api.pollTask).mockResolvedValue(mockCompletedTask as Partial<Task> as Task);

            const result = await getTemplates();

            expect(api.sendMessage).toHaveBeenCalledWith(
                expect.stringContaining("all available")
            );
            expect(result.templates).toHaveLength(2);
            expect(result.totalCount).toBe(2);
        });

        it("should fetch templates with category filter", async () => {
            const mockTask = { id: "template-456" };
            const mockCompletedTask = {
                id: "template-456",
                status: { state: TaskState.COMPLETED },
                metadata: {
                    templates: [{ id: 1, category: "animals", name: "Lion", modelData: "{}" }],
                    totalCount: 1,
                },
            };

            vi.mocked(api.sendMessage).mockResolvedValue(mockTask as Partial<Task> as Task);
            vi.mocked(api.pollTask).mockResolvedValue(mockCompletedTask as Partial<Task> as Task);

            const result = await getTemplates("animals");

            expect(api.sendMessage).toHaveBeenCalledWith(
                expect.stringContaining("animals")
            );
            expect(result.templates).toHaveLength(1);
        });
    });
});
