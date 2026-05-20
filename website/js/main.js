/* ARGO Agent v3.0 — marketing site behavior.
   Plain vanilla JS, no dependencies. */

(function () {
  "use strict";

  /* ---- Mobile navigation toggle ---- */
  var navToggle = document.getElementById("navToggle");
  var navMenu = document.getElementById("navMenu");

  if (navToggle && navMenu) {
    navToggle.addEventListener("click", function () {
      var isOpen = navMenu.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    // Close the menu after following an in-page link on mobile.
    navMenu.addEventListener("click", function (event) {
      if (event.target.tagName === "A") {
        navMenu.classList.remove("open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---- Smooth scroll for in-page anchors ----
     CSS handles this via scroll-behavior; this is a graceful
     fallback for browsers that ignore it. */
  if (!("scrollBehavior" in document.documentElement.style)) {
    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener("click", function (event) {
        var id = link.getAttribute("href");
        if (id.length < 2) { return; }
        var target = document.querySelector(id);
        if (target) {
          event.preventDefault();
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });
  }

  /* ---- Copy-to-clipboard for the quick-start code block ---- */
  var copyBtn = document.getElementById("copyBtn");
  var codeSample = document.getElementById("codeSample");

  if (copyBtn && codeSample) {
    copyBtn.addEventListener("click", function () {
      var text = codeSample.innerText;

      var done = function () {
        copyBtn.textContent = "Copied";
        copyBtn.classList.add("copied");
        window.setTimeout(function () {
          copyBtn.textContent = "Copy";
          copyBtn.classList.remove("copied");
        }, 2000);
      };

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, fallbackCopy);
      } else {
        fallbackCopy();
      }

      function fallbackCopy() {
        var area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "absolute";
        area.style.left = "-9999px";
        document.body.appendChild(area);
        area.select();
        try { document.execCommand("copy"); done(); } catch (e) { /* no-op */ }
        document.body.removeChild(area);
      }
    });
  }

  /* ---- Footer year (keeps the copyright current) ---- */
  var yearEl = document.getElementById("footerYear");
  if (yearEl) {
    yearEl.textContent = String(new Date().getFullYear());
  }
})();
