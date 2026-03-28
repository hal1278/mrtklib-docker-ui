/**
 * Time series chart for quality, satellite count, and AR ratio.
 */

import { useMemo } from 'react';
import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, Area, ComposedChart,
} from 'recharts';
import { Text, useMantineColorScheme } from '@mantine/core';

export interface TimeSeriesPoint {
  timestamp: string;
  quality: number;
  ns: number;
  ratio: number;
}

interface TimeSeriesChartProps {
  points: TimeSeriesPoint[];
  maxPoints?: number;
}

export function TimeSeriesChart({ points, maxPoints = 300 }: TimeSeriesChartProps) {
  const { colorScheme } = useMantineColorScheme();
  const isDark = colorScheme === 'dark';

  const data = useMemo(() => {
    const recent = points.slice(-maxPoints);
    return recent.map((p, i) => ({
      idx: i,
      time: p.timestamp.split(' ').pop()?.slice(0, 8) || '',
      quality: p.quality,
      ns: p.ns,
      ratio: Math.min(p.ratio, 100), // cap ratio display at 100
    }));
  }, [points, maxPoints]);

  if (data.length === 0) {
    return (
      <Text size="sm" c="dimmed" ta="center" py="md">
        No data yet
      </Text>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <ComposedChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#555' : '#ddd'} />
        <XAxis
          dataKey="time"
          tick={{ fontSize: 9 }}
          interval="preserveStartEnd"
        />
        <YAxis
          yAxisId="left"
          tick={{ fontSize: 9 }}
          domain={[0, 'auto']}
          label={{ value: 'Q / NS', angle: -90, position: 'insideLeft', fontSize: 9 }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tick={{ fontSize: 9 }}
          domain={[0, 'auto']}
          label={{ value: 'Ratio', angle: 90, position: 'insideRight', fontSize: 9 }}
        />
        <Tooltip
          contentStyle={{
            fontSize: '10px',
            backgroundColor: isDark ? '#2c2e33' : '#fff',
            border: `1px solid ${isDark ? '#555' : '#ddd'}`,
          }}
        />
        <Legend wrapperStyle={{ fontSize: '10px' }} />
        <Line
          yAxisId="left"
          type="stepAfter"
          dataKey="quality"
          name="Quality"
          stroke="#fa5252"
          dot={false}
          strokeWidth={1.5}
          isAnimationActive={false}
        />
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="ns"
          name="Satellites"
          stroke="#40c057"
          dot={false}
          strokeWidth={1.5}
          isAnimationActive={false}
        />
        <Area
          yAxisId="right"
          type="monotone"
          dataKey="ratio"
          name="AR Ratio"
          stroke="#339af0"
          fill="#339af0"
          fillOpacity={0.1}
          strokeWidth={1}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
