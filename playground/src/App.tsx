import { Toaster } from "sonner";

import { TooltipProvider } from "@/components/ui/tooltip";

import { FeedbackProvider } from "./contexts/FeedbackContext";
import { ThemeProvider } from "./providers/ThemeProvider";
import PrimaryView from "./views/PrimaryView";

const App = () => {
  return (
    <ThemeProvider>
      <FeedbackProvider>
        <TooltipProvider>
          <main className="flex min-h-screen flex-col pt-4 pb-50">
            <PrimaryView />
            <Toaster richColors />
          </main>
        </TooltipProvider>
      </FeedbackProvider>
    </ThemeProvider>
  );
};

export default App;
