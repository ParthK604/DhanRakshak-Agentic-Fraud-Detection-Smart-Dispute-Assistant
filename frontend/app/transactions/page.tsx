"use client";

import { AgGridReact } from "ag-grid-react";
import type { ColDef, IDatasource, IGetRowsParams } from "ag-grid-community";
import { ArrowRight, Download, RefreshCw, Search, Zap } from "lucide-react";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { api, type RiskAssessment, type Transaction } from "@/lib/api";
import { defaultColDef, gridTheme } from "@/lib/ag-grid";
import { PageHeading, StatusBadge } from "@/components/ui";

type GridRow = Transaction & { risk?: RiskAssessment };

function RiskCell({ value }: { value?: number }) {
  const score = value ?? 0;
  return <div className="risk-cell"><strong>{value == null ? "—" : score}</strong>{value != null && <span><i style={{ width: `${score}%` }} /></span>}<small>{value == null ? "not scored" : score >= 70 ? "high" : score >= 35 ? "medium" : "low"}</small></div>;
}

export default function TransactionsPage() {
  const gridRef = useRef<AgGridReact<GridRow>>(null);
  const [search, setSearch] = useState("");
  const [level, setLevel] = useState("");
  const [selected, setSelected] = useState<GridRow | null>(null);
  const [form, setForm] = useState({ merchant_name: "Northstar Electronics", amount: "1250", country: "US", payee_email: "orders@example.com" });
  const [scoring, setScoring] = useState(false);
  const datasource = useMemo<IDatasource>(() => ({
    getRows: async (params: IGetRowsParams) => {
      try {
        const page = Math.floor(params.startRow / 50) + 1;
        const query = new URLSearchParams({ user_id: "demo-user-1", page: String(page), page_size: "50", sort_by: "timestamp", sort_dir: "desc" });
        if (search) query.set("merchant", search);
        const [transactions, scores] = await Promise.all([api.transactions(query), api.riskScores(new URLSearchParams({ user_id: "demo-user-1", page: String(page), page_size: "50" }))]);
        const scoreMap = new Map(scores.items.map((item) => [item.txn_id, item]));
        const rows = transactions.items.map((item) => ({ ...item, risk: scoreMap.get(item.txn_id) })).filter((item) => !level || item.risk?.risk_level === level);
        params.successCallback(rows, page * 50 >= transactions.total ? transactions.total : -1);
      } catch { params.failCallback(); }
    },
  }), [search, level]);
  const columns = useMemo<ColDef<GridRow>[]>(() => [
    { headerName: "Merchant", field: "merchant_name", pinned: "left", cellRenderer: (params: { value: string }) => <div className="merchant-grid-cell"><span className="merchant-avatar">{params.value?.slice(0, 1)}</span>{params.value}</div> },
    { headerName: "Amount", field: "amount", valueFormatter: (params) => params.value == null || Number.isNaN(Number(params.value)) ? "—" : `${params.data?.currency ?? "USD"} ${Number(params.value).toFixed(2)}` },
    { headerName: "Risk score", field: "risk", cellRenderer: (params: { data?: GridRow }) => <RiskCell value={params.data?.risk?.risk_score} />, sort: "desc" },
    { headerName: "Signals", field: "risk", cellRenderer: (params: { data?: GridRow }) => <div className="signal-chips">{params.data?.risk?.signals.filter((x) => x.triggered).slice(0, 2).map((x) => <span key={x.name} title={x.evidence}>{x.name.replaceAll("_", " ")}</span>) ?? <small>—</small>}</div> },
    { headerName: "Source", field: "source", cellRenderer: (params: { value: string }) => <StatusBadge value={params.value === "paypal_sandbox" ? "PayPal sandbox" : params.value} /> },
    { headerName: "When", field: "timestamp", valueFormatter: (params) => params.value ? new Date(params.value).toLocaleString() : "" },
  ], []);
  const runScore = async () => {
    setScoring(true);
    try {
      await api.scoreIncoming({ txn_id: `sim-${Date.now()}`, user_id: "demo-user-1", amount: Number(form.amount), currency: "USD", merchant_name: form.merchant_name, country: form.country, payee_email: form.payee_email, direction: "outgoing", timestamp: new Date().toISOString(), status: "PENDING" });
      toast.success("Payment scored. The result is now in the risk stream.");
      gridRef.current?.api.refreshInfiniteCache();
    } catch (error) { toast.error(error instanceof Error ? error.message : "Could not score payment."); }
    finally { setScoring(false); }
  };
  return <>
    <PageHeading eyebrow="LAYER 1 · REAL-TIME RISK" title="Transactions" description="Every payment, its risk posture, and the evidence behind the recommendation." action={<button className="button secondary" onClick={() => gridRef.current?.api.exportDataAsCsv()}><Download size={16} />Export loaded rows</button>} />
    <div className="split-layout">
      <section className="panel"><div className="toolbar"><div className="search-wrap"><Search size={15} /><input className="search-input" placeholder="Search merchant…" value={search} onChange={(e) => setSearch(e.target.value)} /></div>{["", "high", "medium", "low"].map((item) => <button key={item || "all"} className={`filter-chip ${level === item ? "active" : ""}`} onClick={() => setLevel(item)}>{item || "All risk"}</button>)}<button className="icon-button" aria-label="Refresh transactions" onClick={() => gridRef.current?.api.refreshInfiniteCache()}><RefreshCw size={16} /></button></div><div className="grid-wrap ag-theme-quartz"><AgGridReact ref={gridRef} theme={gridTheme} columnDefs={columns} defaultColDef={defaultColDef} rowModelType="infinite" cacheBlockSize={50} maxBlocksInCache={4} datasource={datasource} onRowClicked={(event) => setSelected(event.data ?? null)} getRowId={(params) => params.data.txn_id} /></div></section>
      <aside className="panel"><div className="panel-heading"><div><h2>Live risk scoring</h2><p>Simulate an incoming payment for the demo.</p></div><Zap size={19} color="var(--teal)" /></div><div className="form-card"><div className="form-grid"><div className="field full"><label>Merchant</label><input className="field-input" value={form.merchant_name} onChange={(e) => setForm({ ...form, merchant_name: e.target.value })} /></div><div className="field"><label>Amount</label><input className="field-input" type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></div><div className="field"><label>Country</label><input className="field-input" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} /></div><div className="field full"><label>Payee email</label><input className="field-input" value={form.payee_email} onChange={(e) => setForm({ ...form, payee_email: e.target.value })} /></div></div><div className="form-actions"><button className="button primary" disabled={scoring} onClick={runScore}><Zap size={15} />{scoring ? "Analysing…" : "Score payment"}</button></div></div><p className="footer-note">Signals are computed deterministically first; AI explains the evidence and remains advisory.</p></aside>
    </div>
    {selected && <><button className="drawer-backdrop" aria-label="Close detail" onClick={() => setSelected(null)} /><aside className="drawer"><div className="drawer-header"><div><p className="eyebrow">TRANSACTION DETAIL</p><h2>{selected.merchant_name}</h2></div><button className="icon-button" aria-label="Close detail" onClick={() => setSelected(null)}>×</button></div><div className="detail-score"><RiskCell value={selected.risk?.risk_score} /></div><p>{selected.risk?.reasoning ?? "This transaction has not been scored yet."}</p><h3>Evidence signals</h3><div className="signal-list">{selected.risk?.signals.filter((x) => x.triggered).map((signal) => <div className="signal" key={signal.name}><strong>{signal.name.replaceAll("_", " ")}</strong><small>{signal.evidence}</small></div>) ?? <div className="signal">No fired signals.</div>}</div>{selected.risk && <><h3>AI provenance</h3><p>{selected.risk.model} · {selected.risk.llm_used ? "LLM reasoning used" : "Rules-only fallback"}</p><div className="action-row"><button className="button secondary" onClick={() => api.score(selected.txn_id, true).then(() => toast.success("Transaction re-scored.")).catch(() => toast.error("Re-score failed."))}><RefreshCw size={14} />Re-score</button><Link className="button primary" href={`/disputes?txn=${encodeURIComponent(selected.txn_id)}`}><ArrowRight size={14} />Dispute this charge</Link></div></>}</aside></>}
  </>;
}
