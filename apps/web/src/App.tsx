import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getCashPosition,
  getImportHistory,
  getPaymentProfiles,
  getPayments,
  runDailyBrief,
  runForecast,
  uploadBankCsv,
} from "./api";
import { ForecastPanel } from "./components/ForecastPanel";
import { DailyBriefPanel } from "./components/DailyBriefPanel";
import { PaymentPanel } from "./components/PaymentPanel";
import { StatusBadge } from "./components/StatusBadge";
import { formatMoney, formatTimestamp } from "./format";
import type {
  CashPosition,
  DailyBrief,
  Forecast,
  ImportRun,
  Payment,
  PaymentProfile,
} from "./types";
import "./styles.css";

function initials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
}

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    window.localStorage.getItem("treasurfy-theme") === "dark" ? "dark" : "light",
  );
  const [cash, setCash] = useState<CashPosition | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [dailyBrief, setDailyBrief] = useState<DailyBrief | null>(null);
  const [imports, setImports] = useState<ImportRun[]>([]);
  const [paymentProfiles, setPaymentProfiles] = useState<PaymentProfile[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<ImportRun | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    window.localStorage.setItem("treasurfy-theme", theme);
  }, [theme]);

  const loadDashboard = useCallback(async () => {
    try {
      setError(null);
      const [cashPosition, importHistory, forecastResult, profilesResult, paymentsResult] = await Promise.all([
        getCashPosition(),
        getImportHistory(),
        runForecast(),
        getPaymentProfiles(),
        getPayments(),
      ]);
      const briefResult = await runDailyBrief();
      setCash(cashPosition);
      setImports(importHistory);
      setForecast(forecastResult);
      setPaymentProfiles(profilesResult);
      setPayments(paymentsResult);
      setDailyBrief(briefResult);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load the TreasurFy workspace.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshPayments = useCallback(async () => {
    const [paymentsResult, briefResult] = await Promise.all([
      getPayments(),
      runDailyBrief(),
    ]);
    setPayments(paymentsResult);
    setDailyBrief(briefResult);
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const largestEntityAmount = useMemo(() => {
    if (!cash?.entities.length) return 1;
    return Math.max(
      ...cash.entities.map((entity) => Number(entity.base_currency_balance)),
    );
  }, [cash]);

  async function handleUpload() {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);
    setUploadResult(null);
    try {
      const result = await uploadBankCsv(selectedFile);
      setUploadResult(result);
      setSelectedFile(null);
      if (fileInput.current) fileInput.current.value = "";
      await loadDashboard();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The CSV import failed.",
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="app-shell" data-theme={theme}>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="TreasurFy dashboard">
          <img
            className="brand-logo"
            src={theme === "dark" ? "/treasurfy-logo-light.png" : "/treasurfy-logo-dark.png"}
            alt=""
            aria-hidden="true"
          />
        </a>
        <nav className="topbar-nav" aria-label="Dashboard sections">
          <a href="#brief">Brief</a>
          <a href="#forecast">Forecast</a>
          <a href="#payments">Payments</a>
          <a href="#accounts">Accounts</a>
        </nav>
        <div className="topbar-actions">
          <button
            className="theme-toggle"
            type="button"
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
            aria-pressed={theme === "dark"}
            onClick={() => setTheme((current) => current === "dark" ? "light" : "dark")}
          >
            <span aria-hidden="true">{theme === "dark" ? "☀" : "◐"}</span>
            {theme === "dark" ? "Light" : "Dark"}
          </button>
          <span className="environment-pill">
            <span className="pulse-dot" aria-hidden="true" /> Demo workspace
          </span>
          <span className="avatar" aria-label="TreasurFy Admin">
            TA
          </span>
        </div>
      </header>

      <main id="top" className="page">
        <section className="page-heading">
          <div>
            <p className="eyebrow">Cash visibility</p>
            <h1>TreasurFy overview</h1>
            <p className="lede">
              One view of cash across every entity, bank, and currency.
            </p>
          </div>
          <button className="secondary-button" onClick={() => void loadDashboard()}>
            Refresh data
          </button>
        </section>

        {error && (
          <div className="message message--error" role="alert">
            <strong>Something needs attention.</strong>
            <span>{error}</span>
          </div>
        )}

        {loading && !cash ? (
          <div className="loading-card" role="status">
            Loading TreasurFy data…
          </div>
        ) : cash ? (
          <>
            <section className="metric-grid" aria-label="Cash summary">
              <article className="metric-card metric-card--primary">
                <span className="metric-label">Total cash</span>
                <strong>{formatMoney(cash.total_cash, cash.base_currency)}</strong>
                <span>Converted to {cash.base_currency}</span>
              </article>
              <article className="metric-card">
                <span className="metric-label">Legal entities</span>
                <strong>{cash.entity_count}</strong>
                <span>{cash.entities.map((entity) => entity.country_code).join(", ")}</span>
              </article>
              <article className="metric-card">
                <span className="metric-label">Bank accounts</span>
                <strong>{cash.account_count}</strong>
                <span>Across {new Set(cash.accounts.map((item) => item.bank_name)).size} banks</span>
              </article>
              <article className="metric-card">
                <span className="metric-label">Data health</span>
                <strong className={cash.stale_account_count ? "warning-text" : "healthy-text"}>
                  {cash.stale_account_count ? `${cash.stale_account_count} stale` : "Current"}
                </strong>
                <span>Oldest: {formatTimestamp(cash.oldest_balance_as_of)}</span>
              </article>
            </section>

            {cash.stale_account_count > 0 && (
              <div className="message message--warning" role="status">
                <strong>Some balances need refreshing.</strong>
                <span>
                  {cash.stale_account_count}{" "}
                  {cash.stale_account_count === 1 ? "account is" : "accounts are"} older
                  than 24 hours. Totals remain visible, with freshness shown below.
                </span>
              </div>
            )}

            {dailyBrief && <DailyBriefPanel brief={dailyBrief} />}

            {forecast && <ForecastPanel forecast={forecast} />}

            <PaymentPanel
              accounts={cash.accounts}
              profiles={paymentProfiles}
              payments={payments}
              onPaymentsChanged={refreshPayments}
            />

            <section className="dashboard-grid">
              <article className="panel entity-panel">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">Liquidity by company</p>
                    <h2>Entity cash position</h2>
                  </div>
                  <span className="as-of">FX as of {formatTimestamp(cash.fx_rate_as_of)}</span>
                </div>
                <div className="entity-list">
                  {cash.entities.map((entity) => {
                    const percentage = Math.max(
                      4,
                      (Number(entity.base_currency_balance) / largestEntityAmount) * 100,
                    );
                    return (
                      <div className="entity-row" key={entity.entity_id}>
                        <span className="entity-monogram" aria-hidden="true">
                          {initials(entity.entity_name)}
                        </span>
                        <div className="entity-detail">
                          <div className="entity-title">
                            <span>{entity.entity_name}</span>
                            <strong>
                              {formatMoney(entity.base_currency_balance, cash.base_currency)}
                            </strong>
                          </div>
                          <div className="bar-track" aria-hidden="true">
                            <span style={{ width: `${percentage}%` }} />
                          </div>
                          <span className="entity-meta">
                            {entity.country_code} · {entity.account_count} accounts
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </article>

              <article className="panel import-panel">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">Reusable profile</p>
                    <h2>Import bank data</h2>
                  </div>
                  <span className="profile-tag">CSV v1.0.0</span>
                </div>
                <p className="panel-copy">
                  Add balances and transactions. Existing files and transaction IDs are
                  detected before duplicate data is written.
                </p>
                <label className="file-drop">
                  <span className="upload-icon" aria-hidden="true">↑</span>
                  <strong>{selectedFile ? selectedFile.name : "Choose a CSV file"}</strong>
                  <span>{selectedFile ? `${Math.ceil(selectedFile.size / 1024)} KB selected` : "UTF-8 · maximum 2 MB"}</span>
                  <input
                    ref={fileInput}
                    type="file"
                    accept=".csv,text/csv"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                  />
                </label>
                <button
                  className="primary-button"
                  disabled={!selectedFile || uploading}
                  onClick={() => void handleUpload()}
                >
                  {uploading ? "Importing…" : "Import selected file"}
                </button>

                {uploadResult && (
                  <div className="import-result" role="status">
                    <div>
                      <StatusBadge status={uploadResult.status} />
                      {uploadResult.duplicate_file && <span>Existing run returned</span>}
                    </div>
                    <p>
                      {uploadResult.accepted_rows} accepted · {uploadResult.rejected_rows}{" "}
                      rejected · {uploadResult.skipped_duplicate_rows} duplicates skipped
                    </p>
                    {uploadResult.issues.length > 0 && (
                      <ul>
                        {uploadResult.issues.map((issue) => (
                          <li key={`${issue.row_number}-${issue.code}`}>
                            Row {issue.row_number}: {issue.message}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </article>
            </section>

            <section id="accounts" className="panel accounts-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Account detail</p>
                  <h2>Balances across banks</h2>
                </div>
                <span className="as-of">{cash.base_currency} reporting currency</span>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th>Entity</th>
                      <th>Native balance</th>
                      <th>Base currency</th>
                      <th>Freshness</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cash.accounts.map((account) => (
                      <tr key={account.account_id}>
                        <td>
                          <strong>{account.bank_name}</strong>
                          <span>{account.account_name} · {account.masked_account_number}</span>
                        </td>
                        <td>{account.entity_name}</td>
                        <td>{formatMoney(account.native_balance, account.currency)}</td>
                        <td>
                          <strong>
                            {formatMoney(account.base_currency_balance, cash.base_currency)}
                          </strong>
                        </td>
                        <td>
                          <StatusBadge status={account.freshness} />
                          <span className="timestamp">{formatTimestamp(account.balance_as_of)}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="panel history-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Data operations</p>
                  <h2>Recent imports</h2>
                </div>
                <span className="as-of">{imports.length} runs</span>
              </div>
              {imports.length === 0 ? (
                <p className="empty-state">No files imported yet. Use the CSV profile above.</p>
              ) : (
                <div className="history-list">
                  {imports.slice(0, 5).map((item) => (
                    <div className="history-row" key={item.import_run_id}>
                      <div>
                        <strong>{item.file_name}</strong>
                        <span>{formatTimestamp(item.completed_at)}</span>
                      </div>
                      <div className="history-counts">
                        <span>{item.accepted_rows} accepted</span>
                        {item.rejected_rows > 0 && <span>{item.rejected_rows} rejected</span>}
                        {item.skipped_duplicate_rows > 0 && (
                          <span>{item.skipped_duplicate_rows} skipped</span>
                        )}
                      </div>
                      <StatusBadge status={item.status} />
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        ) : null}
      </main>

      <footer>
        Demonstration workspace · Synthetic data · No bank connection or payment
        transmission
      </footer>
    </div>
  );
}
