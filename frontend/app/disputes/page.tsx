"use client";

import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";
import { Copy, MessageCircle, Plus, Send, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, demoUserId, type ChatResponse, type DisputeRecord } from "@/lib/api";
import { defaultColDef, gridTheme } from "@/lib/ag-grid";
import { PageHeading, StatusBadge, ErrorState } from "@/components/ui";

export default function DisputesPage() {
  const [selected, setSelected] = useState<DisputeRecord | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(() => typeof window === "undefined" ? undefined : sessionStorage.getItem("dhanrakshak-dispute-session") ?? undefined);
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string; response?: ChatResponse }[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const disputes = useQuery({ queryKey: ["disputes"], queryFn: api.disputes });
  const columns = useMemo<ColDef<DisputeRecord>[]>(() => [
    { headerName: "Issue", field: "issue_type", cellRenderer: (params: { value: string }) => <StatusBadge value={params.value} /> },
    { headerName: "Merchant", valueGetter: (params) => params.data?.evidence.matched_txns[0]?.merchant_name ?? "Multiple" },
    { headerName: "Refund estimate", valueGetter: (params) => params.data ? `${params.data.refund.currency} ${params.data.refund.amount.toFixed(2)}` : "" },
    { headerName: "Status", field: "status", cellRenderer: (params: { value: string }) => <StatusBadge value={params.value} /> },
    { headerName: "Submission", field: "submission_mode", cellRenderer: (params: { value: string }) => <StatusBadge value={params.value === "paypal" ? "Filed with PayPal" : "Prepared · not filed"} /> },
    { headerName: "Created", field: "created_at", valueFormatter: (params) => params.value ? new Date(params.value).toLocaleDateString() : "" },
  ], []);
  const send = async (action?: "confirm" | "cancel" | "select_transaction", payload?: Record<string, unknown>) => {
    const text = message.trim();
    if (!action && !text) return;
    setLoading(true);
    if (text) setMessages((items) => [...items, { role: "user", text }]);
    setMessage("");
    try {
      const response = await api.chat({ user_id: demoUserId, session_id: sessionId, message: action ? null : text, action: action ?? null, payload: payload ?? null });
      setSessionId(response.session_id); sessionStorage.setItem("dhanrakshak-dispute-session", response.session_id);
      setMessages((items) => [...items, { role: "assistant", text: response.reply, response }]);
    } catch (error) { toast.error(error instanceof Error ? error.message : "The dispute assistant is unavailable."); }
    finally { setLoading(false); }
  };
  const newConversation = () => { sessionStorage.removeItem("dhanrakshak-dispute-session"); setSessionId(undefined); setMessages([]); };
  if (disputes.isError) return <ErrorState message={disputes.error.message} onRetry={() => void disputes.refetch()} />;
  return <>
    <PageHeading eyebrow="LAYER 2 · SMART DISPUTES" title="Disputes" description="Turn a confusing charge into grounded evidence, a fair estimate, and clear next steps." action={<button className="button secondary" onClick={newConversation}><Plus size={15} />New conversation</button>} />
    <div className="split-layout"><section className="panel"><div className="panel-heading"><div><h2>Case history</h2><p>Honest status for every dispute submission.</p></div></div><div className="grid-wrap ag-theme-quartz"><AgGridReact theme={gridTheme} rowData={disputes.data?.items ?? []} columnDefs={columns} defaultColDef={defaultColDef} onRowClicked={(event) => setSelected(event.data ?? null)} getRowId={(params) => params.data.dispute_id} /></div></section><section className="panel chat"><div className="panel-heading"><div><h2><MessageCircle size={16} style={{ verticalAlign: "middle", marginRight: 7 }} />Dispute assistant</h2><p>Facts first. Filing only after explicit confirmation.</p></div></div>{messages.length === 0 && <div className="empty-state"><MessageCircle size={27} /><strong>Tell me what happened</strong><p>Try “I was charged twice for Netflix”.</p><div className="action-row"><button className="filter-chip" onClick={() => setMessage("I was charged twice for Netflix")}>Duplicate Netflix charge</button><button className="filter-chip" onClick={() => setMessage("I was overcharged at Spotify")}>Wrong amount</button></div></div>}<div className="chat-messages">{messages.map((item, index) => <div key={`${item.role}-${index}`}><div className={`chat-message ${item.role}`}>{item.text}</div>{item.response && <div className="evidence-card">{item.response.evidence && <><strong>Evidence ready</strong><p>{item.response.evidence.facts.slice(0, 3).join(" · ")}</p></>}{item.response.refund && <p><strong>Estimated refund:</strong> {item.response.refund.currency} {item.response.refund.amount.toFixed(2)}<br /><small>{item.response.refund.disclaimer}</small></p>}{item.response.letter && <p><strong>{item.response.letter.subject}</strong><br />{item.response.letter.body.slice(0, 180)}…</p>}{item.response.awaiting_confirmation && <div className="action-row"><button className="button primary" onClick={() => void send("confirm")}>Confirm submission</button><button className="button secondary" onClick={() => void send("cancel")}><X size={13} />Cancel</button></div>}{item.response.suggested_actions?.map((action) => <button key={action.label} className="filter-chip" onClick={() => void send(action.action === "select_transaction" ? "select_transaction" : undefined, action.payload)}>{action.label}</button>)}</div>}</div>)}</div><div className="chat-compose"><input className="field-input" aria-label="Message dispute assistant" placeholder="Describe the charge…" value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void send(); }} /><button className="button primary" aria-label="Send message" disabled={loading} onClick={() => void send()}><Send size={15} /></button></div></section></div>
    {selected && <><button className="drawer-backdrop" aria-label="Close dispute detail" onClick={() => setSelected(null)} /><aside className="drawer"><div className="drawer-header"><div><p className="eyebrow">DISPUTE CASE</p><h2>{selected.issue_type.replaceAll("_", " ")}</h2></div><button className="icon-button" aria-label="Close detail" onClick={() => setSelected(null)}>×</button></div><StatusBadge value={selected.submission_mode === "paypal" ? "Filed with PayPal" : "Prepared · not filed"} /><h3>Letter</h3><p><strong>{selected.letter.subject}</strong></p><p>{selected.letter.body}</p><button className="button secondary" onClick={() => { void navigator.clipboard.writeText(selected.letter.body); toast.success("Letter copied."); }}><Copy size={14} />Copy letter</button><h3>Resolution steps</h3><div className="signal-list">{selected.steps.map((step) => <div className="signal" key={step.order}><strong>{step.order}. {step.title}</strong><small>{step.detail}</small></div>)}</div></aside></>}
  </>;
}
