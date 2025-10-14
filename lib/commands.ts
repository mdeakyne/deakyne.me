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
  \x1b[32mlogout\x1b[0m                  Clear authentication\r
  \x1b[32mclear\x1b[0m                   Clear terminal screen\r
\r
Type a command and press Enter to execute.\r\n`,
  }),

  docs: () => ({
    output: `\r\n\x1b[1;36mAPI Documentation\x1b[0m\r
\r
Welcome to the Deakyne.Dev API documentation.\r
\r
To get started:\r
  1. Request an API key: \x1b[32mrequest-key your@email.com\x1b[0m\r
  2. Check your email for the JWT token\r
  3. Authenticate: \x1b[32mauth <your-token>\x1b[0m\r
  4. List available endpoints: \x1b[32mapi list\x1b[0m\r
\r
For more information, visit: https://deakyne.dev/docs\r\n`,
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
    } catch (error) {
      return {
        output: '\r\n\x1b[31mError:\x1b[0m Failed to connect to server\r\n',
        error: true,
      };
    }
  },

  auth: (args, context) => {
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

    context.setAuthToken(token);
    localStorage.setItem('auth_token', token);

    return {
      output: '\r\n\x1b[32mAuthentication successful!\x1b[0m\r\nYou can now use API commands.\r\n',
    };
  },

  logout: (args, context) => {
    context.setAuthToken(null);
    localStorage.removeItem('auth_token');
    return {
      output: '\r\n\x1b[33mLogged out successfully\x1b[0m\r\n',
    };
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
  \x1b[32mGET\x1b[0m  /api/v1/status        Check API status\r
  \x1b[32mGET\x1b[0m  /api/v1/user/profile  Get user profile\r
  \x1b[32mPOST\x1b[0m /api/v1/data/query    Query data\r
\r
Use 'api docs <endpoint>' for detailed documentation.\r
Use 'api call <endpoint>' to make a request.\r\n`,
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

        return {
          output: `\r\n\x1b[33mCalling endpoint:\x1b[0m ${subArgs[0]}\r\n\x1b[90m(API integration coming soon)\x1b[0m\r\n`,
        };

      case 'docs':
        if (subArgs.length === 0) {
          return {
            output: '\r\n\x1b[31mError:\x1b[0m Endpoint required\r\nUsage: api docs <endpoint>\r\n',
            error: true,
          };
        }

        return {
          output: `\r\n\x1b[1;36mEndpoint Documentation:\x1b[0m ${subArgs[0]}\r\n\x1b[90m(Documentation coming soon)\x1b[0m\r\n`,
        };

      default:
        return {
          output: `\r\n\x1b[31mError:\x1b[0m Unknown subcommand '${subcommand}'\r\nAvailable: list, call, docs\r\n`,
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
