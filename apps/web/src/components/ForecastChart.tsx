import { formatMoney } from "../format";
import type { ForecastPoint } from "../types";

type ForecastChartProps = {
  points: ForecastPoint[];
  currency: string;
};

const WIDTH = 760;
const HEIGHT = 230;
const PADDING_X = 18;
const PADDING_Y = 24;

export function ForecastChart({ points, currency }: ForecastChartProps) {
  const values = points.map((point) => Number(point.total_cash));
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const spread = Math.max(maximum - minimum, 1);
  const drawableWidth = WIDTH - PADDING_X * 2;
  const drawableHeight = HEIGHT - PADDING_Y * 2;
  const coordinates = points.map((point, index) => {
    const x = PADDING_X + (index / Math.max(points.length - 1, 1)) * drawableWidth;
    const y = PADDING_Y + ((maximum - Number(point.total_cash)) / spread) * drawableHeight;
    return { x, y, point };
  });
  const line = coordinates.map(({ x, y }) => `${x},${y}`).join(" ");
  const area = [
    `${PADDING_X},${HEIGHT - PADDING_Y}`,
    line,
    `${WIDTH - PADDING_X},${HEIGHT - PADDING_Y}`,
  ].join(" ");
  const markers = [0, 30, 60, 90].map((day) => coordinates[day]).filter(Boolean);

  return (
    <div className="forecast-chart">
      <div className="chart-scale" aria-hidden="true">
        <span>{formatMoney(String(maximum), currency)}</span>
        <span>{formatMoney(String(minimum), currency)}</span>
      </div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Projected total cash over 90 days"
      >
        <defs>
          <linearGradient id="forecast-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2c9874" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#2c9874" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <line
          x1={PADDING_X}
          y1={HEIGHT - PADDING_Y}
          x2={WIDTH - PADDING_X}
          y2={HEIGHT - PADDING_Y}
          className="chart-axis"
        />
        <polygon points={area} fill="url(#forecast-area)" />
        <polyline points={line} className="chart-line" />
        {markers.map(({ x, y, point }, index) => (
          <g key={point.date}>
            <circle cx={x} cy={y} r="5" className="chart-marker" />
            <text x={x} y={HEIGHT - 4} textAnchor="middle" className="chart-label">
              {index === 0 ? "Today" : `${index * 30}d`}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
