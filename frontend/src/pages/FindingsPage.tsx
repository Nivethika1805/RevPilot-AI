import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  FileText, ShieldAlert, AlertTriangle, ArrowRight, Download,
  ExternalLink, CheckCircle2, HelpCircle, Compass, Database, RefreshCw
} from 'lucide-react';
import { apiClient } from '../api/client';
import { FindingsReport, FindingItem } from '../types';
import { PriorityBadge } from '../components/Badge';

export const FindingsPage: React.FC = () => {
  const { data: report, isLoading, isFetching } = useQuery({
    queryKey: ['findingsReport'],
    queryFn: () => apiClient.getFindingsReport(),
  });

  const downloadReport = (format: 'json' | 'md') => {
    if (!report) return;
    let content = '';
    let mimeType = '';
    let filename = '';

    if (format === 'json') {
      content = JSON.stringify(report, null, 2);
      mimeType = 'application/json';
      filename = `revpilot_findings_${report.as_of}.json`;
    } else {
      content = `# RevPilot AI — Findings & Evidence Report\n\n`;
      content += `Generated: ${report.generated_at} (As-Of: ${report.as_of})\n\n`;
      content += `## Evidence-Linked Findings\n\n`;
      report.findings.forEach((f, idx) => {
        content += `### Finding #${idx + 1}: ${f.title} [${f.severity.toUpperCase()}]\n`;
        content += `**Opportunity:** ${f.account_name} (${f.deal_code})\n`;
        content += `**Description:** ${f.description}\n\n`;
        content += `**Evidence References:**\n`;
        f.evidence_refs.forEach((ref) => {
          content += `- \`${ref.source_ref}\` (${ref.occurred_at}): "${ref.detail || ref.label}"\n`;
        });
        content += `\n**Recommended Action:** ${f.recommended_action}\n\n---\n\n`;
      });

      if (report.difficult_routing_decision) {
        const d = report.difficult_routing_decision;
        content += `## Difficult Routing Decision & Precedence Analysis\n\n`;
        content += `- **Conversation Ref:** \`${d.conversation_ref}\` (${d.deal_code})\n`;
        content += `- **Summary:** ${d.conversation_summary}\n`;
        content += `- **Chosen Route:** ${d.chosen_owner}\n`;
        content += `- **Rejected Alternative:** ${d.rejected_alternative}\n`;
        content += `- **Winning Precedence Rule:** ${d.winning_rule}\n`;
        content += `- **Explanatory Justification:** ${d.reason}\n`;
      }
      mimeType = 'text/markdown';
      filename = `revpilot_findings_${report.as_of}.md`;
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Findings &amp; Evidence Report</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/20 text-accent border border-accent/30">
              Live Verified Evidence
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Dynamic pipeline findings generated from active database records, with stable source references and explainable routing trade-offs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => downloadReport('md')}
            className="btn-secondary text-xs flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            Export Markdown
          </button>
          <button
            onClick={() => downloadReport('json')}
            className="btn-primary text-xs flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5" />
            Export JSON
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-sm text-muted-foreground">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-accent" />
          Analyzing database signals for findings...
        </div>
      ) : report ? (
        <div className="space-y-8">
          {/* Findings Cards List */}
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-accent" />
              Primary Revenue Intelligence Findings
            </h2>

            <div className="grid grid-cols-1 gap-4">
              {report.findings.map((finding: FindingItem, idx: number) => (
                <div
                  key={finding.id}
                  className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-3 hover:border-accent/40 transition-colors"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="px-2 py-0.5 rounded font-mono text-xs font-bold bg-muted text-muted-foreground">
                        Finding #{idx + 1}
                      </span>
                      <h3 className="text-base font-bold text-foreground">
                        {finding.title}
                      </h3>
                    </div>
                    <PriorityBadge priority={finding.severity} />
                  </div>

                  <p className="text-xs text-muted-foreground">
                    {finding.description}
                  </p>

                  {/* Related Deal Banner */}
                  {finding.deal_id && (
                    <div className="p-2.5 rounded-lg bg-muted/20 border border-border flex items-center justify-between text-xs">
                      <div>
                        <span className="text-muted-foreground">Target Opportunity: </span>
                        <span className="font-semibold text-foreground">{finding.account_name}</span>
                        <span className="font-mono text-accent ml-1.5">({finding.deal_code})</span>
                      </div>
                      <Link
                        to={`/deals/${finding.deal_id}`}
                        className="text-accent hover:underline font-medium flex items-center gap-1"
                      >
                        Inspect Deal Cockpit
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </div>
                  )}

                  {/* Source Evidence References */}
                  <div className="space-y-1.5 pt-1">
                    <span className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider block">
                      Direct Supporting Evidence:
                    </span>
                    <div className="space-y-1">
                      {finding.evidence_refs.map((ref, rIdx) => (
                        <div
                          key={rIdx}
                          className="p-2 rounded bg-muted/30 border border-border flex items-start gap-2 text-xs"
                        >
                          <span className="font-mono text-[11px] font-bold text-accent shrink-0 mt-0.5">
                            {ref.source_ref}
                          </span>
                          <span className="text-muted-foreground text-[11px] shrink-0">
                            [{new Date(ref.occurred_at || '').toLocaleDateString()}]:
                          </span>
                          <span className="text-foreground italic text-xs">
                            "{ref.detail || ref.label}"
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Recommended Action */}
                  <div className="p-3 rounded-lg border border-accent/20 bg-accent/5 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-accent uppercase tracking-wider text-[10px] block mb-0.5">
                        Recommended Next Step
                      </span>
                      <span className="text-foreground font-medium">
                        {finding.recommended_action}
                      </span>
                    </div>
                    <Link
                      to="/actions"
                      className="btn-primary text-xs flex items-center gap-1"
                    >
                      Action Queue
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section: Difficult Routing Decision */}
          {report.difficult_routing_decision && (
            <div className="p-6 rounded-xl border border-accent/30 bg-accent/5 space-y-4">
              <div className="flex items-center gap-2">
                <Compass className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-bold text-foreground">
                  Difficult Routing Decision &amp; Precedence Trade-Off
                </h2>
              </div>

              <p className="text-xs text-muted-foreground">
                In complex enterprise deals, conversations often trigger competing routing rules. RevPilot AI documents both the winning path and the rejected alternative to maintain organizational clarity.
              </p>

              <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-3 text-xs">
                <div className="flex flex-col sm:flex-row justify-between pb-3 border-b border-border">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-accent font-bold">
                      {report.difficult_routing_decision.conversation_ref}
                    </span>
                    <div className="text-sm font-semibold text-foreground mt-0.5">
                      {report.difficult_routing_decision.conversation_summary}
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground font-mono">
                    Deal: {report.difficult_routing_decision.deal_code}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Chosen Destination */}
                  <div className="p-3.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                    <span className="text-[10px] font-bold uppercase tracking-wider block mb-1">
                      ✓ Chosen Destination (Precedence Winner)
                    </span>
                    <div className="text-base font-bold text-foreground">
                      {report.difficult_routing_decision.chosen_owner}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Matched Rule: <strong className="text-foreground">{report.difficult_routing_decision.winning_rule}</strong>
                    </div>
                  </div>

                  {/* Rejected Alternative */}
                  <div className="p-3.5 rounded-lg border border-border bg-muted/20 text-muted-foreground">
                    <span className="text-[10px] font-bold uppercase tracking-wider block mb-1 text-muted-foreground">
                      ✕ Rejected Alternative
                    </span>
                    <div className="text-base font-bold text-foreground">
                      {report.difficult_routing_decision.rejected_alternative}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Lower precedence priority order in hierarchy.
                    </div>
                  </div>
                </div>

                {/* Precedence Justification */}
                <div className="p-3 rounded-lg bg-card border border-border text-xs">
                  <span className="font-semibold text-foreground block mb-1">
                    Precedence Rationale:
                  </span>
                  <p className="text-muted-foreground">
                    {report.difficult_routing_decision.reason}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};
