import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

import { chromium } from "playwright";

import { repositoryRootFromModuleUrl } from "./qa-paths.mjs";

const LONG_TEXT = "UnbrokenCanonicalValue".repeat(256);

async function injectLongCanonicalText(page) {
  await page.evaluate((value) => {
    const blockerList = document.querySelector(".blocker-list");
    blockerList.innerHTML = `
      <li class="blocker-item blocker-item--unaccepted">
        <p class="status-with-icon"><strong></strong></p>
        <p></p><p></p>
      </li>`;
    const selectors = [
      "h1",
      ".trip-thesis",
      ".route-ribbon",
      ".route-sequence strong",
      ".day-overview li",
      ".decision-list li",
      ".day-heading h3",
      ".day-thesis",
      ".timeline-time",
      ".timeline-event strong",
      ".timeline-event p",
      ".scenario-panel strong",
      ".scenario-panel p",
      ".constraint-list li",
      ".readiness-item",
      ".budget-table tbody tr",
      ".blocker-item strong",
      ".blocker-item p:nth-child(2)",
      ".blocker-item p:nth-child(3)",
      ".source-item strong",
      ".source-url",
      ".document-version",
    ];
    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (!element) throw new Error(`Missing representative element: ${selector}`);
      element.textContent = value;
      element.dataset.longCanonical = "";
    }
  }, LONG_TEXT);
}

async function measureContainment(page) {
  return page.evaluate((value) => {
    const root = document.documentElement;
    const elements = Array.from(document.querySelectorAll("[data-long-canonical]"));
    return {
      overflow: root.scrollWidth > root.clientWidth + 1,
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      preserved: elements.every((element) => element.textContent === value),
      outsideViewport: elements
        .filter((element) => {
          const rect = element.getBoundingClientRect();
          return rect.left < -1 || rect.right > root.clientWidth + 1;
        })
        .map((element) => element.tagName + "." + element.className),
      outsideDocument: Array.from(document.querySelectorAll("body *"))
        .filter((element) => element.getBoundingClientRect().right > root.clientWidth + 1)
        .slice(0, 10)
        .map((element) => ({
          element: element.tagName + "." + element.className,
          right: Math.round(element.getBoundingClientRect().right),
          scrollWidth: element.scrollWidth,
          clientWidth: element.clientWidth,
        })),
    };
  }, LONG_TEXT);
}

test("unbroken canonical text stays readable without horizontal document overflow", async () => {
  const repositoryRoot = repositoryRootFromModuleUrl(import.meta.url);
  const fixture = path.join(repositoryRoot, "tests", "ui", "state-fixtures", "final.html");
  const url = pathToFileURL(fixture).href;
  const browser = await chromium.launch({ headless: true });
  try {
    for (const width of [320, 390, 1440]) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      try {
        const page = await context.newPage();
        await page.goto(url, { waitUntil: "load" });
        await injectLongCanonicalText(page);
        const result = await measureContainment(page);
        assert.equal(result.overflow, false, `${width}px document overflowed`);
        assert.equal(result.preserved, true, `${width}px lost canonical text`);
        assert.deepEqual(result.outsideViewport, [], `${width}px clipped canonical elements`);
      } finally {
        await context.close();
      }
    }

    const printContext = await browser.newContext({ viewport: { width: 794, height: 1123 } });
    try {
      const page = await printContext.newPage();
      await page.goto(url, { waitUntil: "load" });
      await injectLongCanonicalText(page);
      await page.emulateMedia({ media: "print" });
      const result = await measureContainment(page);
      assert.equal(result.overflow, false, `print document overflowed: ${JSON.stringify(result)}`);
      assert.equal(result.preserved, true, "print lost canonical text");
      assert.deepEqual(result.outsideViewport, [], "print clipped canonical elements");
    } finally {
      await printContext.close();
    }
  } finally {
    await browser.close();
  }
});

