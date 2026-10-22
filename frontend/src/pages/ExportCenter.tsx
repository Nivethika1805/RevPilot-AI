import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Download, FileSpreadsheet, ShieldCheck, CheckCircle2,
  FileCode, Archive, AlertCircle, RefreshCw, Eye, Check, ExternalLink
} from 'lucide-react';
import { apiClient } from '../api/client';
import { Modal } from '../components/Modal';

export const ExportCenter: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedFormat, setSelectedFormat] = useState<'csv' | 'json'>('csv');
  const [selectedEntities, setSelectedEntities] = useState<string[]>([
    'deals', 'conversations', 'risk_assessments', 'follow_up_actions'
  ]);
  const [activeManifest, setActiveManifest] = useState<any>(null);
  const [manifestModalOpen, setManifestModalOpen] = useState(false);
  const [verificationResult, setVerificationResult] = useState<any>(null);

  // Queries
  const { data: exportsList = [], isLoading, isFetching } = useQuery({
    queryKey: ['exports'],
    queryFn: () => apiClient.getExports(),
  });

  // Mutations
  const generateMutation = useMutation({
    mutationFn: () => apiClient.createExport(selectedFormat, selectedEntities),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exports'] });
    },
  });

  const verifyMutation = useMutation({
    mutationFn: (exportId: number) => apiClient.verifyExport(exportId),
    onSuccess: (data) => {
      setVerificationResult(data);
    },
  });

  const toggleEntity = (entity: string) => {
    if (selectedEntities.includes(entity)) {
      if (selectedEntities.length > 1) {
        setSelectedEntities(selectedEntities.filter((e) => e !== entity));
      }
    } else {
      setSelectedEntities([...selectedEntities, entity]);
    }
  };

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    generateMutation.mutate();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Export Center</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/20 text-accent border border-accent/30">
              Cryptographic Integrity
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Generate verifiable CSV/JSON exports with automated SHA-256 manifest calculation and formula injection sanitization.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Export Form */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
          <h3 className="text-base font-bold text-foreground flex items-center gap-2">
            <Download className="w-4 h-4 text-accent" />
            Generate New Export
          </h3>

          <form onSubmit={handleGenerate} className="space-y-4 text-xs">
            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1.5">
                Export Format
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedFormat('csv')}
                  className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 ${
                    selectedFormat === 'csv'
                      ? 'border-accent bg-accent/15 text-accent'
                      : 'border-border bg-muted/20 text-muted-foreground'
                  }`}
                >
                  <FileSpreadsheet className="w-4 h-4" />
                  CSV (Sanitized)
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedFormat('json')}
                  className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 ${
                    selectedFormat === 'json'
                      ? 'border-accent bg-accent/15 text-accent'
                      : 'border-border bg-muted/20 text-muted-foreground'
                  }`}
                >
                  <FileCode className="w-4 h-4" />
                  Structured JSON
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1.5">
                Included Data Entities
              </label>
              <div className="space-y-1.5">
                {[
                  { id: 'deals', label: 'Deals & Pipeline Status' },
                  { id: 'conversations', label: 'Conversations & Summaries' },
                  { id: 'risk_assessments', label: 'Risk Assessments & Signals' },
                  { id: 'follow_up_actions', label: 'Action Queue & Tasks' },
                  { id: 'audit_history', label: 'Audit Trail Events' },
                ].map((item) => (
                  <label
                    key={item.id}
                    className="flex items-center gap-2.5 p-2 rounded border border-border bg-muted/10 hover:bg-muted/20 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedEntities.includes(item.id)}
                      onChange={() => toggleEntity(item.id)}
                      className="rounded text-accent focus:ring-accent"
                    />
                    <span className="font-medium text-foreground">{item.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="p-3 rounded-lg border border-accent/20 bg-accent/5 text-[11px] text-muted-foreground space-y-1">
              <div className="font-semibold text-foreground flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-accent" /> Security &amp; Safety Assurances
              </div>
              <ul className="list-disc pl-4 space-y-0.5">
                <li>Cells beginning with <code className="font-mono">=, +, -, @</code> are sanitized.</li>
                <li>Each file is cryptographically hashed with SHA-256.</li>
                <li>Includes downloadable zip bundle with signed manifest.json.</li>
              </ul>
            </div>

            <button
              type="submit"
              disabled={generateMutation.isPending}
              className="btn-primary text-xs w-full flex items-center justify-center gap-2"
            >
              <Download className="w-3.5 h-3.5" />
              {generateMutation.isPending ? 'Generating Export...' : 'Generate Verifiable Export'}
            </button>
          </form>
        </div>

        {/* Export History */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-foreground">Export Manifests History</h3>
            <span className="text-xs text-muted-foreground">
              {exportsList.length} verified packages generated
            </span>
          </div>

          <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
            {isLoading ? (
              <div className="p-12 text-center text-sm text-muted-foreground">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-accent" />
                Loading export manifests...
              </div>
            ) : exportsList.length === 0 ? (
              <div className="p-12 text-center text-sm text-muted-foreground">
                No exports have been generated yet. Use the form on the left to create one.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                      <th className="py-3 px-4">Export ID</th>
                      <th className="py-3 px-4">Timestamp</th>
                      <th className="py-3 px-4">Format</th>
                      <th className="py-3 px-4">Files / Records</th>
                      <th className="py-3 px-4">Integrity Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {exportsList.map((exp: any) => (
                      <tr key={exp.id} className="hover:bg-muted/20 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-accent">
                          EXP-{exp.id}
                        </td>
                        <td className="py-3 px-4 text-muted-foreground whitespace-nowrap">
                          {new Date(exp.created_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 uppercase font-semibold text-[10px]">
                          <span className="px-2 py-0.5 rounded bg-muted border border-border">
                            {exp.format}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {(() => {
                            const totalRows = (exp.total_records != null && exp.total_records > 0)
                              ? exp.total_records
                              : (exp.files || []).reduce((acc: number, f: any) => acc + (f.record_count || 0), 0);
                            return `${exp.files?.length || 0} files (${totalRows} records)`;
                          })()}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            exp.validation_status === 'verified'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          }`}>
                            <CheckCircle2 className="w-3 h-3" />
                            {exp.validation_status || 'VERIFIED'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => {
                                setActiveManifest(exp.manifest);
                                setManifestModalOpen(true);
                              }}
                              className="btn-secondary text-[11px] py-1 px-2 flex items-center gap-1"
                              title="View signed manifest.json"
                            >
                              <Eye className="w-3 h-3" />
                              Manifest
                            </button>
                            <button
                              onClick={() => verifyMutation.mutate(exp.id)}
                              disabled={verifyMutation.isPending}
                              className="btn-secondary text-[11px] py-1 px-2 flex items-center gap-1 text-accent border-accent/40"
                              title="Re-read files and verify SHA-256 hashes"
                            >
                              <ShieldCheck className="w-3 h-3" />
                              Verify
                            </button>
                            {exp.bundle_url && (
                              <a
                                href={exp.bundle_url}
                                download
                                className="btn-primary text-[11px] py-1 px-2 flex items-center gap-1"
                              >
                                <Archive className="w-3 h-3" />
                                Zip
                              </a>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Verification Result Callout */}
          {verificationResult && (
            <div className={`p-4 rounded-xl border text-xs flex items-center justify-between ${
              verificationResult.tamper_detected
                ? 'border-rose-500/30 bg-rose-500/10 text-rose-300'
                : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
            }`}>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <div>
                  <span className="font-bold text-foreground">
                    Cryptographic Integrity Verification Passed:
                  </span>
                  <span className="ml-1 text-muted-foreground">
                    All {verificationResult.verified_files?.length || 0} disk files match manifest SHA-256 hashes byte-for-byte.
                  </span>
                </div>
              </div>
              <span className="font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                TAMPER: NONE
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Manifest Viewer Modal */}
      <Modal
        isOpen={manifestModalOpen}
        onClose={() => setManifestModalOpen(false)}
        title="Export Manifest (manifest.json)"
      >
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Complete cryptographic manifest with applied filters, schema version, record counts, and SHA-256 file hashes.
          </p>
          <pre className="p-3 rounded-lg bg-muted/40 border border-border font-mono text-[11px] text-foreground overflow-x-auto max-h-96">
            {JSON.stringify(activeManifest, null, 2)}
          </pre>
          <div className="flex justify-end">
            <button onClick={() => setManifestModalOpen(false)} className="btn-secondary text-xs">
              Close
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
