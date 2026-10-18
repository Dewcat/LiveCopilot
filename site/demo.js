// Website-only demonstrations. No microphone, model, or provider requests.
(() => {
  "use strict";
  document.documentElement.classList.add("js");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const hero = document.querySelector(".hero");
// Reserve the final title geometry; only glyph visibility changes.
if (!reduced.matches) {
  const letters = [...document.querySelectorAll(".title-character")];
  hero.classList.add("typing");
  let count = 0;
  const cursor = document.querySelector(".title-cursor");
  const placeCursor = () => {
    const glyph =
      letters[
        Math.max(0, Math.min(count - 1, letters.length - 1))
      ].getBoundingClientRect();
    const heading = document
      .querySelector("#hero-heading")
      .getBoundingClientRect();
    cursor.style.transform = `translate(${(count ? glyph.right : glyph.left) - heading.left + 5}px, ${glyph.top - heading.top + glyph.height * 0.15}px)`;
  };
  placeCursor();
  const interval = setInterval(() => {
    if (reduced.matches || document.hidden) count = letters.length;
    else count += document.documentElement.lang === "en" ? 3 : 1;
    letters.slice(0, count).forEach((c) => c.classList.add("revealed"));
    placeCursor();
    if (count >= letters.length) {
      clearInterval(interval);
      hero.classList.remove("typing");
      hero.classList.add("typed");
    }
  }, 55);
}

  const english = document.documentElement.lang === "en";
  const menu = document.querySelector(".menu-toggle");
  const links = document.querySelector(".nav-links");
  const closeMenu = () => {
    links.classList.remove("open");
    menu.setAttribute("aria-expanded", "false");
  };
  menu.addEventListener("click", () =>
    menu.setAttribute("aria-expanded", String(links.classList.toggle("open"))),
  );
  links.addEventListener("click", (event) => {
    if (event.target.closest("a")) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && links.classList.contains("open")) {
      closeMenu();
      menu.focus();
    }
  });
  const header = document.querySelector(".site-header");
  const updateHeader = () => header.classList.toggle("scrolled", hero.getBoundingClientRect().bottom < 100);
  window.addEventListener("scroll", updateHeader, { passive: true });
  updateHeader();
  const part = (root, name) => root.querySelector(`[data-part="${name}"]`);
  const text = (node, value) => {
    if (node.textContent !== value) node.textContent = value;
  };
  // Chunk boundaries follow phrases, never individual characters.
  function chunks(value) {
    if (/[\u3400-\u9fff]/.test(value))
      return value.match(/[^，。！？；]+[，。！？；]?/g) || [value];
    return value.match(/(?:\S+\s*){1,5}/g) || [value];
  }
  function stream(node, parts, progress) {
    text(
      node,
      parts
        .slice(0, Math.ceil(Math.max(0, Math.min(1, progress)) * parts.length))
        .join("") || "\u00a0",
    );
  }
  // Fit the native 540px panel into the fixed hardware screen; never animate geometry.
  const screen = document.querySelector(".hero-screen");
  new ResizeObserver(([entry]) => {
    const panel = document.querySelector(".hero-product-live");
    const nativeHeight = panel.offsetHeight;
    const bounds = screen.getBoundingClientRect();
    const right = bounds.right - entry.contentRect.width * .025;
    const visibleWidth = right - Math.max(20, bounds.left + 20);
    const availableWidth = Math.min(entry.contentRect.width * .76, visibleWidth - 18);
    const scale = Math.min(availableWidth / 540, entry.contentRect.height * .86 / nativeHeight);
    screen.style.setProperty("--screen-scale", String(scale));
  }).observe(screen);
  const demo = document.querySelector("#hero-demo");
  const product = document.querySelector('[data-product="hero"]');
  const transcript = part(product, "transcript");
  const answer = part(product, "answer");
  const phaseText = part(product, "phase");
  const status = document.querySelector("#demo-status");
  const toggle = document.querySelector(".demo-toggle");
  const fullQuestion = transcript.textContent;
  const fullAnswer = answer.textContent;
  const questionChunks = chunks(fullQuestion);
  const answerChunks = chunks(fullAnswer);
  const timeline = [
    { at: 0, state: "listening" },
    { at: 500, state: "transcribing" },
    { at: 3000, state: "understanding" },
    { at: 3600, state: "retrieving" },
    { at: 5200, state: "organizing" },
    { at: 6000, state: "answering" },
    { at: 9000, state: "sources" },
    { at: 9500, state: "complete" },
  ];
  const duration = 12000;
  let heroTime = 0,
    heroVisible = false,
    paused = false;
  const heroClock = { previous: 0, frame: 0 };
  function stateAt(time) {
    return [...timeline].reverse().find((item) => time >= item.at).state;
  }
  function renderHero(time) {
    const state = stateAt(time);
    demo.dataset.state = state;
    stream(transcript, questionChunks, (time - 500) / 2500);
    stream(answer, answerChunks, (time - 6000) / 3000);
    part(product, "empty").hidden = time >= 3000;
    part(product, "question").hidden = time < 3000;
    part(product, "loading").hidden = time < 3000 || time >= 6000;
    part(product, "response").hidden = time < 6000;
    part(product, "evidence").hidden = time < 9000;
    part(product, "sources").hidden = time < 9000;
    text(
      phaseText,
      time < 3000
        ? english
          ? "Listening"
          : (document.documentElement.lang === "zh-Hant" ? "正在聆聽" : "正在监听")
        : time < 9000
          ? english
            ? "Assistance in progress"
            : (document.documentElement.lang === "zh-Hant" ? "正在生成建議" : "正在生成建议")
          : english
            ? "Question ready"
            : (document.documentElement.lang === "zh-Hant" ? "問題已完整" : "问题已完整"),
    );
    const key = ["complete", "sources", "resetting"].includes(state)
      ? "complete"
      : state === "transcribing"
        ? "listening"
        : state;
    text(status, demo.dataset[key]);
  }
  function finalHero() {
    renderHero(12000);
    text(transcript, fullQuestion);
    text(answer, fullAnswer);
  }
  function tickHero(now) {
    if (heroClock.previous)
      heroTime = Math.min(duration, heroTime + now - heroClock.previous);
    heroClock.previous = now;
    renderHero(heroTime);
    if (heroTime < duration) heroClock.frame = requestAnimationFrame(tickHero);
    else {
      heroClock.frame = 0;
      toggle.hidden = true;
      finalHero();
    }
  }
  function syncHero() {
    cancelAnimationFrame(heroClock.frame);
    heroClock.frame = 0;
    heroClock.previous = 0;
    const sourcesOpen = [...product.querySelectorAll("details")].some(
      (item) => item.open,
    );
    if (reduced.matches) {
      heroTime = duration;
      finalHero();
    } else if (
      heroTime < duration &&
      heroVisible &&
      !document.hidden &&
      !paused &&
      !sourcesOpen
    )
      heroClock.frame = requestAnimationFrame(tickHero);
    toggle.hidden = reduced.matches || heroTime >= duration;
    toggle.textContent = paused ? "▶" : "Ⅱ";
    toggle.setAttribute(
      "aria-label",
      paused ? toggle.dataset.play : toggle.dataset.pause,
    );
  }
  toggle.addEventListener("click", () => {
    paused = !paused;
    syncHero();
  });
  product
    .querySelectorAll("details")
    .forEach((item) => item.addEventListener("toggle", syncHero));
  product.querySelector("input").addEventListener("focus", () => {
    paused = true;
    heroTime = 12000;
    finalHero();
    syncHero();
  });
  new IntersectionObserver(
    (entries) => {
      heroVisible = entries[0].isIntersecting;
      syncHero();
    },
    { threshold: 0 },
  ).observe(demo);
  window.addEventListener(
    "scroll",
    () => {
      if (demo.getBoundingClientRect().bottom < 0 && heroTime < duration) {
        heroTime = duration;
        finalHero();
        syncHero();
      }
    },
    { passive: true },
  );
  document.addEventListener("visibilitychange", syncHero);
  reduced.addEventListener("change", syncHero);
  // Native Copy has a real browser action; the remaining native chrome is a labeled visual replica.
  document.querySelectorAll(".product-copy").forEach((button) =>
    button.addEventListener("click", async () => {
      const value = part(
        button.closest("[data-product]"),
        "answer",
      ).textContent;
      try {
        await navigator.clipboard.writeText(value);
        button.textContent = button.dataset.copied;
      } catch {
        button.textContent = button.dataset.label;
      }
    }),
  );
  // Workflow: one six-second sequence, paused offscreen, final state retained.
  const workflow = document.querySelector(".workflow");
  const nodes = [...workflow.children];
  const workflowTranscript = document.querySelector(
    "[data-workflow-transcript]",
  );
  let workflowTime = 0,
    workflowVisible = false,
    workflowStarted = false,
    workflowPrevious = 0,
    workflowFrame = 0;
  if (!reduced.matches) workflow.classList.add("pending");
  function tickWorkflow(now) {
    if (workflowPrevious) workflowTime += now - workflowPrevious;
    workflowPrevious = now;
    nodes.forEach((node, index) =>
      node.classList.toggle("active", workflowTime >= index * 1500),
    );
    stream(workflowTranscript, questionChunks, workflowTime / 1300);
    if (workflowTime < 6000)
      workflowFrame = requestAnimationFrame(tickWorkflow);
    else {
      workflow.classList.remove("pending");
      workflowFrame = 0;
    }
  }
  function syncWorkflow() {
    cancelAnimationFrame(workflowFrame);
    workflowFrame = 0;
    workflowPrevious = 0;
    if (reduced.matches) {
      workflowTime = 6000;
      workflow.classList.remove("pending");
      text(workflowTranscript, fullQuestion);
    } else if (
      workflowVisible &&
      workflowStarted &&
      !document.hidden &&
      workflowTime < 6000
    )
      workflowFrame = requestAnimationFrame(tickWorkflow);
  }
  new IntersectionObserver(
    (entries) => {
      workflowVisible = entries[0].isIntersecting;
      if (entries[0].intersectionRatio >= 0.45) workflowStarted = true;
      syncWorkflow();
    },
    { threshold: [0, 0.45] },
  ).observe(workflow);
  document.addEventListener("visibilitychange", syncWorkflow);
  reduced.addEventListener("change", syncWorkflow);
  // The real OverlayWindow fades out completely. It leaves no persistent handle.
  const desktop = document.querySelector(".desktop-preview");
  const edgeButton = document.querySelector(".edge-toggle");
  const edgeNote = document.querySelector(".edge-note");
  const edgeSlot = document.querySelector(".edge-product-slot");
  function tuck(value) {
    desktop.classList.toggle("tucked", value);
    edgeSlot.inert = value;
    edgeButton.setAttribute("aria-pressed", String(value));
    edgeButton.textContent = value
      ? edgeButton.dataset.reveal
      : edgeButton.dataset.hide;
    edgeNote.textContent = value
      ? edgeNote.dataset.hidden
      : edgeNote.dataset.visible;
  }
  edgeButton.addEventListener("click", () =>
    tuck(!desktop.classList.contains("tucked")),
  );
  const zone = document.querySelector(".edge-reveal-zone");
  zone.addEventListener("pointerenter", (event) => {
    if (event.pointerType === "mouse") tuck(false);
  });
  zone.addEventListener("click", () => tuck(false));
  // Responsive scaling changes only the miniature desktop demonstration, not the Hero.
  let edgeWidth = -1,
    edgeResizeFrame = 0;
  new ResizeObserver((entries) => {
    const width = entries[0].contentRect.width;
    if (Math.abs(width - edgeWidth) < 1) return;
    edgeWidth = width;
    cancelAnimationFrame(edgeResizeFrame);
    edgeResizeFrame = requestAnimationFrame(() => {
      const scale = Math.min(1, (width - 24) / 400);
      edgeSlot.style.transform = `scale(${scale})`;
      desktop.style.height = `${Math.ceil(240 * scale + 30)}px`;
    });
  }).observe(desktop);
  // One finite caption example, using the same transcript fragment as the Hero.
  const captionRoot = document.querySelector('[data-product="transcript"]');
  const caption = part(captionRoot, "transcript");
  let captionTime = 0,
    captionLast = 0,
    captionFrame = 0,
    captionVisible = false;
  function tickCaption(now) {
    if (captionLast) captionTime += now - captionLast;
    captionLast = now;
    stream(caption, questionChunks, captionTime / 3000);
    if (captionTime < 3000) captionFrame = requestAnimationFrame(tickCaption);
    else captionFrame = 0;
  }
  function syncCaption() {
    cancelAnimationFrame(captionFrame);
    captionFrame = 0;
    captionLast = 0;
    if (reduced.matches) {
      text(caption, fullQuestion);
      captionTime = 3000;
    } else if (captionVisible && !document.hidden && captionTime < 3000)
      captionFrame = requestAnimationFrame(tickCaption);
  }
  new IntersectionObserver(
    (entries) => {
      captionVisible = entries[0].isIntersecting;
      syncCaption();
    },
    { threshold: 0.4 },
  ).observe(captionRoot);
  document.addEventListener("visibilitychange", syncCaption);
  reduced.addEventListener("change", syncCaption);
  const ambient = [
    ...document.querySelectorAll(".architecture,.privacy-route"),
  ];
  const ambientObserver = new IntersectionObserver(
    (entries) =>
      entries.forEach((entry) => {
        if (entry.isIntersecting && !reduced.matches)
          entry.target.classList.add("flow-shown");
      }),
    { threshold: 0.4 },
  );
  ambient.forEach((node) => ambientObserver.observe(node));
  // Native disclosures work without JS. Deep links additionally open them.
  function revealDetails() {
    const target = document.getElementById(location.hash.slice(1));
    if (target instanceof HTMLDetailsElement) target.open = true;
  }
  window.addEventListener("hashchange", revealDetails);
  revealDetails();
  document.querySelectorAll('a[href^="#"]').forEach((link) =>
    link.addEventListener("click", () => {
      const target = document.getElementById(link.hash.slice(1));
      if (target instanceof HTMLDetailsElement) target.open = true;
    }),
  );
  const cases = JSON.parse(document.getElementById("demo-examples").textContent);
  const tabs = [...document.querySelectorAll("[data-case]")];
  const panel = document.querySelector("#case-panel");
  const caseProduct = document.querySelector('[data-product="case"]');
  let panelAnimation;
  function selectCase(tab) {
    tabs.forEach((button) => {
      button.setAttribute("aria-selected", String(button === tab));
      button.tabIndex = button === tab ? 0 : -1;
    });
    const example = cases[tab.dataset.case];
    panel.setAttribute("aria-labelledby", tab.id);
    document.querySelector("#case-question").textContent = example.question;
    document.querySelector("#case-passage").textContent = example.passage;
    document.querySelector("#case-response-title").textContent = example.title;
    part(caseProduct, "answer").textContent = example.answer;
    part(caseProduct, "question").textContent = example.question;
    part(caseProduct, "source-label").textContent = example.sources[0];
    part(caseProduct, "source-label-2").textContent = example.sources[1];
    part(caseProduct, "source-passage").textContent = example.passage;
    part(caseProduct, "source-passage-2").textContent = example.sourcePassage2;
    caseProduct
      .querySelectorAll("details")
      .forEach((item) => (item.open = false));
    document.querySelector("#case-documents").replaceChildren(
      ...example.documents.map((name) => {
        const span = document.createElement("span");
        span.textContent = name;
        return span;
      }),
    );
    panelAnimation?.cancel();
    if (!reduced.matches)
      panelAnimation = panel.animate([{ opacity: 0.6 }, { opacity: 1 }], {
        duration: 250,
        easing: "ease-out",
      });
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => selectCase(tab));
    tab.addEventListener("keydown", (event) => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft")
        next = (index + tabs.length - 1) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next !== undefined) {
        event.preventDefault();
        tabs[next].focus();
        selectCase(tabs[next]);
      }
    });
  });
  selectCase(document.querySelector('[data-case="meeting"]'));
})();
