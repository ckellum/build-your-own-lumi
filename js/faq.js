// FAQ: search across questions and answers; a link to #question opens it.
const items = [...document.querySelectorAll(".faq-group details")];
const search = document.getElementById("faq-search");
const count = document.getElementById("faq-count");

function filter() {
  const words = search.value.toLowerCase().split(/\s+/).filter(Boolean);
  let shown = 0;
  for (const item of items) {
    const hit = words.every((w) => item.textContent.toLowerCase().includes(w));
    item.hidden = !hit;
    if (hit) shown += 1;
    if (words.length) item.open = hit;
  }
  for (const group of document.querySelectorAll(".faq-group")) {
    group.hidden = ![...group.querySelectorAll("details")].some((d) => !d.hidden);
  }
  count.textContent = words.length ? `${shown} of ${items.length} questions` : `${items.length} questions`;
}

function openFromHash() {
  const target = location.hash && document.getElementById(location.hash.slice(1));
  if (target && target.tagName === "DETAILS") { target.open = true; target.scrollIntoView({ block: "start" }); }
}

if (search) {
  search.addEventListener("input", filter);
  filter();
}
addEventListener("hashchange", openFromHash);
openFromHash();
