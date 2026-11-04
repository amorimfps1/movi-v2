import { createContext, useContext, useLayoutEffect, useState } from "react";
import type { ReactNode } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "./ui";

type Theme = "light" | "dark";
const storageKey = "movi:theme";

function preferredTheme(): Theme {
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    // The toggle still works when browser storage is unavailable.
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function initializeTheme() {
  document.documentElement.dataset.theme = preferredTheme();
}

const ThemeContext = createContext({
  theme: "light" as Theme,
  toggleTheme: () => {},
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(preferredTheme);

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      localStorage.setItem(storageKey, next);
    } catch {
      // Keep the current session usable even if persistence is blocked.
    }
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { theme, toggleTheme } = useContext(ThemeContext);
  const label = theme === "dark" ? "Ativar tema claro" : "Ativar tema escuro";
  const Icon = theme === "dark" ? Sun : Moon;

  return (
    <Button
      type="button"
      variant="ghost"
      className="theme-toggle"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
    >
      <Icon size={18} aria-hidden="true" />
      {!compact && (
        <span>{theme === "dark" ? "Tema claro" : "Tema escuro"}</span>
      )}
    </Button>
  );
}
