import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright";

import { axeOptions, blockingImpacts } from "./axe.config.mjs";
import { repositoryRootFromModuleUrl } from "./qa-paths.mjs";

const sizes = [
  { name: "phone", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1440, height: 900 },
  { name: "narrow", width: 320, height: 800 },
];

function parseArguments(argv) {
  const htmlPath = argv[2];
  if (!htmlPath) throw new Error("Usage: npm run qa:ui -- PATH [--profiles phone,desktop]");
  const profileIndex = argv.indexOf("--profiles");
  const requested = profileIndex >= 0 ? argv[profileIndex + 1]?.split(",") : sizes.map(({ name }) => name);
  const unknown = (requested || []).filter((name) => !sizes.some((size) => size.name === name));
  if (unknown.length) throw new Error(`Unknown QA profiles: ${unknown.join(", ")}`);
  return {
    htmlPath: path.resolve(htmlPath),
    profiles: sizes.filter(({ name }) => requested.includes(name)),
  };
}

function numericMaximum(current, candidate) {
  if (candidate == null || Number.isNaN(candidate)) return current;
  return current == null ? candidate : Math.max(current, candidate);
}

async function coreIsReadable(page) {
  return page.evaluate(() => {
    const heading = document.querySelector("h1");
    const route = document.querySelector("#route-overview");
    const day = document.querySelector("[data-day]");
    const sources = document.querySelector("#sources");
    return Boolean(
      heading?.textContent.trim() &&
        route?.textContent.trim() &&
        day?.textContent.trim() &&
        sources?.textContent.trim(),
    );
  });
}

async function measureInteraction(page) {
  const filter = page.locator('[data-filter="warning"]');
  if ((await filter.count()) === 0) return null;
  return page.evaluate(async () => {
    const button = document.querySelector('[data-filter="warning"]');
    const started = performance.now();
    button.click();
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    return performance.now() - started;
  });
}

async function filtersStaySynchronized(page) {
  const weatherFilter = page.locator('[data-filter="weather"]');
  if ((await weatherFilter.count()) === 0) return false;
  await weatherFilter.click();
  const synchronized = await page.evaluate(() => {
    const articles = Array.from(document.querySelectorAll("[data-day]"));
    const overviewMatches = articles.every((article) => {
      const overview = document.querySelector(`[data-day-overview="${article.id}"]`);
      return overview && overview.hidden === article.hidden;
    });
    const visibleCount = articles.filter((article) => !article.hidden).length;
    const resultText = document.querySelector("[data-filter-results]")?.textContent || "";
    return overviewMatches && resultText.startsWith(String(visibleCount));
  });
  const search = page.locator("[data-day-search]");
  await search.fill("a query that cannot match any itinerary day");
  const emptyStateVisible = await page.locator("[data-filter-empty]").isVisible();
  await page.locator("[data-reset-filters]").click();
  const restored = await page.evaluate(
    () =>
      Array.from(document.querySelectorAll("[data-day], [data-day-overview]")).every(
        (item) => !item.hidden,
      ) && document.querySelector("[data-day-search]")?.value === "",
  );
  return synchronized && emptyStateVisible && restored;
}

async function mobilePriorityIsVisible(page) {
  return page.evaluate(() => {
    const required = [
      document.querySelector("h1"),
      document.querySelector(".route-ribbon"),
      document.querySelector(".readiness-panel"),
      document.querySelector(".budget-panel"),
      document.querySelector(".hero-aside .warning-block"),
    ];
    return required.every((element) => {
      if (!element) return false;
      const rect = element.getBoundingClientRect();
      return rect.top >= 0 && rect.bottom <= window.innerHeight;
    });
  });
}

async function countUndersizedTouchTargets(page) {
  return page.evaluate(() => {
    const selector = [
      "button",
      "input",
      "summary",
      ".summary-counts a",
      ".readiness-panel a",
      ".day-overview a",
      ".external-link",
      ".day-nav a",
      ".source-url",
    ].join(",");
    return Array.from(document.querySelectorAll(selector)).filter((control) => {
      if (control.closest("[hidden], details:not([open])")) return false;
      const rect = control.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.height < 44;
    }).length;
  });
}

async function keyboardFocusIsVisible(page) {
  await page.keyboard.press("Tab");
  return page.evaluate(() => {
    const active = document.activeElement;
    if (!active || active === document.body) return false;
    const style = getComputedStyle(active);
    return parseFloat(style.outlineWidth || "0") >= 3 && style.outlineStyle !== "none";
  });
}

