#!/usr/bin/env node
// Stop hook: quick checks on files changed since HEAD (plus untracked files).
// 1) stray console.log in js/ts  2) tsc --noEmit if TS changed  3) ruff check on changed .py
// Problems -> stderr + exit 2 (Claude keeps working). Clean -> exit 0.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

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

function sh(cmd, args, cwd, timeout = 15000) {
  const r = spawnSync(cmd, args, {
    cwd,
    encoding: "utf8",
    timeout,
    maxBuffer: 16 * 1024 * 1024,
    shell: isWin && /\.cmd$/i.test(cmd),
  });
  return r;
}

function lines(s) {
  return (s || "").split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
}

function localBin(dir, name) {
  const base = path.join(dir, "node_modules", ".bin", name);
  for (const p of isWin ? [`${base}.cmd`, `${base}.exe`, base] : [base]) if (existsSync(p)) return p;
  return null;
}

if (process.env.HACK_SKIP_STOP_CHECK === "1") process.exit(0);

let input = {};
try {
  input = JSON.parse(await readStdin()) || {};
} catch {
  input = {};
}
if (input.stop_hook_active === true) process.exit(0);

const dir = process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd();

let changed = [];
try {
  const diff = sh("git", ["diff", "--name-only", "HEAD"], dir);
  const untracked = sh("git", ["ls-files", "--others", "--exclude-standard"], dir);
  if (diff.status !== 0 && untracked.status !== 0) process.exit(0); // not a git repo
  changed = [...new Set([...lines(diff.stdout), ...lines(untracked.stdout)])]
    .map((f) => f.replace(/\\/g, "/"))
    .filter((f) => existsSync(path.join(dir, f)));
} catch {
  process.exit(0);
}
if (changed.length === 0) process.exit(0);

const problems = [];

// 1. console.log
const JS = /\.(js|jsx|ts|tsx)$/;
const SKIP = (f) => /(^|\/)(scripts|\.claude)\//.test(f) || /\.(test|spec)\.[jt]sx?$/.test(f) || /(^|\/)(__tests__|tests?)\//.test(f);
for (const f of changed.filter((f) => JS.test(f) && !SKIP(f))) {
  try {
    readFileSync(path.join(dir, f), "utf8")
      .split(/\r?\n/)
      .forEach((line, i) => {
        if (line.includes("console.log(") && !line.includes("// keep")) {
          problems.push(`${f}:${i + 1}: console.log left in code (add "// keep" if intentional)`);
        }
      });
  } catch {
    /* unreadable file: skip */
  }
}

// 2. TypeScript
if (changed.some((f) => /\.tsx?$/.test(f)) && existsSync(path.join(dir, "tsconfig.json"))) {
  const tsc = localBin(dir, "tsc");
  if (tsc) {
    const r = sh(tsc, ["--noEmit", "-p", "."], dir, 90000);
    const timedOut = r.error && r.error.code === "ETIMEDOUT";
    if (!timedOut && r.status !== 0 && r.status !== null) {
      const out = lines(`${r.stdout || ""}\n${r.stderr || ""}`).slice(0, 30);
      if (out.length) problems.push("tsc --noEmit failed:", ...out.map((l) => `  ${l}`));
    }
  }
}

// 3. Python
const py = changed.filter((f) => f.endsWith(".py"));
if (py.length) {
  const probe = sh("ruff", ["--version"], dir, 5000);
  if (!probe.error && probe.status === 0) {
    // Errors only (syntax, undefined names, unused imports). Style rules vary by ruff version and would nag on teammates' code.
    const r = sh("ruff", ["check", "--quiet", "--select", "E9,F", ...py], dir, 30000);
    if (r.status !== 0 && r.status !== null) {
      const out = lines(`${r.stdout || ""}\n${r.stderr || ""}`).slice(0, 30);
      if (out.length) problems.push("ruff check failed:", ...out.map((l) => `  ${l}`));
    }
  }
}

if (problems.length) {
  process.stderr.write(`[stop-check] Fix before finishing (set HACK_SKIP_STOP_CHECK=1 to skip):\n${problems.join("\n")}\n`);
  process.exit(2);
}
process.exit(0);