test("full Japan print lets day articles fragment while compact blocks stay atomic", async () => {
  const repositoryRoot = repositoryRootFromModuleUrl(import.meta.url);
  const fixture = path.join(
    repositoryRoot,
    "examples",
    "japan-autumn-2026",
    "outputs",
    "itinerary.html",
  );
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 794, height: 1123 } });
    await page.goto(pathToFileURL(fixture).href, { waitUntil: "load" });
    await page.emulateMedia({ media: "print" });
    const result = await page.evaluate(() => ({
      dayArticles: Array.from(document.querySelectorAll(".day-article")).map((element) => ({
        breakBefore: getComputedStyle(element).breakBefore,
        breakInside: getComputedStyle(element).breakInside,
      })),
      timelineEvent: getComputedStyle(document.querySelector(".timeline-event")).breakInside,
      constraint: getComputedStyle(document.querySelector(".constraint-list li")).breakInside,
    }));

    assert.equal(result.dayArticles.length, 12);
    assert.equal(result.dayArticles.every((value) => value.breakInside !== "avoid"), true);
    assert.equal(result.dayArticles.every((value) => value.breakBefore !== "page"), true);
    assert.equal(result.timelineEvent, "avoid");
    assert.equal(result.constraint, "avoid");
  } finally {
    await browser.close();
  }
});

test("print keeps each scenario heading with its lead without making the panel atomic", async () => {
  const repositoryRoot = repositoryRootFromModuleUrl(import.meta.url);
  const fixture = path.join(
    repositoryRoot,
    "examples",
    "japan-autumn-2026",
    "outputs",
    "itinerary.html",
  );
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 794, height: 1123 } });
    await page.goto(pathToFileURL(fixture).href, { waitUntil: "load" });
    await page.emulateMedia({ media: "print" });
    const scenarios = await page.evaluate(() =>
      Array.from(document.querySelectorAll(".scenario-panel")).map((panel) => {
        const heading = panel.querySelector(":scope > .scenario-heading");
        const description = panel.querySelector(":scope > p");
        return {
          panelBreakInside: getComputedStyle(panel).breakInside,
          headingBreakInside: heading ? getComputedStyle(heading).breakInside : null,
          headingBreakAfter: heading ? getComputedStyle(heading).breakAfter : null,
          headingPrecedesDescription: heading?.nextElementSibling === description,
          descriptionOrphans: description ? Number(getComputedStyle(description).orphans) : 0,
        };
      }),
    );

    assert.equal(scenarios.length > 0, true);
    assert.equal(scenarios.every((scenario) => scenario.panelBreakInside !== "avoid"), true);
    assert.equal(scenarios.every((scenario) => scenario.headingBreakInside === "avoid"), true);
    assert.equal(scenarios.every((scenario) => scenario.headingBreakAfter === "avoid"), true);
    assert.equal(scenarios.every((scenario) => scenario.headingPrecedesDescription), true);
    assert.equal(scenarios.every((scenario) => scenario.descriptionOrphans >= 2), true);
  } finally {
    await browser.close();
  }
});

test("print keeps every day metadata label and value pair atomic", async () => {
  const repositoryRoot = repositoryRootFromModuleUrl(import.meta.url);
  const fixture = path.join(
    repositoryRoot,
    "examples",
    "japan-autumn-2026",
    "outputs",
    "itinerary.html",
  );
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 794, height: 1123 } });
    await page.goto(pathToFileURL(fixture).href, { waitUntil: "load" });
    await page.emulateMedia({ media: "print" });
    const metadata = await page.evaluate(() => ({
      dayCount: document.querySelectorAll(".day-article").length,
      groups: Array.from(document.querySelectorAll(".day-context dl")).map((list) =>
        Array.from(list.children).map((pair) => ({
          tagName: pair.tagName,
          childTags: Array.from(pair.children).map((child) => child.tagName),
          breakInside: getComputedStyle(pair).breakInside,
        })),
      ),
    }));

    assert.equal(metadata.groups.length, metadata.dayCount);
    assert.equal(metadata.groups.every((groups) => groups.length === 4), true);
    assert.equal(
      metadata.groups.flat().every((pair) => pair.tagName === "DIV"),
      true,
    );
    assert.equal(
      metadata.groups.flat().every((pair) => pair.childTags.join(",") === "DT,DD"),
      true,
    );
    assert.equal(metadata.groups.flat().every((pair) => pair.breakInside === "avoid"), true);
  } finally {
    await browser.close();
  }
});
