# Coding Standards

## General Principles

### Clean Code
- Meaningful variable names
- Single responsibility functions
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)

### Error Handling
- Always handle errors explicitly
- Use custom error types
- Include context in error messages
- Log errors with appropriate severity

### Performance
- Profile before optimizing
- Use appropriate data structures
- Minimize I/O operations
- Cache expensive computations

## Language-Specific

### TypeScript
```typescript
// Good: Explicit types, clear naming
interface UserPreferences {
  theme: 'light' | 'dark';
  notifications: boolean;
}

async function getUserPreferences(userId: string): Promise<UserPreferences> {
  // Implementation
}
```

### Python
```python
# Good: Type hints, docstrings
from typing import Optional

def calculate_pressure(
    candles: list[Candle],
    levels: int = 10
) -> PressureState:
    """Calculate pressure levels from candle data."""
    # Implementation
```

## Code Review Checklist
- [ ] Tests included
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Performance considered
- [ ] Error handling complete
