import { describe, expect, it } from 'vitest';
import { getCompletion } from '@/lib/completion';

describe('getCompletion', () => {
  describe('command completion', () => {
    it('completes partial command with single match', () => {
      const result = getCompletion('hel');
      expect(result).toEqual({ completed: 'help ' });
    });

    it('completes partial command with multiple matches', () => {
      const result = getCompletion('a');
      expect(result?.completed).toBe('a');
      expect(result?.suggestions).toContain('api');
      expect(result?.suggestions).toContain('auth');
    });

    it('returns null for no matches', () => {
      const result = getCompletion('xyz');
      expect(result).toBeNull();
    });

    it('completes exact command match', () => {
      const result = getCompletion('help');
      expect(result).toEqual({ completed: 'help ' });
    });
  });

  describe('api subcommand completion', () => {
    it('completes api subcommand with single match', () => {
      const result = getCompletion('api li');
      expect(result).toEqual({ completed: 'api list ' });
    });

    it('completes api subcommand with multiple matches', () => {
      const result = getCompletion('api ');
      expect(result?.suggestions).toContain('list');
      expect(result?.suggestions).toContain('call');
      expect(result?.suggestions).toContain('docs');
    });

    it('completes api call subcommand', () => {
      const result = getCompletion('api ca');
      expect(result).toEqual({ completed: 'api call ' });
    });
  });

  describe('endpoint completion', () => {
    it('completes endpoint for api call', () => {
      const result = getCompletion('api call /api/prof');
      expect(result).toEqual({ completed: 'api call /api/profile' });
    });

    it('completes endpoint for api docs', () => {
      const result = getCompletion('api docs /api/ski');
      expect(result).toEqual({ completed: 'api docs /api/skills' });
    });

    it('shows multiple endpoint matches', () => {
      const result = getCompletion('api call /api/');
      expect(result?.suggestions).toBeDefined();
      expect(result?.suggestions?.length).toBeGreaterThan(1);
    });

    it('completes common prefix for multiple matches', () => {
      const result = getCompletion('api call /api/p');
      expect(result?.completed).toBe('api call /api/pr');
      expect(result?.suggestions).toContain('/api/profile');
      expect(result?.suggestions).toContain('/api/projects');
      expect(result?.suggestions).toContain('/api/principles');
    });
  });

  describe('edge cases', () => {
    it('handles empty input', () => {
      const result = getCompletion('');
      // Should show all commands when empty
      expect(result).toBeDefined();
      if (result) {
        expect(result.suggestions).toBeDefined();
        expect(result.suggestions?.length).toBeGreaterThan(0);
      }
    });

    it('handles trailing spaces', () => {
      const result = getCompletion('api ');
      expect(result?.suggestions).toContain('list');
    });

    it('returns null for non-completable commands', () => {
      const result = getCompletion('help something');
      expect(result).toBeNull();
    });
  });
});
