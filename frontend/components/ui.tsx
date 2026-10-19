import { AlertCircle, CheckCircle2, Info } from "lucide-react";

export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>{action}</div>;
}

export function StatCard({ label, value, note, tone = "teal", icon: Icon }: { label: string; value: string | number; note: string; tone?: string; icon: React.ComponentType<{ size?: number }> }) {
  return <div className="stat-card"><div className={`stat-icon ${tone}`}><Icon size={19} /></div><div className="stat-copy"><span>{label}</span><strong>{value}</strong><small>{note}</small></div></div>;
}

export function StatusBadge({ value }: { value?: string | null }) {
  const label = value?.trim() || "Unknown";
  return <span className={`status-badge ${label.toLowerCase().replaceAll("_", "-")}`}><span className="status-dot" />{label.replaceAll("_", " ")}</span>;
}

export function EmptyState({ title, description, icon: Icon = Info }: { title: string; description: string; icon?: React.ComponentType<{ size?: number }> }) {
  return <div className="empty-state"><Icon size={28} /><strong>{title}</strong><p>{description}</p></div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="error-state"><AlertCircle size={22} /><div><strong>Could not load this view</strong><p>{message}</p>{onRetry && <button className="button secondary" onClick={onRetry}>Try again</button>}</div></div>;
}

export function SuccessNote({ children }: { children: React.ReactNode }) {
  return <div className="success-note"><CheckCircle2 size={17} />{children}</div>;
}
