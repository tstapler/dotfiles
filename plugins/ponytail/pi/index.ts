import { createRequire } from "node:module";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const require = createRequire(import.meta.url);
const config = require("../hooks/ponytail-config.js") as {
  VALID_MODES: string[];
  getDefaultMode(): string;
  isDeactivationCommand(text: string): boolean;
  normalizeConfigMode(mode: string): string | null;
};
const instructions = require("../hooks/ponytail-instructions.js") as {
  getPonytailInstructions(mode: string): string;
};

const ENTRY_TYPE = "ponytail-mode";

export default function ponytail(pi: ExtensionAPI) {
  let mode = config.getDefaultMode();

  const showStatus = (ctx: { ui: { setStatus(key: string, value?: string): void } }) => {
    ctx.ui.setStatus("ponytail", mode === "off" ? undefined : `ponytail:${mode}`);
  };

  const setMode = (
    nextMode: string,
    ctx: { ui: { notify(message: string, level: "info" | "warning" | "error"): void; setStatus(key: string, value?: string): void } },
  ) => {
    mode = nextMode;
    pi.appendEntry(ENTRY_TYPE, { mode });
    showStatus(ctx);
    ctx.ui.notify(
      mode === "off" ? "Ponytail mode off" : `Ponytail mode: ${mode}`,
      "info",
    );
  };

  pi.on("session_start", (_event, ctx) => {
    const saved = ctx.sessionManager
      .getBranch()
      .filter(
        (entry) => entry.type === "custom" && entry.customType === ENTRY_TYPE,
      )
      .at(-1);
    const savedMode =
      saved?.type === "custom" &&
      typeof (saved.data as { mode?: unknown } | undefined)?.mode === "string"
        ? config.normalizeConfigMode(
            (saved.data as { mode: string }).mode,
          )
        : null;
    mode = savedMode ?? config.getDefaultMode();
    showStatus(ctx);
  });

  pi.registerCommand("ponytail", {
    description: "Enable lazy senior developer mode: off, lite, full, or ultra",
    handler: async (args, ctx) => {
      const requested = args.trim().toLowerCase() || config.getDefaultMode();
      const normalized = config.normalizeConfigMode(requested);
      if (!normalized || normalized === "review") {
        ctx.ui.notify("Usage: /ponytail off|lite|full|ultra", "error");
        return;
      }
      setMode(normalized, ctx);
    },
  });

  pi.on("input", (event, ctx) => {
    if (!config.isDeactivationCommand(event.text)) return;
    setMode("off", ctx);
    return { action: "handled" as const };
  });

  pi.on("before_agent_start", (event) => {
    if (mode === "off") return;
    return {
      systemPrompt: `${event.systemPrompt}\n\n${instructions.getPonytailInstructions(mode)}`,
    };
  });
}
