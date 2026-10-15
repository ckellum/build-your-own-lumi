// The "Build with Claude Code" path: a switch, a prompt in every step, and the repo files
// Claude Code reads when someone opens the kit.
import test from "node:test";
import assert from "node:assert";
import { readFileSync, existsSync } from "node:fs";
import { WAYS } from "../js/picker.js";

const root = new URL("../", import.meta.url);
const read = (path) => readFileSync(new URL(path, root), "utf8");
const page = read("index.html");
const css = read("css/site.css");

test("the picker offers both ways to build, by hand first", () => {
  assert.deepEqual(WAYS, ["hand", "claude"]);
  assert.match(page, /data-set-way="hand"/);
  assert.match(page, /data-set-way="claude"/);
  assert.match(read("js/site.js"), /bindChoice\("way", WAYS, "hand"\)/);
});

test("phones get the switch in the Claude Code section, not a third row in the sticky bar", () => {
  assert.match(css, /\.picker-group\.way \{ display: none; \}/);
  const section = page.split('<section id="claude-code">')[1].split("</section>")[0];
  assert.match(section, /data-set-way="hand"[\s\S]*data-set-way="claude"/);
});

test("the page hides the other way's blocks", () => {
  assert.match(css, /:root\[data-way="hand"\] \[data-way-only\]:not\(\[data-way-only~="hand"\]\)/);
  assert.match(css, /:root\[data-way="claude"\] \[data-way-only\]:not\(\[data-way-only~="claude"\]\)/);
});

test("every build step has a Claude Code prompt to copy", () => {
  const steps = page.split('<article class="step"').slice(1);
  assert.equal(steps.length, 9);
  steps.forEach((step, i) => {
    const ask = step.match(/<div class="ask" data-way-only="claude">([\s\S]*?)<\/div>/);
    assert.ok(ask, `step ${i} has no Claude Code prompt`);
    assert.match(ask[1], /<pre><code>[\s\S]+<\/code><\/pre>/, `step ${i}'s prompt is not copyable`);
  });
});

test("there is a section on building with Claude Code, linked from the steps", () => {
  assert.match(page, /<section id="claude-code">/);
  assert.match(page, /https:\/\/claude\.ai\/install\.sh/);
  assert.match(page, /href="#claude-code"/);
});

test("every slash command the page mentions exists in the repo", () => {
  const used = new Set([...page.matchAll(/<code>\/([a-z-]+)(?:\s[^<]*)?<\/code>/g)].map((m) => m[1]));
  for (const name of ["setup", "my-event", "make-it-yours"]) assert.ok(used.has(name), `page never mentions /${name}`);
  for (const name of used) {
    const file = new URL(`.claude/commands/${name}.md`, root);
    assert.ok(existsSync(file), `/${name} is on the page but .claude/commands/${name}.md is missing`);
    assert.match(readFileSync(file, "utf8"), /^---\ndescription: .+\n/, `/${name} needs a description`);
  }
});

test("CLAUDE.md tells Claude Code how to test and what never to commit", () => {
  const guide = read("CLAUDE.md");
  assert.match(guide, /uv run pytest -q/);
  assert.match(guide, /my-event\//);
  assert.match(guide, /config\.toml/);
});
