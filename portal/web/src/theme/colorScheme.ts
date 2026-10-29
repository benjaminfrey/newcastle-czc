// Light or dark follows the device, as Apple's apps do. HeroUI reads data-theme and the
// .dark class; index.css reads data-theme.
export function followDeviceScheme(): () => void {
  const mql = matchMedia("(prefers-color-scheme: dark)");
  const apply = (dark: boolean) => {
    const root = document.documentElement;
    root.dataset.theme = dark ? "dark" : "light";
    root.classList.toggle("dark", dark);
    root.classList.toggle("light", !dark);
  };
  apply(mql.matches);
  const onChange = (e: { matches: boolean }) => apply(e.matches);
  mql.addEventListener("change", onChange);
  return () => mql.removeEventListener("change", onChange);
}
