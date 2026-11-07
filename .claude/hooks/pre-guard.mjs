#!/usr/bin/env node
// PreToolUse guard. Exit 2 + stderr message = block the tool call. Exit 0 = allow.
// Blocks: pushes to main/master, force pushes, `rm -r` on / ~ $HOME,
// edits to .env files (except .env.example), and new .md files outside docs/ and .claude/.
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

const PROTECTED = new Set(["main", "master"]);

function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => (data += c));
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", () => resolve(""));
  });
}

function block(msg) {
  process.stderr.write(`[pre-guard] BLOCKED: ${msg}\n`);
  process.exit(2);
}

// Remove heredoc bodies (e.g. commit messages) so their text is not parsed as commands.
function stripHeredocs(cmd) {
  const lines = cmd.split("\n");
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    out.push(lines[i]);
    const tags = [...lines[i].matchAll(/<<-?\s*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1/g)].map((m) => m[2]);
    for (const tag of tags) {
      while (i + 1 < lines.length && lines[i + 1].trim() !== tag) i++;
      if (i + 1 < lines.length) i++; // skip terminator
    }
  }
  return out.join("\n");
}

// Tokenize respecting quotes; split into simple commands on ; && || | & and newlines (outside quotes).
function splitCommands(cmd) {
  const segments = [];
  let words = [];
  let cur = "";
  let has = false;
  let q = null;
  const endWord = () => {
    if (has) words.push(cur);
    cur = "";
    has = false;
  };
  const endSeg = () => {
    endWord();
    if (words.length) segments.push(words);
    words = [];
  };
  for (let i = 0; i < cmd.length; i++) {
    const c = cmd[i];
    if (q) {
      if (c === q) q = null;
      else if (c === "\\" && q === '"' && i + 1 < cmd.length) cur += cmd[++i];
      else cur += c;
      continue;
    }
    if (c === "'" || c === '"') {
      q = c;
      has = true;
    } else if (c === "\\" && i + 1 < cmd.length) {
      if (cmd[i + 1] !== "\n") {
        cur += cmd[i + 1];
        has = true;
      }
      i++;
    } else if (c === ";" || c === "|" || c === "&" || c === "\n" || c === "(" || c === ")") {
      endSeg();
    } else if (/\s/.test(c)) {
      endWord();
    } else {
      cur += c;
      has = true;
    }
  }
  endSeg();
  return segments;
}

const PREFIXES = new Set(["sudo", "env", "command", "exec", "nohup", "time", "xargs", "builtin", "then", "do", "else", "!"]);

// Index of the actual command word, skipping VAR=val assignments and wrappers like sudo/env.
function commandIndex(w) {
  let i = 0;
  while (i < w.length) {
    const t = w[i];
    if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(t)) i++;
    else if (PREFIXES.has(t)) {
      i++;
      while (i < w.length && w[i].startsWith("-")) i++;
    } else break;
  }
  return i < w.length ? i : -1;
}

const isCmd = (t, name) => t === name || new RegExp(`(^|[\\\\/])${name}(\\.exe)?$`).test(t);

function currentBranch(cwd) {
  try {
    return execFileSync("git", ["rev-parse", "--abbrev-ref", "HEAD"], {
      cwd,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 3000,
    }).trim();
  } catch {
    return "";
  }
}

function refTargetsProtected(ref) {
  let r = ref.replace(/^\+/, "");
  if (r.includes(":")) r = r.split(":").pop();
  r = r.replace(/^refs\/heads\//, "");
  return PROTECTED.has(r);
}

function checkGitPush(w, cwd) {
  // `git [global options] push ...` with git in command position.
  const gi = commandIndex(w);
  if (gi === -1 || !isCmd(w[gi], "git")) return;
  let pi = gi + 1;
  while (pi < w.length && w[pi].startsWith("-")) {
    if (["-C", "-c", "--git-dir", "--work-tree", "--namespace"].includes(w[pi])) pi++;
    pi++;
  }
  if (w[pi] !== "push") return;
  const args = w.slice(pi + 1);

  for (const a of args) {
    if (a === "--force" || a.startsWith("--force-with-lease") || a.startsWith("--force-if-includes")) {
      block(`force push is not allowed (${a}). Push a new branch instead.`);
    }
    if (/^-[a-zA-Z]+$/.test(a) && a.includes("f")) block(`force push is not allowed (${a}).`);
    if (a.startsWith("+") && a.length > 1) block(`force push via +refspec is not allowed (${a}).`);
  }

  const positional = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a.startsWith("-")) {
      if (["-o", "--push-option", "--repo", "--receive-pack", "--exec"].includes(a)) i++;
      continue;
    }
    positional.push(a);
  }
  const refs = positional.slice(1); // first positional = remote
  if (refs.some(refTargetsProtected)) block("pushing to main/master is not allowed. Open a PR from a feature branch.");
  if (refs.length === 0 || refs.includes("HEAD")) {
    const b = currentBranch(cwd);
    if (PROTECTED.has(b)) block(`you are on '${b}'; a bare push would update it. Switch to a feature branch.`);
  }
}

function checkRm(w) {
  const ri = commandIndex(w);
  if (ri === -1 || !isCmd(w[ri], "rm")) return;
  const args = w.slice(ri + 1);
  const recursive = args.some((a) => a === "--recursive" || (/^-[a-zA-Z]+$/.test(a) && /[rR]/.test(a)));
  if (!recursive) return;
  const dangerous = /^(\/|\/\*|~|~\/|~\/\*|\$HOME|\$HOME\/|\$HOME\/\*|\$\{HOME\}|\$\{HOME\}\/|\$\{HOME\}\/\*)$/;
  for (const a of args) {
    if (a.startsWith("-")) continue;
    if (dangerous.test(a)) block(`rm -r on '${a}' is not allowed.`);
  }
}

function isEnvFile(p) {
  const base = path.basename(p.replace(/\\/g, "/"));
  if (base === ".env.example") return false;
  return base === ".env" || base.startsWith(".env.");
}

function newMdAllowed(filePath, projectDir) {
  const norm = (p) => p.replace(/\\/g, "/");
  const base = path.basename(norm(filePath));
  if (base === "README.md" || base === "CLAUDE.md") return true;
  const rel = norm(path.relative(projectDir, filePath));
  return rel.startsWith("docs/") || rel.startsWith(".claude/");
}

const raw = await readStdin();
let input;
try {
  input = JSON.parse(raw);
} catch {
  process.exit(0);
}
if (!input || typeof input !== "object") process.exit(0);

const tool = input.tool_name || "";
const ti = input.tool_input || {};
const cwd = input.cwd || process.cwd();
const projectDir = process.env.CLAUDE_PROJECT_DIR || cwd;

try {
  if (tool === "Bash" && typeof ti.command === "string") {
    for (const w of splitCommands(stripHeredocs(ti.command))) {
      checkGitPush(w, cwd);
      checkRm(w);
    }
  }

  if (["Edit", "Write", "MultiEdit"].includes(tool) && typeof ti.file_path === "string") {
    const abs = path.resolve(cwd, ti.file_path);
    if (isEnvFile(abs)) block(`editing ${path.basename(abs)} is not allowed. Put new variables in .env.example.`);
    if (tool === "Write" && /\.md$/i.test(abs) && !existsSync(abs) && !newMdAllowed(abs, projectDir)) {
      block(`new .md files go under docs/ or .claude/ (got ${ti.file_path}).`);
    }
  }
} catch {
  process.exit(0);
}
process.exit(0);
