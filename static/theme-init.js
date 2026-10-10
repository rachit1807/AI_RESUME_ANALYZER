(() => {
  try {
    const cookieTheme = document.cookie.match(/(?:^|;\s*)career-platform-theme=(dark|light)(?:;|$)/)?.[1];
    const savedTheme = localStorage.getItem("career-platform-theme") || cookieTheme;
    if (savedTheme === "dark" || savedTheme === "light") {
      document.documentElement.dataset.theme = savedTheme;
    }
  } catch {
    // Theme preference is optional; the default theme still renders if storage is unavailable.
  }
})();
