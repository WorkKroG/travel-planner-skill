(() => {
  "use strict";

  const root = document.documentElement;
  root.classList.add("js-enabled");

  const liveRegion = document.querySelector("[data-live-region]");
  const announce = (message) => {
    if (liveRegion) liveRegion.textContent = message;
  };

  try {
    const contents = document.querySelector("details.contents");
    const compact = window.matchMedia("(max-width: 639px)");
    const syncContents = () => {
      if (!contents) return;
      if (compact.matches) contents.removeAttribute("open");
      else contents.setAttribute("open", "");
    };
    syncContents();
    compact.addEventListener?.("change", syncContents);

    const hero = document.querySelector(".trip-hero");
    const syncCompactContentsVisibility = () => {
      if (!contents) return;
      const heroHasPassed = hero ? hero.getBoundingClientRect().bottom <= 0 : true;
      contents.classList.toggle("contents--available", !compact.matches || heroHasPassed);
    };
    syncCompactContentsVisibility();
    window.addEventListener("scroll", syncCompactContentsVisibility, { passive: true });
    compact.addEventListener?.("change", syncCompactContentsVisibility);

    const days = Array.from(document.querySelectorAll("[data-day]"));
    const overviewByDay = new Map(
      Array.from(document.querySelectorAll("[data-day-overview]")).map((overview) => [
        overview.dataset.dayOverview,
        overview,
      ]),
    );
    const search = document.querySelector("[data-day-search]");
    const filterButtons = Array.from(document.querySelectorAll("[data-filter]"));
    const resultCount = document.querySelector("[data-filter-results]");
    const emptyState = document.querySelector("[data-filter-empty]");
    const resetFilters = document.querySelector("[data-reset-filters]");
    let activeFilter = "all";

    const matchesFilter = (day) => {
      if (activeFilter === "all") return true;
      return day.dataset[activeFilter] === "true";
    };

    const applyDayView = () => {
      const query = search?.value.trim().toLocaleLowerCase() || "";
      let visible = 0;
      days.forEach((day) => {
        const matchesSearch = !query || day.textContent.toLocaleLowerCase().includes(query);
        const show = matchesSearch && matchesFilter(day);
        day.hidden = !show;
        const overview = overviewByDay.get(day.id);
        if (overview) overview.hidden = !show;
        if (show) visible += 1;
      });
      const message = `${visible} ${visible === 1 ? "day" : "days"} shown.`;
      if (resultCount) resultCount.textContent = message;
      if (emptyState) emptyState.hidden = visible !== 0;
      announce(message);
    };

    search?.addEventListener("input", applyDayView);
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
      if (search) search.value = "";
      filterButtons.forEach((candidate) => {
        candidate.setAttribute("aria-pressed", String(candidate.dataset.filter === "all"));
      });
      applyDayView();
      search?.focus();
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

    document.querySelectorAll("[data-scenario-switch]").forEach((switcher) => {
      const day = switcher.closest("[data-day]");
      const panels = Array.from(day?.querySelectorAll("[data-scenario]") || []);
      const buttons = Array.from(switcher.querySelectorAll("[data-show-scenario]"));
      const selectScenario = (kind) => {
        panels.forEach((panel) => {
          panel.hidden = panel.dataset.scenario !== kind;
        });
        buttons.forEach((button) => {
          button.setAttribute("aria-pressed", String(button.dataset.showScenario === kind));
        });
        announce(`${kind === "primary" ? "Primary" : "Backup"} scenario shown.`);
      };
      if (panels.some((panel) => panel.dataset.scenario === "primary")) {
        selectScenario("primary");
      }
      buttons.forEach((button) => {
        button.addEventListener("click", () => selectScenario(button.dataset.showScenario));
      });
    });

    document.querySelectorAll(".contents a").forEach((link) => {
      link.addEventListener("click", () => {
        if (compact.matches) contents?.removeAttribute("open");
      });
    });
  } catch (error) {
    root.classList.add("enhancement-failed");
    const notice = document.querySelector("[data-enhancement-error]");
    if (notice) notice.hidden = false;
    console.warn("Itinerary enhancements unavailable; core document remains readable.", error);
  }
})();
