import { existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const REVIEW_GATE =
  "MANDATORY REVIEW GATE: before opening, readying, or merging a PR, run the " +
  "full adversarial review loop and address every real finding. Retry this " +
  "command after completing that review; for docs/config-only changes, state " +
  "that explicitly and scope the review accordingly.";

const TRIVIAL_COMMANDS = new Set([
  "cd", "pwd", "echo", "export", "alias", "unalias", "which", "type",
  "true", "false", "exit", "source", ".", "set", "unset", "umask",
  "history", "jobs", "fg", "bg", "wait", "clear", "pushd", "popd", "dirs",
]);

interface ExecResult {
  code: number;
  stdout: string;
  stderr?: string;
}

interface PiExec {
  exec(command: string, args: string[], options?: { signal?: AbortSignal }): Promise<ExecResult>;
}

export function isPrLifecycleCommand(command: string): boolean {
  return /\bgh\s+pr\s+(?:create|ready|merge)\b/.test(command);
}

function shellQuote(value: string): string {
  return `'${value.replaceAll("'", `'"'"'`)}'`;
}

function skipCompaction(command: string): boolean {
  if (command.includes("<<")) return true;
  if (/^\s*(?:rtk|cmdcrush)\s/.test(command)) return true;
  const firstWord = command.trim().split(/\s+/, 1)[0] ?? "";
  return TRIVIAL_COMMANDS.has(firstWord);
}

export async function compactBashCommand(
  pi: PiExec,
  command: string,
  signal?: AbortSignal,
): Promise<string> {
  if (skipCompaction(command)) return command;

  try {
    const rewritten = await pi.exec("rtk", ["rewrite", command], { signal });
    const candidate = rewritten.stdout.trim();
    if ((rewritten.code === 0 || rewritten.code === 3) && candidate && candidate !== command) {
      return candidate;
    }
  } catch {
    // RTK is optional; fall through to cmdcrush when it is unavailable.
  }

  if (command.length < 20) return command;
  let lookup: ExecResult;
  try {
    lookup = await pi.exec("sh", ["-lc", "command -v cmdcrush"], { signal });
  } catch {
    return command;
  }
  const cmdcrush = lookup.stdout.trim();
  if (lookup.code !== 0 || !cmdcrush) return command;
  return `${cmdcrush} -- bash -c ${shellQuote(command)}`;
}

function startContextAudit(sessionFile: string, sessionId: string, trigger: string): void {
  const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
  const analyzer = join(repoRoot, ".claude", "skills", "context-audit", "scripts", "context_audit.py");
  if (!existsSync(analyzer) || !existsSync(sessionFile)) return;

  const home = process.env.HOME;
  if (!home) return;
  const auditDirectory = join(home, ".claude", "context-audit");
  mkdirSync(auditDirectory, { recursive: true });
  const database = join(auditDirectory, "trend.db");
  const child = spawn(
    "python3",
    [
      analyzer,
      sessionFile,
      "--json",
      "--sqlite", database,
      "--session-id", sessionId,
      "--trigger", trigger,
    ],
    { detached: true, stdio: "ignore" },
  );
  child.once("error", () => {});
  child.unref();
}

export default function dotfilesHooks(pi: ExtensionAPI): void {
  let reviewGateSeen = new Set<string>();

  pi.on("session_start", () => {
    reviewGateSeen = new Set<string>();
  });

  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return;
    const input = event.input as { command?: unknown };
    if (typeof input.command !== "string") return;

    const original = input.command;
    if (isPrLifecycleCommand(original) && !reviewGateSeen.has(original)) {
      reviewGateSeen.add(original);
      return { block: true, reason: REVIEW_GATE };
    }

    input.command = await compactBashCommand(pi, original, ctx.signal);
  });

  pi.on("session_compact", (event, ctx) => {
    const sessionFile = ctx.sessionManager.getSessionFile();
    if (!sessionFile) return;
    startContextAudit(
      sessionFile,
      ctx.sessionManager.getSessionId(),
      event.reason ?? "unknown",
    );
  });

  pi.registerCommand("magic-compact", {
    description: "Compact the current Pi session, optionally with custom instructions",
    handler: async (args, ctx) => {
      ctx.compact({
        customInstructions: args.trim() || "Preserve decisions, unfinished work, and exact file paths.",
        onError: (error) => ctx.ui.notify(`Compaction failed: ${error.message}`, "error"),
      });
    },
  });
}
