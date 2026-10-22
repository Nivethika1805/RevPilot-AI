import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Shell } from './components/layout/Shell';

// Pages
import { CommandCenter } from './pages/CommandCenter';
import { IntelligenceInbox } from './pages/IntelligenceInbox';
import { DealsAndRisk } from './pages/DealsAndRisk';
import { DealDetailPage } from './pages/DealDetailPage';
import { ActionQueue } from './pages/ActionQueue';
import { RoutingRules } from './pages/RoutingRules';
import { ImportCorrections } from './pages/ImportCorrections';
import { DecisionReplay } from './pages/DecisionReplay';
import { ExportCenter } from './pages/ExportCenter';
import { AuditHistory } from './pages/AuditHistory';
import { Settings } from './pages/Settings';
import { FindingsPage } from './pages/FindingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 30000,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<CommandCenter />} />
            <Route path="/inbox" element={<IntelligenceInbox />} />
            <Route path="/deals" element={<DealsAndRisk />} />
            <Route path="/deals/:id" element={<DealDetailPage />} />
            <Route path="/actions" element={<ActionQueue />} />
            <Route path="/routing" element={<RoutingRules />} />
            <Route path="/imports" element={<ImportCorrections />} />
            <Route path="/replay" element={<DecisionReplay />} />
            <Route path="/exports" element={<ExportCenter />} />
            <Route path="/audit" element={<AuditHistory />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/findings" element={<FindingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Shell>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
