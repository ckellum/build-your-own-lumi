import test from "node:test";
import assert from "node:assert";
import { readChoice, saveChoice, applyChoice } from "../js/picker.js";

const blocked = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };

test("blocked storage falls back to the default", () =>
  assert.equal(readChoice(blocked, "tier", ["laptop", "cloud"], "laptop"), "laptop"));
test("saving to blocked storage does not throw", () =>
  assert.doesNotThrow(() => saveChoice(blocked, "tier", "cloud")));
test("missing storage falls back", () =>
  assert.equal(readChoice(undefined, "tier", ["laptop"], "laptop"), "laptop"));
test("a stored value that is not allowed falls back", () =>
  assert.equal(readChoice({ getItem: () => "potato" }, "tier", ["laptop"], "laptop"), "laptop"));
test("a stored allowed value is used", () =>
  assert.equal(readChoice({ getItem: () => "cloud" }, "tier", ["laptop", "cloud"], "laptop"), "cloud"));
test("applyChoice sets the data attribute", () => {
  const root = { dataset: {} };
  applyChoice(root, "tier", "cloud");
  assert.equal(root.dataset.tier, "cloud");
});
