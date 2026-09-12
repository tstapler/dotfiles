import { spawn } from "node:child_process";
import type { ExtensionAPI, ToolExecutionEndEvent } from "@earendil-works/pi-coding-agent";

// Mirrors kibitzer's Claude Code PostToolUse hook contract (src/hook.rs in
// tstapler/kibitzer): stdin is Claude's hook JSON shape, exit code 2 means a
// blocking finding on stderr, exit 0 with stdout means advisory findings as
// `{hookSpecificOutput: {additionalContext}}`, exit 0 with no stdout means clean.
interface KibitzerEditItem {
  old_string: string;
  new_string: string;
}

interface KibitzerToolInput {
  file_path: string;
  content?: string;
  old_string?: string;
  new_string?: string;
  edits?: KibitzerEditItem[];
}

interface PiEditArgs {
  path: string;
  edits?: { oldText: string; newText: string }[];
}

interface PiWriteArgs {
  path: string;
  content: string;
}

function runKibitzerHook(
  payload: unknown,
): Promise<{ code: number | null; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const child = spawn("kibitzer", ["hook"], { stdio: ["pipe", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.stderr.on("data", (chunk) => (stderr += chunk));
    // kibitzer isn't installed, or isn't on PATH in this environment — stay silent.
    child.on("error", () => resolve({ code: null, stdout, stderr }));
    child.on("close", (code) => resolve({ code, stdout, stderr }));
    child.stdin.write(JSON.stringify(payload));
    child.stdin.end();
  });
}

function buildToolInput(event: ToolExecutionEndEvent): KibitzerToolInput | undefined {
  if (event.toolName === "write") {
    const args = event.args as PiWriteArgs;
    if (!args?.path) return undefined;
    return { file_path: args.path, content: args.content ?? "" };
  }

  if (event.toolName === "edit") {
    const args = event.args as PiEditArgs;
    if (!args?.path) return undefined;
    const edits = args.edits ?? [];
    if (edits.length === 1) {
      return {
        file_path: args.path,
        old_string: edits[0].oldText,
        new_string: edits[0].newText,
      };
    }
    return {
      file_path: args.path,
      edits: edits.map((e) => ({ old_string: e.oldText, new_string: e.newText })),
    };
  }

  return undefined;
}

export default function kibitzer(pi: ExtensionAPI) {
  pi.on("tool_execution_end", async (event, ctx) => {
    if (event.isError) return;

    const toolInput = buildToolInput(event);
    if (!toolInput) return;

    const payload = {
      cwd: ctx.cwd,
      hook_event_name: "PostToolUse",
      tool_use_id: event.toolCallId,
      tool_input: toolInput,
    };

    const { code, stdout, stderr } = await runKibitzerHook(payload);
    if (code === null) return;

    if (code === 2) {
      ctx.ui.notify(stderr.trim() || "[kibitzer] blocking finding", "error");
      return;
    }

    if (!stdout.trim()) return;
    try {
      const parsed = JSON.parse(stdout);
      const context = parsed?.hookSpecificOutput?.additionalContext;
      if (context) ctx.ui.notify(context, "warning");
    } catch {
      // Unparsable stdout — nothing actionable to surface.
    }
  });
}
