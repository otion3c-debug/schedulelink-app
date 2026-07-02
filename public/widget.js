(function () {
  "use strict";

  function getBaseFromCurrentScript() {
    var scripts = document.getElementsByTagName("script");
    var current = scripts[scripts.length - 1];
    try {
      var url = new URL(current.src);
      return url.origin;
    } catch (e) {
      return window.location.origin;
    }
  }

  function init() {
    var nodes = document.querySelectorAll("script[data-slug]");
    nodes.forEach(function (script) {
      if (script.dataset.slkInit === "1") return;
      script.dataset.slkInit = "1";

      var slug = script.getAttribute("data-slug");
      var height = script.getAttribute("data-height") || "700";
      var base = getBaseFromCurrentScript();

      var container = document.createElement("div");
      container.id = "schedulelink-widget-" + slug;
      container.style.maxWidth = "720px";
      container.style.margin = "0 auto";

      var iframe = document.createElement("iframe");
      iframe.src = base + "/embed/" + encodeURIComponent(slug);
      iframe.style.width = "100%";
      iframe.style.minHeight = height + "px";
      iframe.style.border = "0";
      iframe.style.background = "transparent";
      iframe.setAttribute("title", "ScheduleLink booking widget");
      iframe.setAttribute("loading", "lazy");
      iframe.setAttribute("allow", "clipboard-write");

      container.appendChild(iframe);
      script.parentNode.insertBefore(container, script);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
