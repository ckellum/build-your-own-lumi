// Listens to minilumi over Server-Sent Events and animates the avatar.
const main = document.querySelector("main");
const mouth = document.querySelector(".mouth");
const caption = document.querySelector(".caption");
const heard = document.querySelector(".heard");
const visitor = document.querySelector(".visitor");
const stateLabel = document.querySelector(".state");
let talk = null;   // { envelope, stepMs, startedAt }

function setState(state) {
  main.dataset.state = state;
  stateLabel.textContent = state;
}

function frame(now) {
  let open = 0;
  if (talk) {
    const i = Math.floor((now - talk.startedAt) / talk.stepMs);
    if (i < talk.envelope.length) open = talk.envelope[i];
    else talk = null;
  }
  mouth.style.height = `${4 + open * 14}%`;
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

function handle(msg) {
  if (msg.type === "state") setState(msg.state);
  if (msg.type === "visitor") {
    visitor.textContent = msg.name ? `Hi, ${msg.name}` : "";
    if (!msg.name) { heard.textContent = ""; caption.textContent = "Press Enter or scan a badge to start."; }
  }
  if (msg.type === "heard") heard.textContent = `“${msg.text}”`;
  if (msg.type === "say") {
    caption.textContent = msg.text;
    talk = { envelope: msg.envelope, stepMs: msg.step_ms, startedAt: performance.now() };
  }
}

const events = new EventSource("/events");
events.onmessage = (e) => handle(JSON.parse(e.data));
events.onerror = () => setState("reconnecting");
