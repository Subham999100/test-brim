// Applies the saved light/dark preference before React renders, to avoid a flash of the wrong theme.
// An external file (not an inline <script>) so the Content-Security-Policy can forbid inline scripts.
(function () {
  try {
    // Move existing browsers to the new light default once; later choices remain user-controlled.
    if (localStorage.getItem('clyptus-light-default-v1') !== 'applied') {
      localStorage.setItem('clyptus-appearance', 'light');
      localStorage.setItem('clyptus-light-default-v1', 'applied');
    }
    var preference = localStorage.getItem('clyptus-appearance');
    if (preference === 'dark' || (preference === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  } catch {
    document.documentElement.classList.remove('dark');
  }
})();
