# Story 2.5: First-Build Guarantee & User Profiling

Status: done

## Story

As a user who has never completed a build,
I want the system to generate simpler models automatically,
So that my first experience is successful and builds my confidence.

## Acceptance Criteria

1. **Given** the user has never completed a build (checked via IndexedDB `userPreferences` table)
   **When** the user generates their first model (Story 2.1 or 2.2)
   **Then** the frontend reads `isFirstBuild` flag from `userPreferences` table (defaults to `true`)

2. **And** if `isFirstBuild === true`, the frontend sets `options.complexity = 'simple'` in the `generateLegoModel()` call

3. **And** the backend coder agent receives the complexity hint and generates a simpler model:
   - Fewer layers (max 5 layers)
   - Larger bricks (prefer 2x4, 2x3 over 1x1)
   - No tricky cantilevers or advanced techniques

4. **And** the UI shows a blue badge: "First-Build Mode - Simplified for success"

5. **And** user can tap "Advanced Mode" toggle to disable First-Build Guarantee for current generation

6. **And** when user completes their first build (Epic 5), `isFirstBuild` is set to `false` in `userPreferences`

7. **And** subsequent generations use normal complexity unless user is still learning

8. **And** a celebration modal appears after first build: "Your first creation! Advanced mode unlocked"

## Tasks / Subtasks

