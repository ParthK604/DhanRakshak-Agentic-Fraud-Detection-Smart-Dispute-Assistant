"use client";

import { AgCharts } from "ag-charts-react";
import type { AgChartOptions } from "ag-charts-community";
import "@/lib/ag-grid";
import { ArrowUpRight, CircleDollarSign, CloudDownload, ShieldAlert, Store, WalletCards } from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { PageHeading, StatCard, StatusBadge, ErrorState } from "@/components/ui";
import { useState } from "react";

export default function Home() {
  const [syncing, setSyncing] = useState(false);
  const risk = useQuery({ queryKey: ["risk-summary"], queryFn: api.riskSummary });
  const disputes = useQuery({ queryKey: ["dispute-summary"], queryFn: api.disputeSummary });
  const merchants = useQuery({ queryKey: ["merchant-summary"], queryFn: api.merchantSummary });
  const transactions = useQuery({
    queryKey: ["recent-transactions"],
    queryFn: () => api.transactions(new URLSearchParams({ user_id: "demo-user-1", page: "1", page_size: "8", sort_by: "timestamp", sort_dir: "desc" })),
  });
  const sync = async () => {
    setSyncing(true);
    try {
      await api.sync();
      toast.success("PayPal sandbox sync completed.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "PayPal sync is unavailable.");
    } finally { setSyncing(false); }
  };
  const riskData = [
    { label: "Low", value: risk.data?.low ?? 0, color: "#2fa878" },
    { label: "Medium", value: risk.data?.medium ?? 0, color: "#e3ae49" },
    { label: "High", value: risk.data?.high ?? 0, color: "#db655b" },
  ];
  const chartOptions: AgChartOptions = {
    data: riskData.map((x) => ({ level: x.label, count: x.value })),
    series: [{ type: "bar" as const, xKey: "level", yKey: "count", fill: "#0f766e", stroke: "#0f766e" }],
    background: { fill: "transparent" },
    legend: { enabled: false },
  };
  if (risk.isError || disputes.isError || merchants.isError) return <ErrorState message="The dashboard could not reach the backend." onRetry={() => { void risk.refetch(); void disputes.refetch(); void merchants.refetch(); }} />;
  return (
    <>
      <PageHeading eyebrow="OVERVIEW" title="Good morning, stay protected." description="One calm view of the activity DhanRakshak is watching for you." action={<Link className="button primary" href="/merchants"><ShieldAlert size={16} />Pre-payment check</Link>} />
      <div className="stat-grid">
        <StatCard label="Transactions analysed" value={risk.data?.total ?? "—"} note="Across your account" tone="teal" icon={CircleDollarSign} />
        <StatCard label="High-risk flagged" value={risk.data?.high ?? "—"} note="Needs your attention" tone="red" icon={ShieldAlert} />
        <StatCard label="Open disputes" value={disputes.data?.total ?? "—"} note="Cases in progress" tone="amber" icon={WalletCards} />
        <StatCard label="Refund estimated" value={`$${(disputes.data?.total_refund_amount ?? 0).toFixed(2)}`} note="Evidence-backed estimate" tone="blue" icon={ArrowUpRight} />
        <StatCard label="High-risk merchants" value={merchants.data?.by_level?.high_risk ?? 0} note="Trust checks completed" tone="purple" icon={Store} />
      </div>
      <div className="dashboard-grid">
        <section className="panel"><div className="panel-heading"><div><h2>Risk distribution</h2><p>Deterministic signals across analysed transactions</p></div><StatusBadge value="live" /></div><div style={{ height: 220 }}><AgCharts options={chartOptions} /></div></section>
        <section className="panel"><div className="panel-heading"><div><h2>Risk posture</h2><p>A quick view of what needs attention</p></div></div><div className="donut-wrap"><div className="donut"><div className="donut-center"><strong>{risk.data?.total ?? 0}</strong><small>analysed</small></div></div><div className="legend">{riskData.map((item) => <div className="legend-item" key={item.label}><i className="legend-dot" style={{ background: item.color }} />{item.label}<b>{item.value}</b></div>)}<div className="legend-item"><span>Average score</span><b>{risk.data?.average_score?.toFixed(0) ?? "—"}</b></div></div></div></section>
      </div>
      <div className="dashboard-grid">
        <section className="panel"><div className="panel-heading"><div><h2>Recent activity</h2><p>Latest transactions from the seeded or PayPal sandbox feed</p></div><Link className="text-link" href="/transactions">View all <ArrowUpRight size={14} /></Link></div><div className="recent-list">{transactions.data?.items.map((row) => <div className="recent-row" key={row.txn_id}><div className="recent-info"><span className="merchant-avatar">{row.merchant_name.slice(0, 1).toUpperCase()}</span><div><strong>{row.merchant_name}</strong><small>{row.source.replace("_", " ")} · {new Date(row.timestamp).toLocaleDateString()}</small></div></div><span className="recent-score">{row.amount.toLocaleString(undefined, { style: "currency", currency: row.currency })}</span></div>)}</div></section>
        <section className="paypal-card"><div><p className="eyebrow" style={{ color: "#a9e5db" }}>PAYPAL CONNECTION</p><h2>Sandbox data bridge</h2><p>Keep the dashboard grounded in the activity PayPal shares with DhanRakshak.</p><button className="button" onClick={sync} disabled={syncing}><CloudDownload size={16} />{syncing ? "Syncing…" : "Sync from PayPal sandbox"}</button></div><div className="paypal-orb"><CircleDollarSign size={23} /></div></section>
      </div>
      <p className="footer-note">AI output is advisory. Every score is shown with its deterministic signals, evidence, and model provenance.</p>
    </>
  );
}
