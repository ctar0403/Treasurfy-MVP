type StatusBadgeProps = {
  status: string;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const readable = status.replaceAll("_", " ");
  return <span className={`status status--${status}`}>{readable}</span>;
}
