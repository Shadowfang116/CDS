'use client';

import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  RadialBarChart,
  RadialBar,
  ReferenceLine,
} from 'recharts';
import { TimeseriesEntry, ExceptionsBySeverity } from '@/lib/api';

// Centralized color palette for dark theme
export const chartPalette = {
  primary: '#7a856f',
  secondary: '#948167',
  tertiary: '#ab764d',
  high: '#bd5a56',
  medium: '#b8975f',
  low: '#6f8c73',
  muted: '#4a525b',
  background: '#1d2227',
  text: '#eceff2',
  textMuted: '#a7afb7',
  selected: '#f5f1e8',
};

// Status colors for bar chart
const statusColors: Record<string, string> = {
  New: '#7a856f',
  Processing: '#6e7a65',
  Review: '#b8975f',
  'Pending Docs': '#ab764d',
  'Ready for Approval': '#6f8c73',
  Approved: '#6f8c73',
  Rejected: '#bd5a56',
  Closed: '#6a737d',
};

// Severity type
export type SeverityLevel = 'High' | 'Medium' | 'Low';

// Custom tooltip component
function CustomTooltip({ active, payload, label, clickHint }: any) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-[rgba(82,90,99,0.5)] bg-[rgba(29,34,39,0.98)] px-3 py-2 shadow-[0_12px_32px_rgba(0,0,0,0.28)]">
      <p className="mb-1 text-xs text-stone-500">{label}</p>
      {payload.map((entry: any, i: number) => (
        <p key={i} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: <span className="font-semibold">{entry.value}</span>
        </p>
      ))}
      {clickHint && (
        <p className="mt-1.5 border-t border-[rgba(82,90,99,0.38)] pt-1.5 text-xs text-stone-400">
          Click to filter
        </p>
      )}
    </div>
  );
}

// Empty state component for charts
function ChartEmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-md border border-[rgba(82,90,99,0.38)] bg-[rgba(34,39,45,0.9)]">
          <svg className="h-5 w-5 text-stone-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25A1.125 1.125 0 0116.5 19.875V4.125z" />
          </svg>
        </div>
        <p className="text-sm text-stone-500">{message}</p>
      </div>
    </div>
  );
}

interface TrendLineChartProps {
  data: TimeseriesEntry[];
  loading?: boolean;
  selectedDate?: string | null;
  onSelectDate?: (date: string) => void;
}

