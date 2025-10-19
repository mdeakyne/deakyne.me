import { renderDashboard, type MetricsDashboardPayload } from '@/lib/metrics';

export interface CommandContext {
  authToken: string | null;
  setAuthToken: (token: string | null) => void;
}

export interface CommandResult {
  output: string;
  error?: boolean;
}

export type CommandHandler = (
  args: string[],
  context: CommandContext
) => Promise<CommandResult> | CommandResult;

export const commands: Record<string, CommandHandler> = {
  help: () => ({
    output: `\r\n\x1b[1;36mAvailable Commands:\x1b[0m\r
\r
  \x1b[32mhelp\x1b[0m                    Show this help message\r
  \x1b[32mdocs\x1b[0m                    Browse API documentation\r
  \x1b[32mrequest-key <email>\x1b[0m     Request JWT authentication key\r
  \x1b[32mauth <token>\x1b[0m            Authenticate with your JWT token\r
  \x1b[32mapi list\x1b[0m                List available API endpoints\r
  \x1b[32mapi call <endpoint>\x1b[0m     Make an API call\r
  \x1b[32mapi docs <endpoint>\x1b[0m     Show endpoint documentation\r
  \x1b[32mmetrics\x1b[0m                 View live API metrics dashboard\r
  \x1b[32mmail <message>\x1b[0m          Send a message to Matt Deakyne\r
  \x1b[32mlogout\x1b[0m                  Clear authentication\r
  \x1b[32mclear\x1b[0m                   Clear terminal screen\r
\r
Type a command and press Enter to execute.\r\n`,
  }),

  docs: () => ({
    output: `\r\n\x1b[1;36mAPI Documentation\x1b[0m\r
\r
Welcome to the Deakyne.me API documentation.\r
\r
To get started:\r
  1. Request an API key: \x1b[32mrequest-key your@email.com\x1b[0m\r
  2. Check your email for the JWT token\r
  3. Authenticate: \x1b[32mauth <your-token>\x1b[0m\r
  4. List available endpoints: \x1b[32mapi list\x1b[0m\r
\r
For more information, visit: https://deakyne.me\r\n`,
  }),

  'request-key': async (args) => {
    if (args.length === 0) {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Email address required\r\nUsage: request-key <email>\r\n',
        error: true,
      };
    }

    const email = args[0];
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(email)) {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Invalid email address\r\n',
        error: true,
      };
    }

    try {
      const response = await fetch('/api/request-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          output: `\r\n\x1b[31mError:\x1b[0m ${data.error || 'Failed to request key'}\r\n`,
          error: true,
        };
      }

      return {
        output: `\r\n\x1b[32mSuccess!\x1b[0m API key has been sent to ${email}\r\nCheck your inbox and use 'auth <token>' to authenticate.\r\n`,
      };
    } catch {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Failed to connect to server\r\n',
        error: true,
      };
    }
  },

  auth: async (args, context) => {
    if (args.length === 0) {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Token required\r\nUsage: auth <token>\r\n',
        error: true,
      };
    }

    const token = args[0];

    // Basic JWT format validation
    if (token.split('.').length !== 3) {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Invalid token format\r\n',
        error: true,
      };
    }

    // Validate token with backend
    try {
      const response = await fetch('/api/validate-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          output: `\r\n\x1b[31mError:\x1b[0m ${data.detail || 'Invalid token'}\r\n`,
          error: true,
        };
      }

      // Token is valid, set it in context and localStorage
      context.setAuthToken(token);
      localStorage.setItem('auth_token', token);

      return {
        output: '\r\n\x1b[32mAuthentication successful!\x1b[0m\r\nYou can now use API commands.\r\n',
      };
    } catch {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Failed to validate token with server\r\n',
        error: true,
      };
    }
  },

  logout: (args, context) => {
    context.setAuthToken(null);
    localStorage.removeItem('auth_token');
    return {
      output: '\r\n\x1b[33mLogged out successfully\x1b[0m\r\n',
    };
  },

  mail: async (args, context) => {
    if (!context.authToken) {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Not authenticated\r\nUse \'request-key\' and \'auth\' commands first.\r\n',
        error: true,
      };
    }

    if (args.length === 0) {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Message required\r\nUsage: mail <your message here>\r\n',
        error: true,
      };
    }

    const message = args.join(' ');

    try {
      const response = await fetch('/api/mail', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${context.authToken}`,
        },
        body: JSON.stringify({ message }),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          output: `\r\n\x1b[31mError:\x1b[0m ${data.error || 'Failed to send message'}\r\n`,
          error: true,
        };
      }

      return {
        output: `\r\n\x1b[32mSuccess!\x1b[0m Message sent from ${data.email} to Matt Deakyne\r\n`,
      };
    } catch {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Failed to send message\r\n',
        error: true,
      };
    }
  },

  api: async (args, context) => {
    if (args.length === 0) {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Subcommand required\r\nUsage: api <list|call|docs> [args]\r\n',
        error: true,
      };
    }

    const subcommand = args[0];
    const subArgs = args.slice(1);

    switch (subcommand) {
      case 'list':
        return {
          output: `\r\n\x1b[1;36mAvailable API Endpoints:\x1b[0m\r
\r
  \x1b[32mGET\x1b[0m  /api/profile          Basic profile information\r
  \x1b[32mGET\x1b[0m  /api/summary          Professional summary\r
  \x1b[32mGET\x1b[0m  /api/experience       Work experience\r
  \x1b[32mGET\x1b[0m  /api/education        Education and degrees\r
  \x1b[32mGET\x1b[0m  /api/skills           Technical skills\r
  \x1b[32mGET\x1b[0m  /api/competencies     Core competencies\r
  \x1b[32mGET\x1b[0m  /api/projects         Portfolio projects\r
  \x1b[32mGET\x1b[0m  /api/hobbies          Hobbies and interests\r
  \x1b[32mGET\x1b[0m  /api/books            Reading list\r
  \x1b[32mGET\x1b[0m  /api/principles       Core principles\r
\r
Use 'api call <endpoint>' to make an authenticated request.\r\n`,
        };

      case 'call':
        if (!context.authToken) {
          return {
            output: '\r\n\x1b[31mError:\x1b[0m Not authenticated\r\nUse \'request-key\' and \'auth\' commands first.\r\n',
            error: true,
          };
        }

        if (subArgs.length === 0) {
          return {
            output: '\r\n\x1b[31mError:\x1b[0m Endpoint required\r\nUsage: api call <endpoint>\r\n',
            error: true,
          };
        }

        const endpoint = subArgs[0];

        try {
          const response = await fetch(`/api/call?endpoint=${encodeURIComponent(endpoint)}`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${context.authToken}`,
            },
          });

          const data = await response.json();

          if (!response.ok) {
            return {
              output: `\r\n\x1b[31mError:\x1b[0m ${data.error || 'API call failed'}\r\n`,
              error: true,
            };
          }

          // Format the JSON response nicely
          const jsonOutput = JSON.stringify(data, null, 2)
            .split('\n')
            .map(line => '  ' + line)
            .join('\r\n');

          return {
            output: `\r\n\x1b[1;36mResponse from ${endpoint}:\x1b[0m\r\n${jsonOutput}\r\n`,
          };
        } catch {
          return {
            output: '\r\n\x1b[31mError:\x1b[0m Failed to call API\r\n',
            error: true,
          };
        }

      case 'docs':
        if (subArgs.length === 0) {
          return {
            output: '\r\n\x1b[31mError:\x1b[0m Endpoint required\r\nUsage: api docs <endpoint>\r\n',
            error: true,
          };
        }

        const docEndpoint = subArgs[0];
        const docs: Record<string, string> = {
          '/api/profile': 'Basic profile information including name, location, contact, and professional headline',
          '/api/summary': 'Professional summary with mission statement and core strengths',
          '/api/experience': 'Detailed work experience and position history',
          '/api/education': 'Educational background and degrees earned',
          '/api/skills': 'Technical skills including languages, frameworks, and tools',
          '/api/competencies': 'Core competencies in leadership, data, automation, and collaboration',
          '/api/projects': 'Portfolio of notable projects and personal work',
          '/api/hobbies': 'Personal hobbies and interests outside of work',
          '/api/books': 'Current reading list and recently completed books',
          '/api/principles': 'Core principles and professional philosophy',
        };

        const description = docs[docEndpoint];
        if (!description) {
          return {
            output: `\r\n\x1b[31mError:\x1b[0m Unknown endpoint '${docEndpoint}'\r\nUse 'api list' to see available endpoints.\r\n`,
            error: true,
          };
        }

        return {
          output: `\r\n\x1b[1;36mEndpoint:\x1b[0m ${docEndpoint}\r
\x1b[1;36mMethod:\x1b[0m GET\r
\x1b[1;36mAuth:\x1b[0m Required (JWT Bearer token)\r
\x1b[1;36mDescription:\x1b[0m ${description}\r
\r
\x1b[33mExample:\x1b[0m api call ${docEndpoint}\r\n`,
        };

      default:
        return {
          output: `\r\n\x1b[31mError:\x1b[0m Unknown subcommand '${subcommand}'\r\nAvailable: list, call, docs\r\n`,
          error: true,
        };
    }
  },

  metrics: async () => {
    try {
      const response = await fetch('/api/metrics/dashboard');
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        return {
          output: `\r\n\x1b[31mError:\x1b[0m Failed to load metrics dashboard${error.message ? `: ${error.message}` : ''}\r\n`,
          error: true,
        };
      }

      const data = (await response.json()) as MetricsDashboardPayload;
      return {
        output: renderDashboard(data),
      };
    } catch {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Unable to reach metrics service\r\n',
        error: true,
      };
    }
  },

  clear: () => {
    return { output: '\x1b[2J\x1b[H' }; // ANSI codes to clear screen
  },
};

export async function executeCommand(
  input: string,
  context: CommandContext
): Promise<CommandResult> {
  const parts = input.trim().split(/\s+/);
  const command = parts[0].toLowerCase();
  const args = parts.slice(1);

  if (command === '') {
    return { output: '' };
  }

  const handler = commands[command];

  if (!handler) {
    return {
      output: `\r\n\x1b[31mCommand not found:\x1b[0m ${command}\r\nType 'help' for available commands.\r\n`,
      error: true,
    };
  }

  return await handler(args, context);
}