- [x] Task 1: Setup Dexie.js database with userPreferences table (AC: #1)
  - [x] Create `/Frontend/lib/db.ts` with Dexie.js schema
  - [x] Define `userPreferences` table with schema: `id, key, value`
  - [x] Create TypeScript interfaces: `UserPreference`, `UserPreferencesTable`
  - [x] Initialize database with default `isFirstBuild: true`
  - [x] Add unit tests for database initialization
  - [x] Export `db` instance and helper functions

- [x] Task 2: Create useFirstBuild custom hook (AC: #1, #6, #7)
  - [x] Create `/Frontend/lib/hooks/use-first-build.ts`
  - [x] Implement `useFirstBuild()` hook returning `{ isFirstBuild, setFirstBuildComplete, isLoading }`
  - [x] Hook reads from Dexie.js `userPreferences` table
  - [x] `setFirstBuildComplete()` sets `isFirstBuild = false` in database
  - [x] Handle loading state while checking database
  - [x] Add unit tests with mocked Dexie.js

- [x] Task 3: Update API client for complexity option (AC: #2, #3)
  - [x] Update `/Frontend/lib/lego-api.ts` `generateLegoModel()` function
  - [x] Add `complexity?: 'simple' | 'normal'` to options parameter
  - [x] Include complexity in A2A request body
  - [x] Update TypeScript types for generation options
  - [x] Add unit tests for complexity parameter

- [x] Task 4: Create FirstBuildBadge component (AC: #4)
  - [x] Create `/Frontend/components/generate/first-build-badge.tsx`
  - [x] Display blue badge: "First-Build Mode - Simplified for success"
  - [x] Use Shadcn/ui Badge component with blue styling
  - [x] Include info icon (lucide-react)
  - [x] Make badge clickable to show explanation modal
  - [x] Add aria-label for accessibility
  - [x] Add unit tests

- [x] Task 5: Create AdvancedModeToggle component (AC: #5)
  - [x] Create `/Frontend/components/generate/advanced-mode-toggle.tsx`
  - [x] Use Shadcn/ui Switch or Toggle component
  - [x] Label: "Advanced Mode" with description
  - [x] Toggle state stored in local component state (per-generation)
  - [x] Emit `onAdvancedModeChange(boolean)` callback
  - [x] Style with warning indicator when enabled for first-time users
  - [x] Add unit tests

- [x] Task 6: Integrate First-Build logic into generation flow (AC: #1, #2, #4, #5)
  - [x] Update `/Frontend/app/generate/page.tsx` to use `useFirstBuild()` hook
  - [x] Pass `complexity` option based on `isFirstBuild` state
  - [x] Respect AdvancedModeToggle override
  - [x] Display FirstBuildBadge when in first-build mode
  - [x] Position badge in generation input section
  - [x] Add integration tests

- [x] Task 7: Create FirstBuildCelebration modal (AC: #8)
  - [x] Create `/Frontend/components/generate/first-build-celebration.tsx`
  - [x] Use Shadcn/ui Dialog component
  - [x] Display: "Your first creation! Advanced mode unlocked"
  - [x] Include celebration icon/animation
  - [x] Show unlock badge graphic
  - [x] "Continue" button to dismiss
  - [x] Add unit tests

- [x] Task 8: Prepare integration point for Epic 5 completion (AC: #6)
  - [x] Export `setFirstBuildComplete()` from hook
  - [x] Document integration point for Epic 5 (build completion triggers this)
  - [x] Add placeholder comment in build completion flow
  - [x] Create utility function `markFirstBuildComplete()` in db.ts

- [x] Task 9: Add comprehensive tests (AC: all)
  - [x] Test `useFirstBuild` returns correct initial state
  - [x] Test database stores and retrieves `isFirstBuild` flag
  - [x] Test `complexity = 'simple'` is sent when `isFirstBuild === true`
  - [x] Test `complexity = 'normal'` when `isFirstBuild === false`
  - [x] Test AdvancedModeToggle overrides first-build mode
  - [x] Test FirstBuildBadge renders correctly
  - [x] Test FirstBuildCelebration modal appears

## Dev Notes

### Key Architecture Decisions

1. **Dexie.js for IndexedDB**: This is the first story introducing IndexedDB storage. Must follow architecture patterns for `userPreferences` table.

2. **Custom Hook Pattern**: `useFirstBuild()` encapsulates all first-build logic, making it reusable across components.

3. **Per-Generation Override**: Advanced Mode toggle is per-generation (not persistent). First-time users can try advanced once without permanently switching.

4. **Deferred Completion**: The `setFirstBuildComplete()` is called by Epic 5 when a build is finished - this story only creates the hook and integration point.

5. **Progressive Disclosure**: Blue badge is informative, not alarming. Makes users feel guided, not restricted.

### Previous Story Learnings (2.4)

From Story 2.4 (Free Retry Mechanism & Structural Feedback):
- **Component Pattern**: Badge + Modal pattern works well for informative features
- **API Extension**: Extend `generateLegoModel()` with new options parameter
- **Test Pattern**: Mock Dexie.js/database in tests, use `vi.mock()`
- **Zustand Integration**: Store patterns already established, but this uses Dexie.js directly
- **File Organization**: Components in `/Frontend/components/generate/`
- **Badge Styling**: Use Tailwind color classes (`bg-blue-100 text-blue-800` for blue badges)

### Technology Stack (CRITICAL - Use Exact Versions)

From `/Frontend/package.json` and architecture:
- **Dexie.js**: `dexie@4.2.1` - IndexedDB wrapper (ADD TO DEPENDENCIES)
- **dexie-react-hooks**: `dexie-react-hooks@4.2.0` - React integration (ADD TO DEPENDENCIES)
- **React**: `react@19.2.1`
- **Zustand**: `zustand@5.x` (for other stores, this feature uses Dexie.js directly)
- **Shadcn/ui**: Badge, Dialog, Switch components
- **Lucide React**: `lucide-react@0.554.0` for icons
- **TypeScript**: 5.x with strict mode

**IMPORTANT**: Dexie.js needs to be installed first:
```bash
cd Frontend && pnpm add dexie@4.2.1 dexie-react-hooks@4.2.0
```

### Database Schema (Dexie.js)

```typescript
// /Frontend/lib/db.ts
import Dexie, { type EntityTable } from 'dexie';

export interface UserPreference {
  id?: number;
  key: string;
  value: string | boolean | number;
}

export class LegoBuilderDB extends Dexie {
  userPreferences!: EntityTable<UserPreference, 'id'>;

  constructor() {
    super('LegoBuilderDB');

    // Schema version 1: userPreferences table only
    // Future stories will add: bricks, builds, templates, generationCache
    this.version(1).stores({
      userPreferences: '++id, key'
    });
  }
}

export const db = new LegoBuilderDB();

// Helper functions
export async function getUserPreference<T>(key: string, defaultValue: T): Promise<T> {
  const pref = await db.userPreferences.where('key').equals(key).first();
  return pref ? (pref.value as T) : defaultValue;
}

export async function setUserPreference<T>(key: string, value: T): Promise<void> {
  const existing = await db.userPreferences.where('key').equals(key).first();
  if (existing) {
    await db.userPreferences.update(existing.id!, { value });
  } else {
    await db.userPreferences.add({ key, value });
  }
}

export async function markFirstBuildComplete(): Promise<void> {
  await setUserPreference('isFirstBuild', false);
}
```

### useFirstBuild Hook Pattern

```typescript
// /Frontend/lib/hooks/use-first-build.ts
"use client";

import { useState, useEffect } from 'react';
import { getUserPreference, setUserPreference } from '@/lib/db';

interface UseFirstBuildReturn {
  isFirstBuild: boolean;
  isLoading: boolean;
  setFirstBuildComplete: () => Promise<void>;
}

export function useFirstBuild(): UseFirstBuildReturn {
  const [isFirstBuild, setIsFirstBuild] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function checkFirstBuild(): Promise<void> {
      try {
        const value = await getUserPreference<boolean>('isFirstBuild', true);
        setIsFirstBuild(value);
      } catch (error) {
        console.error('Failed to check first build status:', error);
        setIsFirstBuild(true); // Default to first-build mode on error
      } finally {
        setIsLoading(false);
      }
    }
    checkFirstBuild();
  }, []);

  const setFirstBuildComplete = async (): Promise<void> => {
    await setUserPreference('isFirstBuild', false);
    setIsFirstBuild(false);
  };

  return { isFirstBuild, isLoading, setFirstBuildComplete };
}
```

### API Client Extension

```typescript
// Update /Frontend/lib/lego-api.ts

export interface GenerationOptions {
  complexity?: 'simple' | 'normal';
  // ... existing options
}

export async function generateLegoModel(
  type: 'text' | 'image',
  prompt: string,
  images: File[],
  inventory: Brick[],
  options?: GenerationOptions
): Promise<GeneratedModel> {
  const payload = {
    type,
    prompt,
    inventory,
    complexity: options?.complexity || 'normal',
    // ... other fields
  };

  // ... existing implementation
}
```

### FirstBuildBadge Component Pattern

```typescript
// /Frontend/components/generate/first-build-badge.tsx
"use client";

import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Info, Sparkles } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export function FirstBuildBadge(): React.JSX.Element {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <Badge
        className={cn(
          "cursor-pointer",
          "bg-blue-100 text-blue-800 hover:bg-blue-200"
        )}
        onClick={() => setIsModalOpen(true)}
        role="button"
        aria-label="First-Build Mode active. Click for more information."
      >
        <Sparkles className="size-3 mr-1" />
        First-Build Mode
      </Badge>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>First-Build Mode</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-muted-foreground">
              We're generating a simpler design to help ensure your first build is successful!
            </p>
            <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
              <li>Fewer layers (max 5) for easier assembly</li>
              <li>Larger bricks that are easier to handle</li>
              <li>Stable structures without tricky overhangs</li>
            </ul>
            <p className="text-sm">
              After you complete your first build, you'll unlock Advanced Mode for more complex designs.
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

### AdvancedModeToggle Component Pattern

```typescript
// /Frontend/components/generate/advanced-mode-toggle.tsx
"use client";

import React from "react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AdvancedModeToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  isFirstBuild: boolean;
}

export function AdvancedModeToggle({
  enabled,
  onChange,
  isFirstBuild,
}: AdvancedModeToggleProps): React.JSX.Element {
  return (
    <div className="flex items-center gap-3">
      <Switch
        id="advanced-mode"
        checked={enabled}
        onCheckedChange={onChange}
      />
      <div className="flex flex-col">
        <Label htmlFor="advanced-mode" className="text-sm font-medium">
          Advanced Mode
        </Label>
        {isFirstBuild && enabled && (
          <span className="flex items-center gap-1 text-xs text-amber-600">
            <AlertTriangle className="size-3" />
            Complex models may be harder to build
          </span>
        )}
      </div>
    </div>
  );
}
```

### FirstBuildCelebration Modal Pattern

```typescript
// /Frontend/components/generate/first-build-celebration.tsx
"use client";

import React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Trophy, Sparkles } from "lucide-react";

interface FirstBuildCelebrationProps {
  open: boolean;
  onClose: () => void;
}

export function FirstBuildCelebration({
  open,
  onClose,
}: FirstBuildCelebrationProps): React.JSX.Element {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="text-center">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-center gap-2 text-2xl">
            <Trophy className="size-8 text-yellow-500" />
            Your First Creation!
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <p className="text-lg text-muted-foreground">
            Congratulations on completing your first Lego build!
          </p>
          <div className="flex items-center justify-center gap-2 text-blue-600">
            <Sparkles className="size-5" />
            <span className="font-semibold">Advanced Mode Unlocked</span>
          </div>
          <p className="text-sm text-muted-foreground">
            You can now generate more complex and challenging designs.
          </p>
        </div>
        <Button onClick={onClose} className="w-full">
          Continue
        </Button>
      </DialogContent>
    </Dialog>
  );
}
```

### File Locations

**New Files:**
- `/Frontend/lib/db.ts` - Dexie.js database schema and helpers
- `/Frontend/lib/db.test.ts` - Database tests
- `/Frontend/lib/hooks/use-first-build.ts` - Custom hook
- `/Frontend/lib/hooks/use-first-build.test.ts` - Hook tests
- `/Frontend/components/generate/first-build-badge.tsx` - Badge component
- `/Frontend/components/generate/first-build-badge.test.tsx` - Badge tests
- `/Frontend/components/generate/advanced-mode-toggle.tsx` - Toggle component
- `/Frontend/components/generate/advanced-mode-toggle.test.tsx` - Toggle tests
- `/Frontend/components/generate/first-build-celebration.tsx` - Celebration modal
- `/Frontend/components/generate/first-build-celebration.test.tsx` - Modal tests

**Modified Files:**
- `/Frontend/package.json` - Add dexie and dexie-react-hooks dependencies
- `/Frontend/lib/lego-api.ts` - Add complexity option to generateLegoModel
- `/Frontend/lib/lego-api.test.ts` - Add tests for complexity parameter
- `/Frontend/lib/types.ts` - Add GenerationOptions interface if not exists
- `/Frontend/app/generate/page.tsx` - Integrate useFirstBuild hook and components

### Existing Code to Leverage

From `/Frontend/lib/lego-api.ts`:
```typescript
// Existing function to extend:
export async function generateLegoModel(
  type: 'text' | 'image',
  prompt: string,
  images: File[],
  inventory: Brick[],
  options?: GenerationOptions
): Promise<GeneratedModel>
```

From `/Frontend/components/ui/badge.tsx` (created in Story 2.4):
```typescript
// Already installed - use for FirstBuildBadge
import { Badge } from "@/components/ui/badge";
```

From `/Frontend/components/ui/dialog.tsx`:
```typescript
// Shadcn/ui Dialog - check if installed, if not run:
// npx shadcn@latest add dialog switch label
```

### Design System Integration

Colors (from design spec):
- Blue (First-Build Mode): `bg-blue-100 text-blue-800` (Tailwind)
- Amber (warning): `bg-amber-100 text-amber-800` (Tailwind)
- Yellow (celebration): `text-yellow-500` for trophy icon

Icons (Lucide):
- `Sparkles` - For First-Build badge (positive, magical)
- `Info` - Alternative for badge
- `AlertTriangle` - For advanced mode warning
- `Trophy` - For celebration modal

### Testing Strategy

**What to Test:**
1. Database initializes with `isFirstBuild: true` by default
2. `getUserPreference()` returns default when key not found
3. `setUserPreference()` creates new entry if not exists
4. `setUserPreference()` updates existing entry if exists
5. `useFirstBuild()` returns `isFirstBuild: true` initially
6. `useFirstBuild()` returns loading state while checking DB
7. `setFirstBuildComplete()` sets `isFirstBuild: false` in DB
8. `generateLegoModel()` sends `complexity: 'simple'` when passed
9. `generateLegoModel()` defaults to `complexity: 'normal'`
10. FirstBuildBadge renders with correct text and icon
11. FirstBuildBadge opens modal on click
12. AdvancedModeToggle calls onChange with correct value
13. AdvancedModeToggle shows warning when enabled for first-build user
14. FirstBuildCelebration modal shows trophy and unlock message

**Mocking Strategy:**
```typescript
// Mock Dexie.js for unit tests
vi.mock('@/lib/db', () => ({
  getUserPreference: vi.fn(),
  setUserPreference: vi.fn(),
  markFirstBuildComplete: vi.fn(),
}));
```

### Accessibility Requirements (WCAG AA)

- Badge has `role="button"` and descriptive `aria-label`
- Switch/Toggle properly associated with label via `id` and `htmlFor`
- Modal uses Shadcn/ui Dialog which handles focus trap
- Color is not sole indicator (icons accompany text)
- Touch targets >= 44px for mobile
- Keyboard navigable: Tab to switch, Space to toggle

### Project Structure Notes

Per Architecture:
- Database layer in `/Frontend/lib/db.ts`
- Custom hooks in `/Frontend/lib/hooks/`
- New components in `/Frontend/components/generate/`
- Tests co-located: `*.tsx` + `*.test.tsx`
- Types in `/Frontend/lib/types.ts`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.5]
- [Source: _bmad-output/planning-artifacts/architecture.md#IndexedDB Schema Design]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/project-context.md#Technology Stack]
- [Source: Frontend/lib/lego-api.ts] - API client to extend
- [Source: Frontend/components/ui/badge.tsx] - Badge component pattern from Story 2.4
- [Source: Dexie.js Documentation](https://dexie.org/docs/)
- [Source: Shadcn/ui Switch Documentation](https://ui.shadcn.com/docs/components/switch)

### Integration Points

**Consumes from Story 2.1/2.2/2.4:**
- Generation flow from Stories 2.1, 2.2
- Structural feedback from Story 2.4 (simpler models should have higher scores)

**Enables for Epic 5:**
- Epic 5 Story 5.3 (Build Completion Celebration) will call `setFirstBuildComplete()`
- FirstBuildCelebration modal can be triggered from Epic 5 completion flow

**Backend Integration:**
- Backend coder agent must respect `complexity: 'simple'` hint
- If backend doesn't support this yet, document as known limitation

### Critical Dependencies

**Install before development:**
```bash
cd Frontend && pnpm add dexie@4.2.1 dexie-react-hooks@4.2.0
```

**Add Shadcn/ui components if not installed:**
```bash
cd Frontend && npx shadcn@latest add switch label
```

### Risk Considerations

1. **Backend Complexity Support**: Verify backend coder agent honors `complexity` parameter. If not, this is frontend-only preparation.

2. **IndexedDB Browser Support**: IndexedDB is widely supported, but test in Safari/iOS for edge cases.

3. **First-Build Detection Edge Case**: User could clear browser data - `isFirstBuild` defaults to `true`, so they get first-build mode again (acceptable UX).

4. **Epic 5 Dependency**: Celebration modal is created here but triggered by Epic 5. Ensure interface is well-documented.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- All 83 story-specific tests pass (after code review fixes)
- Build passes with no TypeScript errors
- 1 pre-existing test failure in `__tests__/Chat.test.tsx` (unrelated to this story)

### Code Review Fixes Applied

| Issue | Severity | Fix |
|-------|----------|-----|
| H1: Badge text mismatch | HIGH | Updated badge to "First-Build Mode - Simplified for success" |
| M1: Missing error handling | MEDIUM | Added try/catch to setFirstBuildComplete |
| M2: Type mismatch in db.test.ts | MEDIUM | Fixed tests to use string values |
| M3: Missing integration tests | MEDIUM | Added 8 integration tests to generate.test.tsx |
| M4: File List incomplete | MEDIUM | Added missing files to documentation |

### Completion Notes List

1. Database helper functions (`getUserPreference`, `setUserPreference`, `markFirstBuildComplete`) added to existing `db.ts`
2. New custom hook `useFirstBuild()` in `/Frontend/lib/hooks/`
3. Updated `GenerateOptions.complexity` from `'simple' | 'medium' | 'complex'` to `'simple' | 'normal'`
4. Three new components: `FirstBuildBadge`, `AdvancedModeToggle`, `FirstBuildCelebration`
5. Integration complete in `/Frontend/app/generate/page.tsx`
6. Shadcn/ui Switch and Label components installed
7. Epic 5 integration point prepared via `useFirstBuild().setFirstBuildComplete()` and `markFirstBuildComplete()`

### File List

**New Files:**
- `/Frontend/lib/db.test.ts` - 13 tests for database helpers
- `/Frontend/lib/hooks/use-first-build.ts` - Custom hook for first-build state
- `/Frontend/lib/hooks/use-first-build.test.ts` - 8 tests for hook
- `/Frontend/lib/hooks/index.ts` - Exports for hooks
- `/Frontend/components/generate/first-build-badge.tsx` - Blue badge component
- `/Frontend/components/generate/first-build-badge.test.tsx` - 9 tests
- `/Frontend/components/generate/advanced-mode-toggle.tsx` - Toggle component
- `/Frontend/components/generate/advanced-mode-toggle.test.tsx` - 9 tests
- `/Frontend/components/generate/first-build-celebration.tsx` - Celebration modal
- `/Frontend/components/generate/first-build-celebration.test.tsx` - 10 tests
- `/Frontend/components/ui/switch.tsx` - Shadcn/ui switch (installed)
- `/Frontend/components/ui/label.tsx` - Shadcn/ui label (installed)

**Modified Files:**
- `/Frontend/lib/db.ts` - Added helper functions
- `/Frontend/lib/types.ts` - Updated `GenerateOptions.complexity` type
- `/Frontend/lib/api.ts` - No changes needed (already supports options)
- `/Frontend/__tests__/lego-api.test.ts` - Updated to use `'normal'` complexity, added 2 new tests
- `/Frontend/__tests__/generate.test.tsx` - Added first-build integration tests (8 tests)
- `/Frontend/app/generate/page.tsx` - Integrated First-Build logic
- `/Frontend/components/generate/index.ts` - Added exports for new components
- `/Frontend/package.json` - Added @radix-ui/react-switch, @radix-ui/react-label
- `/Frontend/package-lock.json` - Updated dependency lockfile
- `/_bmad-output/implementation-artifacts/sprint-status.yaml` - Updated story status tracking