export function TrendLineChart({ data, loading, selectedDate, onSelectDate }: TrendLineChartProps) {
  const displayData = useMemo(() => {
    return data.length > 14 ? data.slice(-14) : data;
  }, [data]);

  const hasData = useMemo(() => {
    return displayData.some(d => d.cases_created > 0 || d.exports_generated > 0);
  }, [displayData]);

  // Format date for display
  const formattedData = useMemo(() => {
    return displayData.map(d => ({
      ...d,
      displayDate: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    }));
  }, [displayData]);

  const handleClick = (e: any) => {
    if (e?.activePayload?.[0]?.payload?.date && onSelectDate) {
      onSelectDate(e.activePayload[0].payload.date);
    }
  };

  if (loading) {
    return (
      <div className="h-64 min-w-0 w-full rounded-md border border-[rgba(82,90,99,0.24)] bg-[rgba(18,22,26,0.44)] px-4 py-4">
        <div className="flex h-full animate-pulse flex-col justify-between">
          <div className="flex gap-2">
            <div className="h-3 w-20 rounded bg-[rgba(82,90,99,0.35)]" />
            <div className="h-3 w-16 rounded bg-[rgba(82,90,99,0.24)]" />
          </div>
          <div className="grid h-40 grid-cols-7 items-end gap-2">
            {Array.from({ length: 7 }).map((_, index) => (
              <div
                key={index}
                className="rounded-sm bg-[rgba(82,90,99,0.22)]"
                style={{ height: `${35 + ((index % 4) + 1) * 16}px` }}
              />
            ))}
          </div>
          <div className="flex gap-3">
            <div className="h-3 w-24 rounded bg-[rgba(82,90,99,0.28)]" />
            <div className="h-3 w-24 rounded bg-[rgba(82,90,99,0.18)]" />
          </div>
        </div>
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="h-64 min-w-0 w-full">
        <ChartEmptyState message="No activity in this range" />
      </div>
    );
  }

  return (
    <div className="h-64 min-w-0 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart 
          data={formattedData} 
          margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
          onClick={handleClick}
          style={{ cursor: onSelectDate ? 'pointer' : 'default' }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={chartPalette.muted} opacity={0.3} />
          <XAxis
            dataKey="displayDate"
            tick={{ fill: chartPalette.textMuted, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: chartPalette.muted }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: chartPalette.textMuted, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />
          <Tooltip content={<CustomTooltip clickHint={!!onSelectDate} />} />
          {selectedDate && (
            <ReferenceLine
              x={new Date(selectedDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              stroke={chartPalette.selected}
              strokeDasharray="3 3"
              strokeWidth={2}
            />
          )}
          <Line
            type="monotone"
            dataKey="cases_created"
            name="Cases Created"
            stroke={chartPalette.primary}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6, fill: chartPalette.primary, stroke: chartPalette.selected, strokeWidth: 2 }}
          />
          <Line
            type="monotone"
            dataKey="exports_generated"
            name="Exports Generated"
            stroke={chartPalette.secondary}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6, fill: chartPalette.secondary, stroke: chartPalette.selected, strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

interface SeverityDonutProps {
  data: ExceptionsBySeverity;
  loading?: boolean;
  selectedSeverity?: SeverityLevel | null;
  onSelectSeverity?: (severity: SeverityLevel) => void;
}

export function SeverityDonut({ data, loading, selectedSeverity, onSelectSeverity }: SeverityDonutProps) {
  const chartData = useMemo(() => [
    { name: 'High', value: data.high, color: chartPalette.high },
    { name: 'Medium', value: data.medium, color: chartPalette.medium },
    { name: 'Low', value: data.low, color: chartPalette.low },
  ], [data]);

  const total = data.high + data.medium + data.low;

  const handleClick = (entry: any) => {
    if (onSelectSeverity && entry?.name) {
      onSelectSeverity(entry.name as SeverityLevel);
    }
  };

  if (loading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="animate-pulse text-slate-500">Loading...</div>
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="h-48 min-w-0 w-full">
        <ChartEmptyState message="No open exceptions" />
      </div>
    );
  }

  return (
    <div className="h-48 min-w-0 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={65}
            paddingAngle={2}
            dataKey="value"
            onClick={handleClick}
            style={{ cursor: onSelectSeverity ? 'pointer' : 'default' }}
          >
            {chartData.map((entry, index) => {
              const isSelected = selectedSeverity === entry.name;
              const isOtherSelected = selectedSeverity && selectedSeverity !== entry.name;
              return (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.color}
                  opacity={isOtherSelected ? 0.3 : 1}
                  stroke={isSelected ? chartPalette.selected : 'transparent'}
                  strokeWidth={isSelected ? 2 : 0}
                />
              );
            })}
          </Pie>
          <Tooltip 
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const entry = payload[0].payload;
              return (
                <div className="rounded-lg border border-[rgba(82,90,99,0.5)] bg-[rgba(29,34,39,0.98)] px-3 py-2 shadow-[0_12px_32px_rgba(0,0,0,0.28)]">
                  <p className="text-sm" style={{ color: entry.color }}>
                    {entry.name}: <span className="font-semibold">{entry.value}</span>
                  </p>
                  {onSelectSeverity && (
                    <p className="mt-1.5 border-t border-[rgba(82,90,99,0.38)] pt-1.5 text-xs text-stone-400">
                      Click to filter
                    </p>
                  )}
                </div>
              );
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-4 -mt-2">
        {chartData.map((entry) => {
          const isSelected = selectedSeverity === entry.name;
          const isOtherSelected = selectedSeverity && selectedSeverity !== entry.name;
          return (
            <button
              key={entry.name}
              onClick={() => onSelectSeverity?.(entry.name as SeverityLevel)}
              className={`flex items-center gap-1.5 transition-opacity ${
                isOtherSelected ? 'opacity-40' : 'opacity-100'
              } ${onSelectSeverity ? 'cursor-pointer hover:opacity-80' : ''}`}
            >
              <div 
                className={`w-2.5 h-2.5 rounded-full ${isSelected ? 'ring-2 ring-white ring-offset-1 ring-offset-slate-800' : ''}`}
                style={{ backgroundColor: entry.color }} 
              />
              <span className="text-xs text-stone-400">{entry.name}: {entry.value}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface StatusBarChartProps {
  data: Record<string, number>;
  loading?: boolean;
  selectedStatus?: string | null;
  onSelectStatus?: (status: string) => void;
}

export function StatusBarChart({ data, loading, selectedStatus, onSelectStatus }: StatusBarChartProps) {
  const chartData = useMemo(() => {
    return Object.entries(data)
      .filter(([, count]) => count > 0)
      .map(([status, count]) => ({
        status,
        count,
        color: statusColors[status] || chartPalette.muted,
      }));
  }, [data]);

  const hasData = chartData.length > 0;

  const handleClick = (entry: any) => {
    if (onSelectStatus && entry?.status) {
      onSelectStatus(entry.status);
    }
  };

  if (loading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="animate-pulse text-stone-500">Loading...</div>
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="h-48 min-w-0 w-full">
        <ChartEmptyState message="No cases in this range" />
      </div>
    );
  }

  return (
    <div className="h-48 min-w-0 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart 
          data={chartData} 
          layout="vertical" 
          margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
          onClick={handleClick}
          style={{ cursor: onSelectStatus ? 'pointer' : 'default' }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={chartPalette.muted} opacity={0.3} horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: chartPalette.textMuted, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="status"
            tick={{ fill: chartPalette.textMuted, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={100}
          />
          <Tooltip 
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const entry = payload[0].payload;
              return (
                <div className="rounded-lg border border-[rgba(82,90,99,0.5)] bg-[rgba(29,34,39,0.98)] px-3 py-2 shadow-[0_12px_32px_rgba(0,0,0,0.28)]">
                  <p className="text-sm" style={{ color: entry.color }}>
                    {entry.status}: <span className="font-semibold">{entry.count}</span>
                  </p>
                  {onSelectStatus && (
                    <p className="mt-1.5 border-t border-[rgba(82,90,99,0.38)] pt-1.5 text-xs text-stone-400">
                      Click to filter
                    </p>
                  )}
                </div>
              );
            }}
          />
          <Bar dataKey="count" name="Cases" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => {
              const isSelected = selectedStatus === entry.status;
              const isOtherSelected = selectedStatus && selectedStatus !== entry.status;
              return (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.color}
                  opacity={isOtherSelected ? 0.3 : 1}
                  stroke={isSelected ? chartPalette.selected : 'transparent'}
                  strokeWidth={isSelected ? 2 : 0}
                />
              );
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

interface RadialMeterProps {
  value: number;
  label: string;
  color?: string;
  loading?: boolean;
}

export function RadialMeter({ value, label, color = chartPalette.primary, loading }: RadialMeterProps) {
  const data = [
    { name: label, value: value, fill: color },
  ];

  if (loading) {
    return (
      <div className="h-32 flex items-center justify-center">
        <div className="animate-pulse text-stone-500">...</div>
      </div>
    );
  }

  return (
    <div className="h-32 relative min-w-0 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="60%"
          outerRadius="90%"
          barSize={10}
          data={data}
          startAngle={180}
          endAngle={0}
        >
          <RadialBar
            background={{ fill: chartPalette.muted }}
            dataKey="value"
            cornerRadius={5}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-2xl font-bold text-slate-100 tabular-nums">{value}%</span>
        <span className="text-xs text-slate-400 mt-0.5">{label}</span>
      </div>
    </div>
  );
}

