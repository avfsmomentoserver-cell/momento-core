# Testing Guide

## Testing Pyramid

### Unit Tests (70%)
- Test individual functions/components
- Fast execution (<100ms per test)
- No external dependencies
- Mock all I/O operations

### Integration Tests (20%)
- Test component interactions
- Use test database
- Verify API contracts
- Test error scenarios

### E2E Tests (10%)
- Full user workflows
- Real browser testing (Playwright)
- Critical path coverage
- Visual regression testing

## Test Structure
```typescript
describe('PressureTracker', () => {
  describe('calculateLevels', () => {
    it('should return correct levels for valid input', () => {
      // Arrange
      const candles = [...];
      
      // Act
      const result = calculateLevels(candles);
      
      // Assert
      expect(result.levels).toHaveLength(10);
    });
    
    it('should throw error for empty input', () => {
      expect(() => calculateLevels([])).toThrow();
    });
  });
});
```

## CI/CD Integration
- Run unit tests on every commit
- Run integration tests on PR
- Run E2E tests before deployment
- Coverage threshold: 90%
