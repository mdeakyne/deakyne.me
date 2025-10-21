import { commands } from './commands';

export interface CompletionResult {
  completed: string;
  suggestions?: string[];
}

/**
 * Get tab completion for the current input line
 * Returns the completed string and optionally a list of suggestions if multiple matches
 */
export function getCompletion(line: string): CompletionResult | null {
  const trimmed = line.trimStart();
  const hasTrailingSpace = line.endsWith(' ');
  const parts = trimmed.split(/\s+/).filter(p => p.length > 0);

  // Determine what we're completing
  const lastPart = hasTrailingSpace ? '' : (parts[parts.length - 1] || '');
  const effectiveLength = hasTrailingSpace ? parts.length + 1 : parts.length;

  // Command completion (first word)
  if (effectiveLength === 1) {
    const commandNames = Object.keys(commands);
    const matches = commandNames.filter(cmd => cmd.startsWith(lastPart.toLowerCase()));

    if (matches.length === 0) {
      return null;
    }

    if (matches.length === 1) {
      return { completed: matches[0] + ' ' };
    }

    // Multiple matches - return common prefix
    const commonPrefix = getCommonPrefix(matches);
    return {
      completed: commonPrefix,
      suggestions: matches,
    };
  }

  // API subcommand completion
  if (effectiveLength === 2 && parts[0].toLowerCase() === 'api') {
    const subcommands = ['list', 'call', 'docs'];
    const matches = subcommands.filter(sub => sub.startsWith(lastPart.toLowerCase()));

    if (matches.length === 0) {
      return null;
    }

    if (matches.length === 1) {
      return { completed: parts[0] + ' ' + matches[0] + ' ' };
    }

    return {
      completed: parts[0] + ' ' + getCommonPrefix(matches),
      suggestions: matches,
    };
  }

  // API endpoint completion (for "api call" and "api docs")
  if (effectiveLength === 3 && parts[0].toLowerCase() === 'api' &&
      parts.length >= 2 && (parts[1].toLowerCase() === 'call' || parts[1].toLowerCase() === 'docs')) {
    const endpoints = [
      '/api/profile',
      '/api/summary',
      '/api/experience',
      '/api/education',
      '/api/skills',
      '/api/competencies',
      '/api/projects',
      '/api/hobbies',
      '/api/books',
      '/api/principles',
    ];

    const matches = endpoints.filter(ep => ep.startsWith(lastPart));

    if (matches.length === 0) {
      return null;
    }

    if (matches.length === 1) {
      return { completed: `${parts[0]} ${parts[1]} ${matches[0]}` };
    }

    return {
      completed: `${parts[0]} ${parts[1]} ${getCommonPrefix(matches)}`,
      suggestions: matches,
    };
  }

  return null;
}

/**
 * Find the longest common prefix among strings
 */
function getCommonPrefix(strings: string[]): string {
  if (strings.length === 0) return '';
  if (strings.length === 1) return strings[0];

  let prefix = strings[0];
  for (let i = 1; i < strings.length; i++) {
    while (strings[i].indexOf(prefix) !== 0) {
      prefix = prefix.slice(0, -1);
      if (prefix === '') return '';
    }
  }
  return prefix;
}
