// The hardware picker and depth switch: remember a choice, apply it to the page.
// No DOM access at import time, so this module is testable in Node.

export const TIERS = ["workstation", "laptop", "cloud"];
export const LEVELS = ["beginner", "intermediate", "expert"];
export const WAYS = ["hand", "claude"];        // build it yourself, or with Claude Code

export function readChoice(storage, key, allowed, fallback) {
  try {
    const value = storage?.getItem(key);
    return allowed.includes(value) ? value : fallback;
  } catch {
    return fallback;   // private mode or blocked storage: the page still works
  }
}

export function saveChoice(storage, key, value) {
  try {
    storage?.setItem(key, value);
  } catch {
    /* nothing to do: the choice just won't be remembered */
  }
}

export function applyChoice(root, attr, value) {
  root.dataset[attr] = value;
}
