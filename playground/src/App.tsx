import { Toaster } from "sonner";

import { TooltipProvider } from "@/components/ui/tooltip";

import { ThemeProvider } from "./providers/ThemeProvider";
import PrimaryView from "./views/PrimaryView";

const App = () => {
  return (
    <ThemeProvider>
      <TooltipProvider>
        <main className="flex min-h-screen flex-col pt-4 pb-50">
          <PrimaryView />
          <Toaster richColors />
        </main>
      </TooltipProvider>
    </ThemeProvider>
  );
};

export default App;
