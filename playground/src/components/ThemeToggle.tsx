import { Theme, useTheme } from "@/providers/ThemeProvider";
import { Moon, Sun, SunMoon } from "lucide-react";
import { MouseEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme, systemTheme } = useTheme();
  const [isDark, setIsDark] = useState(theme === "dark");

  const reducedMotion = !window.matchMedia("(prefers-reduced-motion: reduce)")
    .matches;

  useEffect(() => {
    setIsDark(
      theme === "dark" || (theme === "system" && systemTheme === "dark"),
    );
  }, [theme, systemTheme]);

  const transitTheme = (event: MouseEvent<HTMLButtonElement>) => {
    let newTheme: Theme = "light";
    if (theme === "light") {
      newTheme = "dark";
    } else if (theme === "dark") {
      newTheme = "system";
    } else {
      newTheme = "light";
    }

    let skipTransition = false;
    if (theme === "system") {
      skipTransition = newTheme === systemTheme;
    } else if (newTheme === "system") {
      skipTransition = theme === systemTheme;
    }

    if (
      !document.startViewTransition ||
      !reducedMotion ||
      !event ||
      skipTransition
    ) {
      setTheme(newTheme);
      return;
    }

    const x = event.clientX;
    const y = event.clientY;
    const endRadius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y),
    );

    const transition = document.startViewTransition(() => {
      setTheme(newTheme);
    });

    transition.ready.then(() => {
      const clipPath = [
        `circle(0px at ${x}px ${y}px)`,
        `circle(${endRadius}px at ${x}px ${y}px)`,
      ];

      document.documentElement.animate(
        {
          clipPath: isDark ? [...clipPath].reverse() : clipPath,
        },
        {
          duration: 400,
          easing: "ease-in",
          pseudoElement: isDark
            ? "::view-transition-old(root)"
            : "::view-transition-new(root)",
        },
      );
    });
  };

  return (
    <div>
      <Button
        variant="ghost"
        size="icon"
        className={className}
        onClick={transitTheme}
      >
        {theme === "dark" ? (
          <Moon className="h-[1.2rem] w-[1.2rem]" />
        ) : theme === "light" ? (
          <Sun className="h-[1.2rem] w-[1.2rem]" />
        ) : (
          <SunMoon className="h-[1.2rem] w-[1.2rem]" />
        )}
      </Button>
    </div>
  );
}
