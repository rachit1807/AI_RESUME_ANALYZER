(() => {
  const themeToggle = document.querySelector("[data-theme-toggle]");
  if (themeToggle) {
    const themeIcon = themeToggle.querySelector("[data-theme-icon]");
    const themeLabel = themeToggle.querySelector(".theme-toggle-label");
    const syncThemeControl = () => {
      const isDark = document.documentElement.dataset.theme === "dark";
      themeToggle.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} theme`);
      themeToggle.setAttribute("title", `Switch to ${isDark ? "light" : "dark"} theme`);
      themeToggle.setAttribute("aria-pressed", String(isDark));
      if (themeIcon) themeIcon.textContent = isDark ? "☀" : "☾";
      if (themeLabel) themeLabel.textContent = isDark ? "Light" : "Dark";
    };
    const applyTheme = (theme) => {
      if (theme !== "dark" && theme !== "light") return;
      document.documentElement.dataset.theme = theme;
      syncThemeControl();
    };
    syncThemeControl();
    themeToggle.addEventListener("click", () => {
      const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      try { localStorage.setItem("career-platform-theme", nextTheme); } catch {}
      try { document.cookie = `career-platform-theme=${nextTheme}; Path=/; Max-Age=31536000; SameSite=Lax${location.protocol === "https:" ? "; Secure" : ""}`; } catch {}
      applyTheme(nextTheme);
    });
    window.addEventListener("storage", (event) => {
      if (event.key === "career-platform-theme") applyTheme(event.newValue);
    });
  }

  const roleSelect = document.getElementById("role-select");
  const companyField = document.getElementById("company-field");
  if (roleSelect && companyField) {
    const toggleCompany = () => {
      const showCompany = roleSelect.value === "recruiter";
      companyField.hidden = !showCompany;
      companyField.querySelector("input").required = showCompany;
    };
    roleSelect.addEventListener("change", toggleCompany);
    toggleCompany();
  }

  const builder = document.getElementById("builder-form");
  if (builder) {
    const fields = {name: "preview-name", contact: "preview-contact", summary: "preview-summary",
      skills: "preview-skills", experience: "preview-experience", projects: "preview-projects", education: "preview-education"};
    const fallback = {name: "Your Name", contact: "Email · phone · city", summary: "A concise introduction will appear here.",
      skills: "Add your relevant skills.", experience: "Describe your role and impact.", projects: "Show work you can discuss.",
      education: "Add your education details."};
    const templateSelect = document.getElementById("template-select");
    const syncPreview = () => {
      for (const [name, target] of Object.entries(fields)) {
        const input = builder.elements.namedItem(name);
        const preview = document.getElementById(target);
        if (input && preview) preview.textContent = input.value.trim() || fallback[name];
      }
      document.getElementById("resume-preview").className = `resume-sheet template-${templateSelect.value}`;
    };
    builder.querySelectorAll("input, textarea, select").forEach((field) => field.addEventListener("input", syncPreview));
    templateSelect.addEventListener("change", syncPreview);
    syncPreview();
  }

  document.querySelectorAll(".question-pick").forEach((button) => {
    button.addEventListener("click", () => {
      const questionField = document.getElementById("question");
      if (questionField) questionField.value = button.dataset.question || "";
    });
  });

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
})();
