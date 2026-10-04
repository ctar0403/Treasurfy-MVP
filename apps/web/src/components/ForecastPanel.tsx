import { formatDate, formatMoney, formatTimestamp } from "../format";
import type { Forecast } from "../types";
import { ForecastChart } from "./ForecastChart";
import { StatusBadge } from "./StatusBadge";

type ForecastPanelProps = {
  forecast: Forecast;
};

export function ForecastPanel({ forecast }: ForecastPanelProps) {
  return (
    <section className="forecast-section" aria-labelledby="forecast-title">
      <article className="panel forecast-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Forward view</p>
            <h2 id="forecast-title">90-day cash forecast</h2>
          </div>
          <span className="profile-tag">Deterministic model</span>
        </div>
        <div className="horizon-grid">
          {forecast.horizons.map((horizon) => {
            const change = Number(horizon.change_from_opening);
            return (
              <div className="horizon-card" key={horizon.days}>
                <span>{horizon.days}-day position</span>
                <strong>{formatMoney(horizon.total_cash, forecast.base_currency)}</strong>
                <small className={change < 0 ? "negative-change" : "positive-change"}>
                  {change >= 0 ? "+" : ""}
                  {formatMoney(horizon.change_from_opening, forecast.base_currency)} from today
                </small>
              </div>
            );
          })}
        </div>
        <ForecastChart points={forecast.points} currency={forecast.base_currency} />
        <div className="forecast-meta">
          <span>As of {formatDate(forecast.as_of_date)}</span>
          <span>{forecast.expected_flows.length} planned cash flows</span>
          <span>{forecast.reused_run ? "Verified existing run" : "New run generated"}</span>
        </div>
      </article>

      <div className="forecast-detail-grid">
        <article className="panel liquidity-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Threshold monitoring</p>
              <h2>Liquidity risks</h2>
            </div>
            <span className={`risk-count ${forecast.alerts.length ? "risk-count--active" : ""}`}>
              {forecast.alerts.length} alerts
            </span>
          </div>
          {forecast.alerts.length === 0 ? (
            <p className="empty-state">No entity is projected below its minimum balance.</p>
          ) : (
            <div className="alert-list">
              {forecast.alerts.map((alert) => (
                <div className="liquidity-alert" key={`${alert.entity_id}-${alert.breach_date}`}>
                  <span className="alert-icon" aria-hidden="true">!</span>
                  <div>
                    <strong>{alert.entity_name}</strong>
                    <p>{alert.message}</p>
                    <span>
                      {formatMoney(alert.projected_balance, forecast.base_currency)} projected /{" "}
                      {formatMoney(alert.minimum_balance, forecast.base_currency)} minimum
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="entity-forecast-list">
            {forecast.entities
              .slice()
              .sort((a, b) => a.rank_at_30_days - b.rank_at_30_days)
              .map((entity) => (
                <div className="entity-forecast-row" key={entity.entity_id}>
                  <span className="rank">#{entity.rank_at_30_days}</span>
                  <div>
                    <strong>{entity.entity_name}</strong>
                    <span>30-day projected position</span>
                  </div>
                  <strong>{formatMoney(entity.projected_30_days, forecast.base_currency)}</strong>
                  <StatusBadge status={entity.status} />
                </div>
              ))}
          </div>
        </article>

        <article className="panel flows-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Forecast inputs</p>
              <h2>Upcoming cash flows</h2>
            </div>
            <span className="as-of">Generated {formatTimestamp(forecast.created_at)}</span>
          </div>
          <div className="flow-list">
            {forecast.expected_flows.map((flow) => (
              <div className="flow-row" key={flow.id}>
                <span className={`flow-direction flow-direction--${flow.direction}`} aria-hidden="true">
                  {flow.direction === "inflow" ? "+" : "-"}
                </span>
                <div>
                  <strong>{flow.name}</strong>
                  <span>{flow.entity_name} / {formatDate(flow.due_date)}</span>
                </div>
                <strong className={flow.direction === "inflow" ? "positive-change" : "negative-change"}>
                  {formatMoney(flow.base_currency_amount, forecast.base_currency)}
                </strong>
              </div>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}