async function testNoJavaScript(browser, url) {
  const context = await browser.newContext({
    javaScriptEnabled: false,
    viewport: { width: 390, height: 844 },
  });
  try {
    const page = await context.newPage();
    await page.goto(url, { waitUntil: "load" });
    const scenarios = await page.locator("[data-scenario]").count();
    return (await coreIsReadable(page)) && scenarios >= 2;
  } finally {
    await context.close();
  }
}

async function testEquivalentZoom(browser, url) {
  const context = await browser.newContext({ viewport: { width: 320, height: 800 } });
  try {
    const page = await context.newPage();
    await page.goto(url, { waitUntil: "load" });
    return await page.evaluate(() => {
      const root = document.documentElement;
      const controls = Array.from(document.querySelectorAll("button, input, summary, a")).filter(
        (control) => !control.closest("details:not([open])") && !control.closest("[hidden]"),
      );
      return (
        root.scrollWidth <= root.clientWidth + 1 &&
        controls.every((control) => {
          const rect = control.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0;
        })
      );
    });
  } finally {
    await context.close();
  }
}

async function testThirtyDayMemory(page) {
  return page.evaluate(() => {
    const container = document.querySelector("#detailed-days");
    const source = document.querySelector("[data-day]");
    if (!container || !source) return null;
    const existing = document.querySelectorAll("[data-day]").length;
    const clones = [];
    try {
      for (let index = existing; index < 30; index += 1) {
        const clone = source.cloneNode(true);
        clone.id = `stress-day-${index + 1}`;
        clone.querySelectorAll("[id]").forEach((element) => element.removeAttribute("id"));
        container.append(clone);
        clones.push(clone);
      }
      return performance.memory?.usedJSHeapSize ?? null;
    } finally {
      clones.forEach((clone) => clone.remove());
    }
  });
}

async function captureStateMatrix(page, baselineDirectory, finalUrl) {
  const stateDirectory = path.join(baselineDirectory, "states");
  await fs.mkdir(stateDirectory, { recursive: true });
  const finalPage = await page.context().newPage();
  let validFinal = false;
  try {
    await finalPage.goto(finalUrl, { waitUntil: "load" });
    validFinal = await finalPage.evaluate(() => {
      const status = document.querySelector(".document-status")?.textContent.trim();
      const readiness = document.querySelector(".readiness-panel strong")?.textContent.trim();
      const readinessMatch = readiness?.match(/^(\d+) of (\d+) confirmed$/);
      return (
        status === "Final — проверено в Codex" &&
        readinessMatch?.[1] === readinessMatch?.[2] &&
        !document.querySelector(".hero-aside .warning-block") &&
        !document.querySelector(".status--blocking") &&
        !document.querySelector("#open-decisions .decision-item")
      );
    });
    await finalPage.locator(".trip-hero").screenshot({
      path: path.join(stateDirectory, "final.png"),
    });
  } finally {
    await finalPage.close();
  }

  await page.locator("[data-day]").first().evaluate((day) => {
    const figure = document.createElement("figure");
    figure.className = "day-photo media-unavailable qa-media-state";
    figure.dataset.optionalMedia = "";
    figure.innerHTML =
      '<p class="media-fallback" data-media-fallback>Photo unavailable; the day plan remains complete.</p>' +
      "<figcaption>Optional media failure state</figcaption>";
    day.querySelector(".day-heading")?.after(figure);
  });
  await page.locator(".qa-media-state").screenshot({
    path: path.join(stateDirectory, "media-failure.png"),
  });
  await page.locator(".qa-media-state").evaluate((element) => element.remove());

  const enhancementState = await page.evaluate(() => {
    document.documentElement.classList.add("enhancement-failed");
    const notice = document.querySelector("[data-enhancement-error]");
    if (notice) notice.hidden = false;
    return Array.from(document.querySelectorAll(".interactive-controls")).every(
      (control) => getComputedStyle(control).display === "none",
    );
  });
  await page.locator("[data-enhancement-error]").screenshot({
    path: path.join(stateDirectory, "enhancement-failure.png"),
  });
  await page.evaluate(() => {
    document.documentElement.classList.remove("enhancement-failed");
    const notice = document.querySelector("[data-enhancement-error]");
    if (notice) notice.hidden = true;
  });

  const outputs = ["final.png", "media-failure.png", "enhancement-failure.png"];
  const sizes = await Promise.all(outputs.map((name) => fs.stat(path.join(stateDirectory, name))));
  return validFinal && enhancementState && sizes.every((stat) => stat.size > 1000);
}

