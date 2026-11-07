#!/usr/bin/env node
// PostToolUse formatter. Formats the edited file with the project's local prettier,
// or `ruff format` for Python. Never blocks: all errors are swallowed and it always exits 0.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

const PRETTIER_EXT = new Set([".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json", ".css", ".scss", ".html", ".md"]);
const TIMEOUT = 15000;
const isWin = process.platform === "win32";

function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => (data += c));
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", () => resolve(""));
  });
}

function localBin(projectDir, name) {
  const base = path.join(projectDir, "node_modules", ".bin", name);
  for (const p of isWin ? [`${base}.cmd`, `${base}.exe`, base] : [base]) if (existsSync(p)) return p;
  return null;
}

function run(cmd, args, cwd) {
  spawnSync(cmd, args, { cwd, stdio: "ignore", timeout: TIMEOUT, shell: isWin && /\.cmd$/i.test(cmd) });
}

try {
  const input = JSON.parse(await readStdin());
  const fp = input?.tool_input?.file_path;
  if (typeof fp === "string") {
    const cwd = input.cwd || process.cwd();
    const projectDir = process.env.CLAUDE_PROJECT_DIR || cwd;
    const abs = path.resolve(cwd, fp);
    const ext = path.extname(abs).toLowerCase();
    if (existsSync(abs)) {
      if (PRETTIER_EXT.has(ext)) {
        const prettier = localBin(projectDir, "prettier");
        if (prettier) run(prettier, ["--write", "--log-level", "silent", abs], projectDir);
      } else if (ext === ".py") {
        run("ruff", ["format", "--quiet", abs], projectDir);
      }
    }
  }
} catch {
  // never block
}
process.exit(0);
