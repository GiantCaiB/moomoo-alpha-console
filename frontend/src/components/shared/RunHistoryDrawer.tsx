import { X } from "lucide-react";
import StatusBadge from "@/components/shared/StatusBadge";

export interface RunHistoryItem {
  id: string;
  strategy_name: string;
  strategy_version: string | null;
  status: string;
  scanned_count: number;
  generated_count: number;
  data_error_count: number;
  finished_at: string | null;
  created_at: string;
  error_message: string | null;
}

function runStatus(run: RunHistoryItem): string {
  if (run.status === "COMPLETED" && run.data_error_count > 0) return "COMPLETED_WITH_ERRORS";
  return run.status;
}

function formatTimestamp(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Not finished";
}

export default function RunHistoryDrawer({
  title,
  runs,
  onClose,
}: {
  title: string;
  runs: RunHistoryItem[];
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <aside
        className="ml-auto flex h-full w-[min(480px,100vw)] flex-col border-l border-surface-border bg-[#090d14] shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="flex shrink-0 items-center justify-between border-b border-surface-border px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
            <p className="mt-1 text-xs leading-relaxed text-text-muted">
              Run history may include older runs. Current pages only show records relevant to the current universe or current holdings.
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-text-muted hover:bg-surface-hover hover:text-text-primary" aria-label="Close run history">
            <X size={18} />
          </button>
        </header>
        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-5">
          {runs.length === 0 ? (
            <p className="py-10 text-center text-sm text-text-muted">No runs recorded yet.</p>
          ) : runs.map((run) => (
            <article
              key={run.id}
              className={`rounded-xl border p-4 ${run.status === "FAILED" ? "border-accent-red/40 bg-accent-red/10" : run.status === "COMPLETED" && run.data_error_count > 0 ? "border-accent-amber/35 bg-accent-amber/10" : "border-accent-green/20 bg-accent-green/5"}`}
            >
              <div className="flex items-start justify-between gap-3">
                <StatusBadge status={runStatus(run)} />
                <span className="font-mono text-[11px] text-text-muted">{run.id.slice(0, 8)}</span>
              </div>
              <p className="mt-3 text-sm font-medium text-text-primary">
                {run.strategy_name} {run.strategy_version ? `v${run.strategy_version}` : ""}
              </p>
              <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                <div><p className="text-text-muted">Scanned</p><p className="mt-1 font-mono text-text-secondary">{run.scanned_count}</p></div>
                <div><p className="text-text-muted">Generated</p><p className="mt-1 font-mono text-text-secondary">{run.generated_count}</p></div>
                <div><p className="text-text-muted">Data errors</p><p className="mt-1 font-mono text-text-secondary">{run.data_error_count}</p></div>
              </div>
              <p className="mt-3 text-xs text-text-muted">Finished {formatTimestamp(run.finished_at ?? run.created_at)}</p>
              {run.error_message && <p className="mt-2 rounded-lg border border-accent-red/25 bg-accent-red/10 p-2 text-xs leading-relaxed text-accent-red">{run.error_message}</p>}
            </article>
          ))}
        </div>
      </aside>
    </div>
  );
}
