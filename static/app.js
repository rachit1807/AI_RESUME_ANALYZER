(() => {
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
