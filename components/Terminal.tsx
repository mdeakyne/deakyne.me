'use client';

import { useEffect, useRef, useState } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import { executeCommand, type CommandContext } from '@/lib/commands';
import { captureTerminalEvent } from '@/app/config/posthog';

const PROMPT = '\r\n\x1b[32mdeakyne.me\x1b[0m $ ';

export default function Terminal() {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const currentLineRef = useRef<string>('');
  const cursorPositionRef = useRef<number>(0);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize terminal
    const term = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'JetBrains Mono, Fira Code, monospace',
      theme: {
        background: '#0a0e14',
        foreground: '#00ff00',
        cursor: '#00ff00',
        selectionBackground: '#00ff0040',
      },
      rows: 30,
      cols: 100,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);

    // Safely open terminal with null check
    if (terminalRef.current) {
      term.open(terminalRef.current);

      // Fit terminal with error handling and delay
      setTimeout(() => {
        try {
          if (fitAddon && term.element) {
            fitAddon.fit();
          }
        } catch (error) {
          console.error('Failed to fit terminal:', error);
        }
      }, 100);
    }

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Load saved auth token
    const savedToken = localStorage.getItem('auth_token');
    if (savedToken) {
      setAuthToken(savedToken);
    }

    // Welcome message
    term.writeln('\x1b[1;36m╔══════════════════════════════════════════════════════════════╗\x1b[0m');
    term.writeln('\x1b[1;36m║\x1b[0m  \x1b[1;32mWelcome to Deakyne.me Developer Portal\x1b[0m                  \x1b[1;36m║\x1b[0m');
    term.writeln('\x1b[1;36m║\x1b[0m  Interactive API Documentation & Testing                  \x1b[1;36m║\x1b[0m');
    term.writeln('\x1b[1;36m╚══════════════════════════════════════════════════════════════╝\x1b[0m');
    term.writeln('');
    term.writeln('Type \x1b[33mhelp\x1b[0m to see available commands.');
    term.write(PROMPT);

    captureTerminalEvent('terminal_ready');

    // Handle terminal input
    term.onData((data) => {
      const code = data.charCodeAt(0);

      // Handle Enter
      if (code === 13) {
        const command = currentLineRef.current.trim();

        if (command) {
          const context: CommandContext = {
            authToken,
            setAuthToken,
          };

          executeCommand(command, context).then((result) => {
            if (result.output) {
              term.write(result.output);
            }
            term.write(PROMPT);
            currentLineRef.current = '';
            cursorPositionRef.current = 0;
            captureTerminalEvent('terminal_command', {
              command,
              error: Boolean(result.error),
            });
          });
        } else {
          term.write(PROMPT);
        }
        return;
      }

      // Handle Backspace
      if (code === 127) {
        if (cursorPositionRef.current > 0) {
          currentLineRef.current =
            currentLineRef.current.slice(0, cursorPositionRef.current - 1) +
            currentLineRef.current.slice(cursorPositionRef.current);
          cursorPositionRef.current--;
          term.write('\b \b');
        }
        return;
      }

      // Handle Ctrl+C
      if (code === 3) {
        term.write('^C');
        term.write(PROMPT);
        currentLineRef.current = '';
        cursorPositionRef.current = 0;
        return;
      }

      // Handle Ctrl+L (clear)
      if (code === 12) {
        term.clear();
        term.write(PROMPT);
        return;
      }

      // Handle printable characters
      if (code >= 32 && code < 127) {
        currentLineRef.current =
          currentLineRef.current.slice(0, cursorPositionRef.current) +
          data +
          currentLineRef.current.slice(cursorPositionRef.current);
        cursorPositionRef.current++;
        term.write(data);
      }
    });

    // Handle window resize with debounce and error handling
    let resizeTimeout: NodeJS.Timeout;
    const handleResize = () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        try {
          if (fitAddon && term.element) {
            fitAddon.fit();
          }
        } catch (error) {
          console.error('Failed to fit terminal on resize:', error);
        }
      }, 100);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      clearTimeout(resizeTimeout);
      window.removeEventListener('resize', handleResize);
      term.dispose();
    };
  }, [authToken]);

  return (
    <div className="w-full h-screen">
      <div ref={terminalRef} className="w-full h-full" />
    </div>
  );
}
