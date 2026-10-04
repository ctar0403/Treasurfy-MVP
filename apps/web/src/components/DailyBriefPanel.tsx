import { formatDate, formatMoney, formatTimestamp } from "../format";
import type { DailyBrief } from "../types";

type DailyBriefPanelProps = {
  brief: DailyBrief;
};

function metricValue(value: string, currency: string | null): string {
  return currency ? formatMoney(value, currency) : value;
}

export function DailyBriefPanel({ brief }: DailyBriefPanelProps) {
  return (
    <section id="brief" className="brief-section" aria-labelledby="daily-brief-title">
      <article className="brief-hero">
        <div className="brief-heading">
          <div>
            <p className="eyebrow">Daily control room / {formatDate(brief.as_of_date)}</p>
            <h2 id="daily-brief-title">{brief.headline}</h2>
          </div>
          <div className="brief-run-meta">
            <span className="grounded-badge">Grounded / {brief.evidence.length} sources</span>
            <span>{brief.reused_run ? "Inputs unchanged" : "New brief generated"}</span>
          </div>
        </div>
        <p className="brief-summary">{brief.summary}</p>
        <div className="brief-metrics">
          {brief.metrics.map((metric) => (
            <div className={`brief-metric brief-metric--${metric.tone}`} key={metric.key}>
              <span>{metric.label}</span>
              <strong>{metricValue(metric.value, metric.currency)}</strong>
              <small>{metric.context}</small>
            </div>
          ))}
        </div>
      </article>

      <div className="brief-grid">
        <article className="panel brief-highlights-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">What changed or needs attention</p>
              <h2>Exceptions</h2>
            </div>
            <span className="as-of">{brief.highlights.length} findings</span>
          </div>
          <div className="brief-list">
            {brief.highlights.map((highlight) => (
              <div className="brief-item" key={`${highlight.severity}-${highlight.title}`}>
                <span className={`brief-indicator brief-indicator--${highlight.severity}`} aria-hidden="true" />
                <div>
                  <strong>{highlight.title}</strong>
                  <p>{highlight.detail}</p>
                  <span>{highlight.evidence.length} linked evidence records</span>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel brief-actions-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Ordered by operational priority</p>
              <h2>Today&apos;s actions</h2>
            </div>
            <span className="as-of">{brief.actions.length} actions</span>
          </div>
          <ol className="action-list">
            {brief.actions.map((action) => (
              <li key={`${action.target_type}-${action.target_id}-${action.title}`}>
                <span className={`priority-tag priority-tag--${action.priority}`}>
                  {action.priority}
                </span>
                <div>
                  <strong>{action.title}</strong>
                  <p>{action.detail}</p>
                </div>
              </li>
            ))}
          </ol>
          <details className="evidence-details">
            <summary>View calculation evidence</summary>
            <ul>
              {brief.evidence.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </details>
          <p className="brief-generated">Generated {formatTimestamp(brief.generated_at)}</p>
        </article>
      </div>
    </section>
  );
}
