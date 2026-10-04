import { useMemo, useState } from "react";
import {
  decidePayment,
  downloadPaymentXml,
  getPaymentAudit,
  preparePayment,
  submitPayment,
} from "../api";
import { formatDate, formatMoney, formatTimestamp } from "../format";
import type {
  AccountCash,
  Payment,
  PaymentAuditEvent,
  PaymentCreateInput,
  PaymentProfile,
} from "../types";
import { StatusBadge } from "./StatusBadge";

type PaymentPanelProps = {
  accounts: AccountCash[];
  profiles: PaymentProfile[];
  payments: Payment[];
  onPaymentsChanged: () => Promise<void>;
};

function defaultExecutionDate(): string {
  const value = new Date();
  value.setUTCDate(value.getUTCDate() + 2);
  return value.toISOString().slice(0, 10);
}

export function PaymentPanel({
  accounts,
  profiles,
  payments,
  onPaymentsChanged,
}: PaymentPanelProps) {
  const [sourceAccountId, setSourceAccountId] = useState(accounts[0]?.account_id ?? "");
  const [beneficiaryName, setBeneficiaryName] = useState("");
  const [beneficiaryAccount, setBeneficiaryAccount] = useState("");
  const [beneficiaryCountry, setBeneficiaryCountry] = useState("");
  const [amount, setAmount] = useState("");
  const [executionDate, setExecutionDate] = useState(defaultExecutionDate);
  const [reference, setReference] = useState("");
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [auditByPayment, setAuditByPayment] = useState<Record<string, PaymentAuditEvent[]>>({});
  const [expandedAudit, setExpandedAudit] = useState<string | null>(null);

  const selectedAccount = useMemo(
    () => accounts.find((account) => account.account_id === sourceAccountId) ?? accounts[0],
    [accounts, sourceAccountId],
  );
  const profile = profiles[0];

  async function handlePrepare(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedAccount || !profile) return;
    setPreparing(true);
    setLocalError(null);
    setMessage(null);
    const input: PaymentCreateInput = {
      entity_id: selectedAccount.entity_id,
      source_account_id: selectedAccount.account_id,
      payment_profile_id: profile.id,
      beneficiary_name: beneficiaryName,
      beneficiary_account: beneficiaryAccount,
      beneficiary_country_code: beneficiaryCountry,
      amount,
      currency: selectedAccount.currency,
      requested_execution_date: executionDate,
      reference,
    };
    try {
      const payment = await preparePayment(input);
      setMessage(
        payment.validation_status === "passed"
          ? "Draft prepared and profile validation passed."
          : "Draft saved with validation issues.",
      );
      setBeneficiaryName("");
      setBeneficiaryAccount("");
      setBeneficiaryCountry("");
      setAmount("");
      setReference("");
      await onPaymentsChanged();
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Unable to prepare payment.");
    } finally {
      setPreparing(false);
    }
  }

  async function runAction(payment: Payment, action: "submit" | "approve" | "reject" | "export") {
    setWorkingId(payment.id);
    setLocalError(null);
    setMessage(null);
    try {
      if (action === "submit") {
        await submitPayment(payment.id);
        setMessage("Payment submitted to a separate checker.");
      } else if (action === "approve") {
        await decidePayment(payment.id, "approve", "Payment details verified in the MVP.");
        setMessage("Payment approved by the demo checker.");
      } else if (action === "reject") {
        await decidePayment(payment.id, "reject", "Returned to the maker for review.");
        setMessage("Payment returned to the maker.");
      } else {
        await downloadPaymentXml(payment.id);
        setMessage("Illustrative pain.001 XML downloaded.");
      }
      await onPaymentsChanged();
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Payment action failed.");
    } finally {
      setWorkingId(null);
    }
  }

  async function toggleAudit(paymentId: string) {
    if (expandedAudit === paymentId) {
      setExpandedAudit(null);
      return;
    }
    setLocalError(null);
    try {
      const events = auditByPayment[paymentId] ?? (await getPaymentAudit(paymentId));
      setAuditByPayment((current) => ({ ...current, [paymentId]: events }));
      setExpandedAudit(paymentId);
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Unable to load audit history.");
    }
  }

  return (
    <section id="payments" className="payments-section" aria-labelledby="payments-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Controlled execution</p>
          <h2 id="payments-title">Payment workspace</h2>
          <p>Prepare, validate, approve, and export. No payment is transmitted.</p>
        </div>
        {profile && (
          <span className="profile-tag">
            {profile.message_type} / v{profile.version}
          </span>
        )}
      </div>

      {(localError || message) && (
        <div className={`message ${localError ? "message--error" : "message--success"}`} role="status">
          <strong>{localError ? "Payment action needs attention." : "Payment workflow updated."}</strong>
          <span>{localError ?? message}</span>
        </div>
      )}

      <div className="payment-layout">
        <article className="panel payment-form-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Maker</p>
              <h3>Prepare a payment</h3>
            </div>
            <span className="role-pill">Priya / preparer</span>
          </div>
          <form className="payment-form" onSubmit={(event) => void handlePrepare(event)}>
            <label>
              Source account
              <select
                value={sourceAccountId}
                onChange={(event) => setSourceAccountId(event.target.value)}
                required
              >
                {accounts.map((account) => (
                  <option key={account.account_id} value={account.account_id}>
                    {account.entity_name} / {account.account_name} / {account.currency}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Beneficiary name
              <input
                value={beneficiaryName}
                onChange={(event) => setBeneficiaryName(event.target.value)}
                placeholder="Supplier legal name"
                required
              />
            </label>
            <label>
              Beneficiary account or IBAN
              <input
                value={beneficiaryAccount}
                onChange={(event) => setBeneficiaryAccount(event.target.value)}
                placeholder="DE89370400440532013000"
                required
              />
            </label>
            <div className="form-row">
              <label>
                Country
                <input
                  value={beneficiaryCountry}
                  onChange={(event) => setBeneficiaryCountry(event.target.value.toUpperCase())}
                  maxLength={2}
                  placeholder="DE"
                  required
                />
              </label>
              <label>
                Amount {selectedAccount ? `(${selectedAccount.currency})` : ""}
                <input
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="0.00"
                  required
                />
              </label>
            </div>
            <div className="form-row">
              <label>
                Execution date
                <input
                  value={executionDate}
                  onChange={(event) => setExecutionDate(event.target.value)}
                  type="date"
                  required
                />
              </label>
              <label>
                Payment reference
                <input
                  value={reference}
                  onChange={(event) => setReference(event.target.value)}
                  placeholder="Invoice number"
                  required
                />
              </label>
            </div>
            <button className="primary-button" disabled={preparing || !profile || !selectedAccount}>
              {preparing ? "Validating..." : "Validate and save draft"}
            </button>
          </form>
        </article>

        <article className="panel payment-queue-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Maker / checker queue</p>
              <h3>Payments and approvals</h3>
            </div>
            <span className="as-of">{payments.length} payments</span>
          </div>
          <div className="payment-list">
            {payments.length === 0 ? (
              <p className="empty-state">No payments prepared yet.</p>
            ) : (
              payments.map((payment) => (
                <div className="payment-card" key={payment.id}>
                  <div className="payment-card-main">
                    <div>
                      <strong>{payment.beneficiary_name}</strong>
                      <span>{payment.entity_name} / {payment.reference}</span>
                    </div>
                    <strong>{formatMoney(payment.amount, payment.currency)}</strong>
                  </div>
                  <div className="payment-meta">
                    <StatusBadge status={payment.status} />
                    <StatusBadge status={`validation_${payment.validation_status}`} />
                    <span>Execute {formatDate(payment.requested_execution_date)}</span>
                    <span>Profile v{payment.profile_version}</span>
                  </div>
                  {payment.validation_errors.length > 0 && (
                    <ul className="validation-list">
                      {payment.validation_errors.map((error) => <li key={error}>{error}</li>)}
                    </ul>
                  )}
                  <div className="payment-actions">
                    {(payment.status === "draft" || payment.status === "rejected") && (
                      <button
                        className="primary-button primary-button--compact"
                        disabled={workingId === payment.id || payment.validation_status === "failed"}
                        onClick={() => void runAction(payment, "submit")}
                      >
                        Submit for approval
                      </button>
                    )}
                    {payment.status === "pending_approval" && (
                      <>
                        <button
                          className="primary-button primary-button--compact"
                          disabled={workingId === payment.id}
                          onClick={() => void runAction(payment, "approve")}
                        >
                          Approve as checker
                        </button>
                        <button
                          className="text-button text-button--danger"
                          disabled={workingId === payment.id}
                          onClick={() => void runAction(payment, "reject")}
                        >
                          Reject
                        </button>
                      </>
                    )}
                    {payment.can_export && (
                      <button
                        className="primary-button primary-button--compact"
                        disabled={workingId === payment.id}
                        onClick={() => void runAction(payment, "export")}
                      >
                        Download XML
                      </button>
                    )}
                    <button className="text-button" onClick={() => void toggleAudit(payment.id)}>
                      {expandedAudit === payment.id ? "Hide audit" : "View audit"}
                    </button>
                  </div>
                  {expandedAudit === payment.id && (
                    <div className="audit-list">
                      {(auditByPayment[payment.id] ?? []).map((event) => (
                        <div key={event.id}>
                          <span className="audit-dot" aria-hidden="true" />
                          <div>
                            <strong>{event.action.replaceAll(".", " / ")}</strong>
                            <span>{event.actor_name} / {formatTimestamp(event.created_at)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
          <p className="payment-disclaimer">
            Export is an illustrative ISO 20022 pain.001 file. It is not bank-certified and is never transmitted.
          </p>
        </article>
      </div>
    </section>
  );
}
