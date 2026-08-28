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

    const days = Array.from(document.querySelectorAll("[data-day]"));
    const search = document.querySelector("[data-day-search]");
    const filterButtons = Array.from(document.querySelectorAll("[data-filter]"));
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
        if (show) visible += 1;
      });
      announce(`${visible} ${visible === 1 ? "day" : "days"} shown.`);
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