async function run() {
  const { htmlPath, profiles } = parseArguments(process.argv);
  await fs.access(htmlPath);
  const url = pathToFileURL(htmlPath).href;
  const repositoryRoot = repositoryRootFromModuleUrl(import.meta.url);
  const finalHtmlPath = path.join(repositoryRoot, "tests", "ui", "state-fixtures", "final.html");
  await fs.access(finalHtmlPath);
  const finalUrl = pathToFileURL(finalHtmlPath).href;
  const baselineDirectory =
    process.env.TRAVEL_PLANNER_QA_BASELINES || path.join(repositoryRoot, "tests", "ui", "visual-baselines");
  await fs.mkdir(baselineDirectory, { recursive: true });

  const report = {
    accessibility_critical: 0,
    accessibility_serious: 0,
    horizontal_overflow_count: 0,
    first_useful_ms: null,
    cumulative_layout_shift: null,
    interaction_ms: null,
    focus_visible: true,
    no_js_core: false,
    offline_core: true,
    zoom_200_core: false,
    reduced_motion_core: true,
    external_asset_requests: 0,
    undersized_touch_targets: 0,
    filter_sync: false,
    mobile_priority_visible: false,
    state_matrix_complete: false,
    file_size_bytes: (await fs.stat(htmlPath)).size,
    peak_memory_bytes: null,
    errors: [],
  };

  const browser = await chromium.launch({ headless: true });
  try {
    for (const profile of profiles) {
      const context = await browser.newContext({
        viewport: { width: profile.width, height: profile.height },
        colorScheme: "light",
        reducedMotion: "reduce",
      });
      await context.addInitScript(() => {
        window.__travelPlannerCls = 0;
        new PerformanceObserver((entries) => {
          for (const entry of entries.getEntries()) {
            if (!entry.hadRecentInput) window.__travelPlannerCls += entry.value;
          }
        }).observe({ type: "layout-shift", buffered: true });
      });
      try {
        const page = await context.newPage();
        page.on("request", (request) => {
          const requestUrl = request.url();
          const requiredType = ["stylesheet", "script", "image", "font"].includes(request.resourceType());
          if (/^https?:/.test(requestUrl) && requiredType) report.external_asset_requests += 1;
        });
        await page.goto(url, { waitUntil: "load" });
        await page.waitForTimeout(50);

        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
        );
        if (overflow) report.horizontal_overflow_count += 1;

        const accessibility = await new AxeBuilder({ page }).options(axeOptions).analyze();
        for (const violation of accessibility.violations) {
          if (!blockingImpacts.has(violation.impact)) continue;
          if (violation.impact === "critical") report.accessibility_critical += 1;
          if (violation.impact === "serious") report.accessibility_serious += 1;
        }

        report.focus_visible &&= await keyboardFocusIsVisible(page);
        report.reduced_motion_core &&= await page.evaluate(() => {
          const value = getComputedStyle(document.querySelector("button")).transitionDuration;
          return value === "0s" || parseFloat(value) <= 0.02;
        });

        if (profile.name === "phone") {
          const performanceValues = await page.evaluate(() => {
            const navigation = performance.getEntriesByType("navigation")[0];
            const paint = performance.getEntriesByName("first-contentful-paint")[0];
            return {
              firstUseful: paint?.startTime ?? navigation?.domContentLoadedEventEnd ?? null,
              cls: window.__travelPlannerCls ?? 0,
            };
          });
          report.first_useful_ms = numericMaximum(report.first_useful_ms, performanceValues.firstUseful);
          report.cumulative_layout_shift = numericMaximum(
            report.cumulative_layout_shift,
            performanceValues.cls,
          );
          report.mobile_priority_visible = await mobilePriorityIsVisible(page);
          report.undersized_touch_targets += await countUndersizedTouchTargets(page);
          report.interaction_ms = numericMaximum(report.interaction_ms, await measureInteraction(page));
          report.filter_sync = await filtersStaySynchronized(page);
        }

        await context.setOffline(true);
        await page.reload({ waitUntil: "load" });
        report.offline_core &&= await coreIsReadable(page);
        await context.setOffline(false);

        await page.screenshot({
          path: path.join(baselineDirectory, `${profile.name}.png`),
          fullPage: true,
        });

        if (profile.name === "desktop") {
          report.state_matrix_complete = await captureStateMatrix(page, baselineDirectory, finalUrl);
          report.peak_memory_bytes = await testThirtyDayMemory(page);
        }
      } catch (error) {
        report.errors.push(`${profile.name}: ${error.message}`);
      } finally {
        await context.close();
      }
    }
    report.no_js_core = await testNoJavaScript(browser, url);
    report.zoom_200_core = await testEquivalentZoom(browser, url);
  } finally {
    await browser.close();
  }

  process.stdout.write(`${JSON.stringify(report)}\n`);
}

run().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
