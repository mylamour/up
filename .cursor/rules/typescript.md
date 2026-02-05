---
description: TypeScript code standards
globs: ["**/*.ts", "**/*.tsx"]
---

# TypeScript Rules

## Style

- Enable strict mode
- Use interfaces over types for objects
- Prefer async/await over promises
- Use const assertions where appropriate

## Imports

```typescript
// External packages
import React from 'react';
import { useState } from 'react';

// Internal modules
import { Component } from '@/components';
import { utils } from '@/lib';

// Types
import type { User } from '@/types';
```

## Types

```typescript
// Prefer interfaces for objects
interface User {
  id: string;
  name: string;
  email: string;
}

// Use type for unions/intersections
type Status = 'pending' | 'active' | 'completed';

// Generic constraints
function process<T extends { id: string }>(item: T): string {
  return item.id;
}
```

## React Components (if applicable)

```tsx
interface Props {
  title: string;
  onAction: () => void;
}

export function Component({ title, onAction }: Props) {
  const [state, setState] = useState(false);
  
  return (
    <div>
      <h1>{title}</h1>
      <button onClick={onAction}>Action</button>
    </div>
  );
}
```

## Testing

- Use Jest or Vitest
- Name test files `*.test.ts` or `*.spec.ts`
- Mock external dependencies
