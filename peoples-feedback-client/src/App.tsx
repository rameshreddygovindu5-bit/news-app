import { Switch, Route } from "wouter";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/queryClient";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";

import Home from "@/pages/Home";
import News from "@/pages/News";
import NewsDetail from "@/pages/NewsDetail";
import Telugu from "@/pages/Telugu";
import Hindi from "@/pages/Hindi";
import TeluguDetail from "@/pages/TeluguDetail";
import MarketNews from "@/pages/MarketNews";
import Wishes from "@/pages/Wishes";
import NotFound from "@/pages/NotFound";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/news" component={News} />
      <Route path="/market-news" component={MarketNews} />
      <Route path="/news/:idOrSlug" component={NewsDetail} />
      <Route path="/telugu" component={Telugu} />
      <Route path="/hindi" component={Hindi} />
      <Route path="/telugu/:idOrSlug" component={TeluguDetail} />
      <Route path="/wishes" component={Wishes} />
      <Route component={NotFound} />
    </Switch>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Router />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
