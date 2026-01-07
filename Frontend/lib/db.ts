/**
 * IndexedDB database schema using Dexie.js for the LEGO Builder app.
 * Manages local storage for bricks, builds, templates, preferences, and generation cache.
 */

import Dexie, { type Table } from "dexie";
import type {
    Brick,
    Build,
    Template,
    UserPreference,
    GenerationCacheEntry,
} from "@/lib/types";

/**
 * LEGO Builder IndexedDB database.
 * Version 1: Initial schema with 5 tables.
 */
export class LegoDatabase extends Dexie {
    // Table declarations with TypeScript types
    bricks!: Table<Brick>;
    builds!: Table<Build>;
    templates!: Table<Template>;
    userPreferences!: Table<UserPreference>;
    generationCache!: Table<GenerationCacheEntry>;

    constructor() {
        super("LegoBuilderDB");

        // Define version 1 schema
        this.version(1).stores({
            // Bricks table: auto-increment ID, indexed on type, color, and createdAt
            bricks: "++id, type, color, createdAt",

            // Builds table: auto-increment ID, indexed on name, createdAt, and completedAt
            builds: "++id, name, createdAt, completedAt",

            // Templates table: auto-increment ID, indexed on category and name
            templates: "++id, category, name",

            // User preferences: auto-increment ID, unique index on key
            userPreferences: "++id, &key",

            // Generation cache: auto-increment ID, indexed on expiresAt (for TTL cleanup) and prompt (for deduplication)
            generationCache: "++id, expiresAt, prompt",
        });
    }
}

// Export singleton database instance
export const db = new LegoDatabase();
