(() => {
  "use strict";

  const root = document.documentElement;
  const body = document.body;
  const liveRegion = document.querySelector("[data-live-region]");
  const announce = (message) => {
    if (liveRegion) liveRegion.textContent = message;
  };
  const copy = (name, replacements = {}) => {
    let value = body?.dataset[name] || "";
    Object.entries(replacements).forEach(([key, replacement]) => {
      value = value.replace(`{${key}}`, String(replacement));
    });
    return value;
  };

  root.classList.add("js-enabled");

  try {
    const days = Array.from(document.querySelectorAll("[data-day]"));
    const overviewByDay = new Map(
      Array.from(document.querySelectorAll("[data-day-overview]")).map((overview) => [
        overview.dataset.dayOverview,
        overview,
      ]),
    );
    const filterButtons = Array.from(document.querySelectorAll("[data-filter]"));
    const resultCount = document.querySelector("[data-filter-results]");
    const emptyState = document.querySelector("[data-filter-empty]");
    const resetFilters = document.querySelector("[data-reset-filters]");
    let activeFilter = "all";

    const matchesFilter = (day) =>
      activeFilter === "all" || day.dataset[activeFilter] === "true";

    const applyDayView = () => {
      let visible = 0;
      days.forEach((day) => {
        const show = matchesFilter(day);
        day.hidden = !show;
        const overview = overviewByDay.get(day.id);
        if (overview) overview.hidden = !show;
        if (show) visible += 1;
      });
      const message = copy("daysShownCopy", { count: visible });
      if (resultCount) resultCount.textContent = message;
      if (emptyState) emptyState.hidden = visible !== 0;
      announce(message);
    };

    filterButtons.forEach((button) => {
      button.addEventListener("click", () => {
        activeFilter = button.dataset.filter || "all";
        filterButtons.forEach((candidate) => {
          candidate.setAttribute("aria-pressed", String(candidate === button));
        });
        applyDayView();
      });
    });
    resetFilters?.addEventListener("click", () => {
      activeFilter = "all";
      filterButtons.forEach((candidate) => {
        candidate.setAttribute("aria-pressed", String(candidate.dataset.filter === "all"));
      });
      applyDayView();
      filterButtons.find((candidate) => candidate.dataset.filter === "all")?.focus();
    });

    document.querySelectorAll("[data-scenario-tabs]").forEach((tablist) => {
      const day = tablist.closest("[data-day]");
      const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
      const panels = Array.from(day?.querySelectorAll("[data-scenario]") || []);
      const selectScenario = (tab, { focus = false, speak = true } = {}) => {
        const selected = tab.dataset.showScenario;
        tabs.forEach((candidate) => {
          const active = candidate === tab;
          candidate.setAttribute("aria-selected", String(active));
          candidate.tabIndex = active ? 0 : -1;
        });
        panels.forEach((panel) => {
          panel.hidden = panel.dataset.scenario !== selected;
        });
        if (focus) tab.focus();
        if (speak) announce(copy("scenarioShownCopy", { label: tab.textContent.trim() }));
      };

      const initial = tabs.find((tab) => tab.getAttribute("aria-selected") === "true");
      if (initial) selectScenario(initial, { speak: false });
      tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => selectScenario(tab));
        tab.addEventListener("keydown", (event) => {
          let targetIndex;
          if (event.key === "ArrowRight") targetIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft") targetIndex = (index - 1 + tabs.length) % tabs.length;
          if (event.key === "Home") targetIndex = 0;
          if (event.key === "End") targetIndex = tabs.length - 1;
          if (targetIndex === undefined) return;
          event.preventDefault();
          selectScenario(tabs[targetIndex], { focus: true });
        });
      });
    });

    document.querySelectorAll("[data-optional-media]").forEach((figure) => {
      const photo = figure.querySelector("[data-media-image]");
      const fallback = figure.querySelector("[data-media-fallback]");
      const markLoaded = () => figure.classList.add("media-loaded");
      const markUnavailable = () => {
        figure.classList.add("media-unavailable");
        if (fallback) fallback.hidden = false;
      };
      if (photo?.complete) {
        if (photo.naturalWidth > 0) markLoaded();
        else markUnavailable();
      } else {
        photo?.addEventListener("load", markLoaded, { once: true });
        photo?.addEventListener("error", markUnavailable, { once: true });
      }
    });
  } catch (error) {
    root.classList.add("enhancement-failed");
    const notice = document.querySelector("[data-enhancement-error]");
    if (notice) notice.hidden = false;
    document.querySelectorAll("[data-scenario]").forEach((panel) => {
      panel.hidden = false;
    });
    console.warn("Itinerary enhancements unavailable; core document remains readable.", error);
  }
})();
