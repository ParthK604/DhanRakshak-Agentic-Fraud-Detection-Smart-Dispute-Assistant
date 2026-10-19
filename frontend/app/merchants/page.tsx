"use client";

import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";
import { RefreshCw, ShieldCheck, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, type PrecheckResponse, type TrustAssessment } from "@/lib/api";
import { defaultColDef, gridTheme } from "@/lib/ag-grid";
import { PageHeading, StatusBadge, ErrorState } from "@/components/ui";

function TrustCell({ value, level }: { value: number; level: string }) { return <div className="trust-cell"><strong>{value}</strong><span><i style={{ width: `${value}%` }} /></span><small>{level.replace("_", " ")}</small></div>; }

export default function MerchantsPage() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<TrustAssessment | null>(null);
  const [check, setCheck] = useState<PrecheckResponse | null>(null);
  const [checking, setChecking] = useState(false);
  const [form, setForm] = useState({ merchant_name: "Flash Prize Outlet", merchant_url: "", amount: "299" });
  const merchants = useQuery({ queryKey: ["merchants", search], queryFn: () => api.merchants(`page=1&page_size=100${search ? `&q=${encodeURIComponent(search)}` : ""}`) });
  const columns = useMemo<ColDef<TrustAssessment>[]>(() => [
    { headerName: "Merchant", field: "merchant_name", pinned: "left", cellRenderer: (params: { value: string }) => <div className="merchant-grid-cell"><span className="merchant-avatar">{params.value?.slice(0, 1)}</span>{params.value}</div> },
    { headerName: "Trust score", field: "trust_score", cellRenderer: (params: { data?: TrustAssessment }) => params.data ? <TrustCell value={params.data.trust_score} level={params.data.trust_level} /> : null },
    { headerName: "Recommendation", field: "recommendation", cellRenderer: (params: { value: string }) => <StatusBadge value={params.value} /> },
    { headerName: "Confidence", field: "confidence", valueFormatter: (params) => `${Math.round(Number(params.value) * 100)}%` },
    { headerName: "Flags", valueGetter: (params) => `${params.data?.red_flags?.length ?? 0} red · ${params.data?.green_flags?.length ?? 0} green` },
    { headerName: "Research", field: "research_mode", cellRenderer: (params: { value: string }) => <StatusBadge value={params.value} /> },
  ], []);
  const runCheck = async () => {
    setChecking(true);
    try { setCheck(await api.precheck({ user_id: "demo-user-1", merchant_name: form.merchant_name, merchant_url: form.merchant_url || null, amount: Number(form.amount), currency: "USD" })); }
    catch (error) { toast.error(error instanceof Error ? error.message : "Pre-payment check failed."); }
    finally { setChecking(false); }
  };
  if (merchants.isError) return <ErrorState message={merchants.error.message} onRetry={() => void merchants.refetch()} />;
  const data = merchants.data?.items ?? [];
  return <><PageHeading eyebrow="LAYER 3 · MERCHANT TRUST" title="Merchants" description="Know who you are paying before the money moves." action={<span className="status-badge trusted"><ShieldCheck size={13} />Evidence grounded</span>} /><div className="split-layout"><section className="panel"><div className="toolbar"><div className="search-wrap"><Search size={15} /><input className="search-input" placeholder="Search merchants…" value={search} onChange={(e) => setSearch(e.target.value)} /></div><button className="icon-button" aria-label="Refresh merchant list" onClick={() => void merchants.refetch()}><RefreshCw size={16} /></button></div><div className="grid-wrap ag-theme-quartz"><AgGridReact<TrustAssessment> theme={gridTheme} rowData={data} columnDefs={columns} defaultColDef={defaultColDef} onRowClicked={(event) => setSelected(event.data ?? null)} getRowId={(params) => params.data.merchant_id} /></div></section><aside className="panel"><div className="panel-heading"><div><h2>Pre-payment check</h2><p>Trust plus payment risk, before you pay.</p></div></div><div className="form-card"><div className="form-grid"><div className="field full"><label>Merchant name</label><input className="field-input" value={form.merchant_name} onChange={(e) => setForm({ ...form, merchant_name: e.target.value })} /></div><div className="field full"><label>Merchant URL (optional)</label><input className="field-input" placeholder="https://" value={form.merchant_url} onChange={(e) => setForm({ ...form, merchant_url: e.target.value })} /></div><div className="field"><label>Amount</label><input className="field-input" type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></div><div className="field"><label>Currency</label><input className="field-input" value="USD" readOnly /></div></div><div className="form-actions"><button className="button primary" onClick={runCheck} disabled={checking}>{checking ? "Checking…" : "Run pre-payment check"}</button></div></div>{check && <div className={`verdict ${check.combined_verdict}`}><strong>{check.combined_verdict.replaceAll("_", " ")}</strong><p>{check.combined_reasoning}</p><div className="action-row"><StatusBadge value={check.trust.trust_level} /><StatusBadge value={`payment risk ${check.payment_risk_score}`} /></div></div>}</aside></div>{selected && <><button className="drawer-backdrop" aria-label="Close merchant detail" onClick={() => setSelected(null)} /><aside className="drawer"><div className="drawer-header"><div><p className="eyebrow">TRUST ASSESSMENT</p><h2>{selected.merchant_name}</h2></div><button className="icon-button" aria-label="Close detail" onClick={() => setSelected(null)}>×</button></div><TrustCell value={selected.trust_score} level={selected.trust_level} /><p>{selected.reasoning}</p><h3>Green flags</h3><div className="signal-list">{(selected.green_flags ?? []).map((item) => <div className="signal positive" key={item}><strong>Positive evidence</strong><small>{item}</small></div>)}</div><h3>Red flags</h3><div className="signal-list">{(selected.red_flags ?? []).map((item) => <div className="signal negative" key={item}><strong>Risk evidence</strong><small>{item}</small></div>)}</div><h3>Research provenance</h3><p>{selected.research_mode} research · {selected.model} · {selected.llm_used ? "LLM used" : "Rules-only fallback"}</p><button className="button secondary" onClick={() => api.merchantTrust({ merchant_name: selected.merchant_name, refresh: true }).then((next) => { setSelected(next); toast.success("Merchant re-checked."); }).catch(() => toast.error("Re-check failed."))}><RefreshCw size={14} />Re-check</button></aside></>}</>;
}
