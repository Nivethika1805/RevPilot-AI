import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Upload, FileSpreadsheet, AlertTriangle, CheckCircle, XCircle,
  ArrowRight, RefreshCw, FileText, Download, ShieldCheck, Database,
  Sliders, Layers, HelpCircle, Check, Eye
} from 'lucide-react';
import { apiClient } from '../api/client';
import { FieldConflict, FieldProvenance } from '../types';
import { Modal } from '../components/Modal';

export const ImportCorrections: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'wizard' | 'conflicts' | 'provenance'>('wizard');

  // Wizard state
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3 | 4>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [entityType, setEntityType] = useState<string>('deal');
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [planResult, setPlanResult] = useState<any>(null);
  const [importReport, setImportReport] = useState<any>(null);
  const [skipInvalidRows, setSkipInvalidRows] = useState(false);

  // Conflicts state
  const [selectedConflict, setSelectedConflict] = useState<FieldConflict | null>(null);
  const [customValueInput, setCustomValueInput] = useState('');
  const [resolveModalOpen, setResolveModalOpen] = useState(false);
  const [resolutionChoice, setResolutionChoice] = useState<'keep_manual' | 'accept_source' | 'custom_value'>('keep_manual');

  // Provenance viewer state
  const [provEntityType, setProvEntityType] = useState('deal');
  const [provEntityId, setProvEntityId] = useState(1);

  // Queries
  const { data: conflicts = [], isLoading: conflictsLoading } = useQuery({
    queryKey: ['conflicts'],
    queryFn: () => apiClient.getConflicts(),
  });

  const { data: provenanceList = [], isLoading: provLoading } = useQuery({
    queryKey: ['provenance', provEntityType, provEntityId],
    queryFn: () => apiClient.getProvenance(provEntityType, provEntityId),
  });

  // Mutations
  const uploadMutation = useMutation({
    mutationFn: (file: File) => apiClient.uploadImportFile(file),
    onSuccess: (data) => {
      setUploadResult(data);
      // Auto-suggest mapping
      const mapping: Record<string, string> = {};
      const fileHeaders: string[] = data.headers || [];
      fileHeaders.forEach((h) => {
        mapping[h] = h.toLowerCase().trim();
      });
      setColumnMapping(mapping);
      setWizardStep(2);
    },
  });

  const planMutation = useMutation({
    mutationFn: () => apiClient.planImport(uploadResult.job_id, entityType, columnMapping),
    onSuccess: (data) => {
      setPlanResult(data);
      setWizardStep(3);
    },
  });

  const confirmMutation = useMutation({
    mutationFn: () => apiClient.confirmImport(uploadResult.job_id, skipInvalidRows),
    onSuccess: (data) => {
      setImportReport(data);
      setWizardStep(4);
      queryClient.invalidateQueries({ queryKey: ['conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: ({ conflictId, choice, customVal }: { conflictId: number; choice: any; customVal?: string }) =>
      apiClient.resolveConflict(conflictId, choice, customVal),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      setResolveModalOpen(false);
      setSelectedConflict(null);
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleStartUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    uploadMutation.mutate(selectedFile);
  };

  const resetWizard = () => {
    setWizardStep(1);
    setSelectedFile(null);
    setUploadResult(null);
    setPlanResult(null);
    setImportReport(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Import &amp; Correction Lab</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/20 text-accent border border-accent/30">
              Idempotent Pipeline &amp; Provenance
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Safe multi-source imports with field-level provenance, deduplication, atomic rollback, and manual correction protection.
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-border">
        <button
          onClick={() => setActiveTab('wizard')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'wizard'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Upload className="w-4 h-4" />
          Import Wizard
        </button>
        <button
          onClick={() => setActiveTab('conflicts')}
          className={`px-4 py-2 text-sm font-medium border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'conflicts'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          Pending Conflicts
          {conflicts.length > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30">
              {conflicts.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('provenance')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'provenance'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Layers className="w-4 h-4" />
          Field-Level Provenance Viewer
        </button>
      </div>

      {/* TAB 1: 11-STAGE IMPORT WIZARD */}
      {activeTab === 'wizard' && (
        <div className="space-y-6">
          {/* Stepper bar */}
          <div className="grid grid-cols-4 gap-2 text-center text-xs">
            <div className={`p-2.5 rounded-lg border font-semibold ${wizardStep === 1 ? 'border-accent bg-accent/10 text-accent' : 'border-border bg-card text-muted-foreground'}`}>
              1. Upload &amp; Sniff
            </div>
            <div className={`p-2.5 rounded-lg border font-semibold ${wizardStep === 2 ? 'border-accent bg-accent/10 text-accent' : 'border-border bg-card text-muted-foreground'}`}>
              2. Column Mapping
            </div>
            <div className={`p-2.5 rounded-lg border font-semibold ${wizardStep === 3 ? 'border-accent bg-accent/10 text-accent' : 'border-border bg-card text-muted-foreground'}`}>
              3. Diff &amp; Classification
            </div>
            <div className={`p-2.5 rounded-lg border font-semibold ${wizardStep === 4 ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400' : 'border-border bg-card text-muted-foreground'}`}>
              4. Atomic Report
            </div>
          </div>

          {/* STEP 1: Upload */}
          {wizardStep === 1 && (
            <div className="p-8 rounded-xl border border-dashed border-border bg-card/40 text-center max-w-xl mx-auto space-y-4">
              <Upload className="w-12 h-12 text-accent mx-auto opacity-80" />
              <div>
                <h3 className="text-base font-bold text-foreground">Select File for Ingestion</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Supported formats: CSV, JSON. Max 5MB. Automatic SHA-256 fingerprinting and formula injection sanitization.
                </p>
              </div>

              <div className="flex items-center justify-center gap-4 text-xs">
                <label className="font-semibold text-muted-foreground">Target Entity:</label>
                <select
                  value={entityType}
                  onChange={(e) => setEntityType(e.target.value)}
                  className="bg-card border border-border rounded px-3 py-1.5 text-foreground"
                >
                  <option value="deal">Deals</option>
                  <option value="conversation">Conversations</option>
                  <option value="activity">Activities</option>
                  <option value="account">Accounts</option>
                </select>
              </div>

              <div className="pt-2">
                <input
                  type="file"
                  accept=".csv,.json"
                  onChange={handleFileChange}
                  className="text-xs text-muted-foreground file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-accent file:text-accent-foreground hover:file:opacity-90"
                />
              </div>

              {selectedFile && (
                <div className="pt-3">
                  <button
                    onClick={handleStartUpload}
                    disabled={uploadMutation.isPending}
                    className="btn-primary text-xs flex items-center justify-center gap-2 mx-auto"
                  >
                    <Upload className="w-4 h-4" />
                    {uploadMutation.isPending ? 'Validating File...' : 'Upload & Sniff Headers'}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: Column Mapping */}
          {wizardStep === 2 && uploadResult && (
            <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4 max-w-2xl mx-auto">
              <div>
                <h3 className="text-base font-bold text-foreground">Step 2: Map Columns to Target Fields</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  File: <strong className="text-foreground">{uploadResult.filename}</strong> ({uploadResult.row_count} rows, SHA: {uploadResult.file_sha256?.substring(0, 10)}...)
                </p>
              </div>

              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {(uploadResult.headers || []).map((header: string) => (
                  <div key={header} className="grid grid-cols-2 gap-4 items-center p-2 rounded bg-muted/20 border border-border">
                    <span className="text-xs font-mono font-medium text-foreground">{header}</span>
                    <input
                      type="text"
                      value={columnMapping[header] || ''}
                      onChange={(e) => setColumnMapping({ ...columnMapping, [header]: e.target.value })}
                      placeholder="Destination field name..."
                      className="bg-card border border-border rounded px-2.5 py-1 text-xs text-foreground focus:ring-1 focus:ring-accent focus:outline-none"
                    />
                  </div>
                ))}
              </div>

              <div className="flex justify-between items-center pt-3 border-t border-border">
                <button onClick={resetWizard} className="btn-secondary text-xs">
                  Back
                </button>
                <button
                  onClick={() => planMutation.mutate()}
                  disabled={planMutation.isPending}
                  className="btn-primary text-xs flex items-center gap-1.5"
                >
                  <ArrowRight className="w-4 h-4" />
                  {planMutation.isPending ? 'Classifying Diff...' : 'Generate Import Plan'}
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: Classification & Diff Preview */}
          {wizardStep === 3 && planResult && (
            <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5 max-w-3xl mx-auto">
              <div>
                <h3 className="text-base font-bold text-foreground">Step 3: Preview Row Classification &amp; Diffs</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Each row was validated and matched against stable database keys. Unchanged rows will execute 0 updates.
                </p>
              </div>

              {/* Counts Badge Matrix */}
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-center text-xs">
                <div className="p-2.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                  <div className="text-lg font-bold">{planResult.summary?.new_count || 0}</div>
                  <div className="text-[10px] uppercase font-semibold">New</div>
                </div>
                <div className="p-2.5 rounded-lg border border-blue-500/30 bg-blue-500/10 text-blue-300">
                  <div className="text-lg font-bold">{planResult.summary?.changed_count || 0}</div>
                  <div className="text-[10px] uppercase font-semibold">Changed</div>
                </div>
                <div className="p-2.5 rounded-lg border border-border bg-muted/30 text-muted-foreground">
                  <div className="text-lg font-bold">{planResult.summary?.unchanged_count || 0}</div>
                  <div className="text-[10px] uppercase font-semibold">Unchanged</div>
                </div>
                <div className="p-2.5 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300">
                  <div className="text-lg font-bold">{planResult.summary?.conflict_count || 0}</div>
                  <div className="text-[10px] uppercase font-semibold">Conflicts</div>
                </div>
                <div className="p-2.5 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300">
                  <div className="text-lg font-bold">{planResult.summary?.invalid_count || 0}</div>
                  <div className="text-[10px] uppercase font-semibold">Invalid</div>
                </div>
                <div className="p-2.5 rounded-lg border border-purple-500/30 bg-purple-500/10 text-purple-300">
                  <div className="text-lg font-bold">{planResult.summary?.duplicate_in_file_count || 0}</div>
                  <div className="text-[10px] uppercase font-semibold">In-File Dups</div>
                </div>
              </div>

              {/* Sample Rows Preview */}
              <div className="border border-border rounded-lg overflow-hidden text-xs">
                <div className="p-2.5 bg-muted/40 font-semibold text-muted-foreground border-b border-border">
                  Row Classification Preview (First 5 Rows)
                </div>
                <div className="divide-y divide-border max-h-48 overflow-y-auto">
                  {(planResult.row_previews || []).slice(0, 5).map((row: any, idx: number) => (
                    <div key={idx} className="p-2.5 flex items-center justify-between hover:bg-muted/10">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-muted-foreground">#{row.row_number}</span>
                        <span className="font-medium text-foreground">{row.external_key || 'Row Record'}</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        row.outcome === 'new' ? 'bg-emerald-500/20 text-emerald-300' :
                        row.outcome === 'changed' ? 'bg-blue-500/20 text-blue-300' :
                        row.outcome === 'unchanged' ? 'bg-muted text-muted-foreground' :
                        row.outcome === 'conflict' ? 'bg-amber-500/20 text-amber-300' :
                        'bg-rose-500/20 text-rose-300'
                      }`}>
                        {row.outcome}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {planResult.summary?.invalid_count > 0 && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
                  <span>File contains {planResult.summary.invalid_count} invalid rows.</span>
                  <label className="flex items-center gap-2 cursor-pointer font-semibold">
                    <input
                      type="checkbox"
                      checked={skipInvalidRows}
                      onChange={(e) => setSkipInvalidRows(e.target.checked)}
                      className="rounded text-accent focus:ring-accent"
                    />
                    Skip invalid rows &amp; import valid records
                  </label>
                </div>
              )}

              <div className="flex justify-between items-center pt-3 border-t border-border">
                <button onClick={() => setWizardStep(2)} className="btn-secondary text-xs">
                  Back
                </button>
                <button
                  onClick={() => confirmMutation.mutate()}
                  disabled={confirmMutation.isPending || (planResult.summary?.invalid_count > 0 && !skipInvalidRows)}
                  className="btn-primary text-xs flex items-center gap-1.5"
                >
                  <Check className="w-4 h-4" />
                  {confirmMutation.isPending ? 'Committing Transaction...' : 'Commit Import Transaction'}
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: Completed Import Report */}
          {wizardStep === 4 && importReport && (
            <div className="p-8 rounded-xl border border-emerald-500/30 bg-card shadow-sm text-center max-w-xl mx-auto space-y-4">
              <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto" />
              <div>
                <h3 className="text-lg font-bold text-foreground">Import Transaction Committed</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Job #{importReport.job_id} successfully executed inside a single database transaction.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-muted/20 border border-border text-xs text-left space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">New Records Created:</span>
                  <span className="font-bold text-emerald-400">{importReport.summary?.new_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Updated Records:</span>
                  <span className="font-bold text-blue-400">{importReport.summary?.changed_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Unchanged Records (0 DB writes):</span>
                  <span className="font-bold text-foreground">{importReport.summary?.unchanged_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Conflicts Held for Manual Review:</span>
                  <span className="font-bold text-amber-400">{importReport.summary?.conflict_count || 0}</span>
                </div>
              </div>

              <div className="pt-2 flex justify-center gap-3">
                <button onClick={resetWizard} className="btn-secondary text-xs">
                  Import Another File
                </button>
                {importReport.summary?.conflict_count > 0 && (
                  <button
                    onClick={() => setActiveTab('conflicts')}
                    className="btn-primary text-xs flex items-center gap-1.5"
                  >
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Resolve Conflicts
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: PENDING CONFLICTS RESOLUTION */}
      {activeTab === 'conflicts' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 text-xs text-muted-foreground flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-foreground mb-1">
                Field-Level Conflict Protection Policy
              </div>
              When a source import contains a new value for a field that was previously manually corrected, RevPilot holds the manual value intact and records a pending conflict. You can choose to keep manual, accept incoming source, or enter a custom value.
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
            {conflicts.length === 0 ? (
              <div className="p-12 text-center">
                <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
                <h3 className="text-base font-semibold text-foreground">No Pending Conflicts</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  All fields are in sync between manual overrides and source data.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                      <th className="py-3 px-4">Entity &amp; Field</th>
                      <th className="py-3 px-4">Current Manual Value</th>
                      <th className="py-3 px-4">Incoming Source Value</th>
                      <th className="py-3 px-4">Source Baseline</th>
                      <th className="py-3 px-4">Import Job</th>
                      <th className="py-3 px-4 text-right">Resolve</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border text-sm">
                    {conflicts.map((conflict) => (
                      <tr key={conflict.id} className="hover:bg-muted/20 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-foreground">
                            {conflict.entity_label || `${conflict.entity_type} #${conflict.entity_id}`}
                          </div>
                          <div className="text-xs text-accent font-mono">
                            field: {conflict.field_name}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-1 rounded bg-accent/10 border border-accent/20 text-accent font-medium text-xs">
                            {conflict.current_value}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-1 rounded bg-blue-500/10 border border-blue-500/20 text-blue-300 font-medium text-xs">
                            {conflict.incoming_value}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-xs text-muted-foreground">
                          {conflict.source_baseline_value || 'None'}
                        </td>
                        <td className="py-3 px-4 text-xs font-mono text-muted-foreground">
                          Job #{conflict.import_job_id}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => {
                              setSelectedConflict(conflict);
                              setResolutionChoice('keep_manual');
                              setCustomValueInput(conflict.current_value || '');
                              setResolveModalOpen(true);
                            }}
                            className="btn-primary text-xs"
                          >
                            Resolve Conflict
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: FIELD PROVENANCE VIEWER */}
      {activeTab === 'provenance' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-border bg-card shadow-sm flex flex-wrap items-center gap-4 text-xs">
            <span className="font-semibold uppercase text-muted-foreground">Lookup Record:</span>
            <div className="flex items-center gap-2">
              <label className="text-muted-foreground">Type:</label>
              <select
                value={provEntityType}
                onChange={(e) => setProvEntityType(e.target.value)}
                className="bg-card border border-border rounded px-2.5 py-1 text-foreground"
              >
                <option value="deal">Deal</option>
                <option value="account">Account</option>
                <option value="conversation">Conversation</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-muted-foreground">ID:</label>
              <input
                type="number"
                value={provEntityId}
                onChange={(e) => setProvEntityId(parseInt(e.target.value) || 1)}
                className="bg-card border border-border rounded w-20 px-2 py-1 text-foreground"
              />
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                    <th className="py-3 px-4">Field Name</th>
                    <th className="py-3 px-4">Current Active Value</th>
                    <th className="py-3 px-4">Last Imported Source Value</th>
                    <th className="py-3 px-4">Manual Override?</th>
                    <th className="py-3 px-4">Update Source</th>
                    <th className="py-3 px-4">Last Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-xs">
                  {provenanceList.map((p) => (
                    <tr key={p.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-foreground">
                        {p.field_name}
                      </td>
                      <td className="py-3 px-4 font-semibold text-foreground">
                        {p.current_value || 'None'}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {p.source_value || 'None'}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          p.is_overridden
                            ? 'bg-accent/20 text-accent border border-accent/30'
                            : 'bg-muted text-muted-foreground'
                        }`}>
                          {p.is_overridden ? 'Manual Override' : 'From Source'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground uppercase font-mono text-[10px]">
                        {p.last_update_source}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {new Date(p.updated_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Conflict Resolution Modal */}
      <Modal
        isOpen={resolveModalOpen}
        onClose={() => setResolveModalOpen(false)}
        title="Resolve Field Conflict"
      >
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Resolving conflict for <strong className="text-foreground">{selectedConflict?.entity_label}</strong> on field <code className="text-accent font-mono">{selectedConflict?.field_name}</code>.
          </p>

          <div className="space-y-2">
            <label className="flex items-start gap-3 p-3 rounded-lg border border-border hover:bg-muted/20 cursor-pointer">
              <input
                type="radio"
                name="resolution"
                checked={resolutionChoice === 'keep_manual'}
                onChange={() => setResolutionChoice('keep_manual')}
                className="mt-1 text-accent focus:ring-accent"
              />
              <div className="text-xs">
                <div className="font-semibold text-foreground">Keep Current Manual Value</div>
                <div className="text-muted-foreground mt-0.5">
                  Preserve "{selectedConflict?.current_value}" and mark incoming source as acknowledged.
                </div>
              </div>
            </label>

            <label className="flex items-start gap-3 p-3 rounded-lg border border-border hover:bg-muted/20 cursor-pointer">
              <input
                type="radio"
                name="resolution"
                checked={resolutionChoice === 'accept_source'}
                onChange={() => setResolutionChoice('accept_source')}
                className="mt-1 text-accent focus:ring-accent"
              />
              <div className="text-xs">
                <div className="font-semibold text-foreground">Accept Incoming Source Value</div>
                <div className="text-muted-foreground mt-0.5">
                  Update record to "{selectedConflict?.incoming_value}" and clear manual override status.
                </div>
              </div>
            </label>

            <label className="flex items-start gap-3 p-3 rounded-lg border border-border hover:bg-muted/20 cursor-pointer">
              <input
                type="radio"
                name="resolution"
                checked={resolutionChoice === 'custom_value'}
                onChange={() => setResolutionChoice('custom_value')}
                className="mt-1 text-accent focus:ring-accent"
              />
              <div className="text-xs w-full">
                <div className="font-semibold text-foreground">Enter Custom Value</div>
                <div className="text-muted-foreground mt-0.5 mb-2">
                  Override with an agreed negotiated value.
                </div>
                {resolutionChoice === 'custom_value' && (
                  <input
                    type="text"
                    value={customValueInput}
                    onChange={(e) => setCustomValueInput(e.target.value)}
                    placeholder="Enter custom value..."
                    className="w-full bg-card border border-border rounded p-2 text-xs text-foreground focus:ring-1 focus:ring-accent focus:outline-none"
                  />
                )}
              </div>
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={() => setResolveModalOpen(false)} className="btn-secondary text-xs">
              Cancel
            </button>
            <button
              onClick={() => {
                if (!selectedConflict) return;
                resolveMutation.mutate({
                  conflictId: selectedConflict.id,
                  choice: resolutionChoice,
                  customVal: resolutionChoice === 'custom_value' ? customValueInput : undefined,
                });
              }}
              disabled={resolveMutation.isPending}
              className="btn-primary text-xs"
            >
              Confirm Resolution
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
