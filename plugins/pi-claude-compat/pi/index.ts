import { Type, type Static } from "typebox";
import type { ExtensionAPI, ExtensionContext, ToolDefinition } from "@earendil-works/pi-coding-agent";
import {
  createFindToolDefinition,
  createGrepToolDefinition,
  createLsToolDefinition,
} from "@earendil-works/pi-coding-agent";

type AnyToolDefinition = ToolDefinition<any, any, any>;

/**
 * Registers `name` as a full alias of a Pi-native tool.
 *
 * Pi's extension API has no "forward this tool call to another registered
 * tool" primitive (tool_call handlers can only mutate input or block), so
 * this re-derives the native tool definition from its own factory — using
 * the live `ctx.cwd` at call time rather than a cwd frozen at extension
 * load — and delegates straight to its `execute`. Everything else (schema,
 * description, rendering) comes from the native definition unchanged.
 */
function aliasNativeTool(
  name: string,
  createDefinition: (cwd: string) => AnyToolDefinition,
): AnyToolDefinition {
  const template = createDefinition(process.cwd());
  return {
    ...template,
    name,
    execute: (toolCallId, params, signal, onUpdate, ctx) =>
      createDefinition(ctx.cwd).execute(toolCallId, params, signal, onUpdate, ctx),
  };
}

const askUserQuestionOptionSchema = Type.Object({
  label: Type.String(),
  description: Type.Optional(Type.String()),
});

const askUserQuestionQuestionSchema = Type.Object({
  header: Type.Optional(Type.String()),
  question: Type.String(),
  multiSelect: Type.Optional(Type.Boolean()),
  options: Type.Array(askUserQuestionOptionSchema),
});

const askUserQuestionSchema = Type.Object({
  questions: Type.Array(askUserQuestionQuestionSchema),
});

type AskUserQuestionInput = Static<typeof askUserQuestionSchema>;

interface AskUserQuestionAnswer {
  header?: string;
  question: string;
  answer: string;
}

// Pi's native ask-user primitive is ctx.ui.select() — a single-choice
// dialog. There is no native multi-select prompt, so a `multiSelect: true`
// question still only returns one answer here; that is a known gap, not a
// silent no-op (see project_plans/pi-dotfiles/implementation/plan.md's Task
// 3.4.1a).
async function executeAskUserQuestion(
  _toolCallId: string,
  params: AskUserQuestionInput,
  signal: AbortSignal | undefined,
  _onUpdate: unknown,
  ctx: ExtensionContext,
) {
  if (!ctx.hasUI) {
    throw new Error("AskUserQuestion: no interactive UI available in this Pi run mode.");
  }

  const answers: AskUserQuestionAnswer[] = [];
  for (const q of params.questions) {
    const title = q.header ? `${q.header}: ${q.question}` : q.question;
    const labels = q.options.map((option) =>
      option.description ? `${option.label} — ${option.description}` : option.label,
    );
    const choice = await ctx.ui.select(title, labels, { signal });
    answers.push({ header: q.header, question: q.question, answer: choice ?? "(no answer)" });
  }

  const text = answers
    .map((a) => `${a.header ? `[${a.header}] ` : ""}${a.question} -> ${a.answer}`)
    .join("\n");

  return { content: [{ type: "text" as const, text }], details: answers };
}

const askUserQuestionTool: ToolDefinition<typeof askUserQuestionSchema, AskUserQuestionAnswer[]> = {
  name: "AskUserQuestion",
  label: "Ask User Question",
  description:
    "Ask the user one or more multiple-choice questions and wait for their answers. " +
    "Compat shim for Claude Code's AskUserQuestion tool, backed by Pi's native " +
    "single-choice ui.select() prompt.",
  promptSnippet: "Ask the user a multiple-choice question",
  parameters: askUserQuestionSchema,
  execute: executeAskUserQuestion,
};

export default function piClaudeCompat(pi: ExtensionAPI): void {
  pi.registerTool(aliasNativeTool("Grep", (cwd) => createGrepToolDefinition(cwd)));
  pi.registerTool(aliasNativeTool("Glob", (cwd) => createFindToolDefinition(cwd)));
  pi.registerTool(aliasNativeTool("LS", (cwd) => createLsToolDefinition(cwd)));
  pi.registerTool(askUserQuestionTool);
}
