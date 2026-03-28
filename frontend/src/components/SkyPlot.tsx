/**
 * Sky plot (polar view) showing satellite positions.
 * Renders azimuth/elevation as dots on a polar chart.
 *
 * Note: Satellite azimuth/elevation data will come from Phase E+
 * when we parse the `satellite` command output. For now, this is a
 * placeholder that can accept satellite data.
 */

import { useMantineColorScheme, Text } from '@mantine/core';

export interface SatelliteInfo {
  prn: string;         // e.g. "G01", "E05", "J02"
  azimuth: number;     // degrees (0-360, 0=North)
  elevation: number;   // degrees (0-90)
  snr: number;         // dBHz
  used: boolean;       // used in solution
  system: 'GPS' | 'GLONASS' | 'Galileo' | 'QZSS' | 'BeiDou' | 'SBAS' | 'NavIC';
}

const SYSTEM_COLORS: Record<string, string> = {
  GPS: '#fa5252',
  GLONASS: '#339af0',
  Galileo: '#fab005',
  QZSS: '#40c057',
  BeiDou: '#e64980',
  SBAS: '#868e96',
  NavIC: '#7950f2',
};

interface SkyPlotProps {
  satellites: SatelliteInfo[];
  size?: number;
}

export function SkyPlot({ satellites, size = 250 }: SkyPlotProps) {
  const { colorScheme } = useMantineColorScheme();
  const isDark = colorScheme === 'dark';

  const cx = size / 2;
  const cy = size / 2;
  const radius = (size - 40) / 2; // margin for labels

  // Convert az/el to x,y on polar chart
  // elevation 90° = center, 0° = edge
  const toXY = (az: number, el: number) => {
    const r = radius * (1 - el / 90);
    const rad = (az - 90) * Math.PI / 180; // rotate so 0°=North (top)
    return {
      x: cx + r * Math.cos(rad),
      y: cy + r * Math.sin(rad),
    };
  };

  const gridColor = isDark ? '#555' : '#ccc';
  const textColor = isDark ? '#aaa' : '#666';

  if (satellites.length === 0) {
    return (
      <Text size="sm" c="dimmed" ta="center" py="md">
        No satellite data available
      </Text>
    );
  }

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Background */}
      <circle cx={cx} cy={cy} r={radius} fill="none" stroke={gridColor} strokeWidth={1} />

      {/* Elevation rings: 0, 30, 60 */}
      {[30, 60].map(el => (
        <circle
          key={el}
          cx={cx}
          cy={cy}
          r={radius * (1 - el / 90)}
          fill="none"
          stroke={gridColor}
          strokeWidth={0.5}
          strokeDasharray="4 4"
        />
      ))}

      {/* Azimuth lines: N, E, S, W */}
      {[0, 90, 180, 270].map(az => {
        const end = toXY(az, 0);
        return (
          <line
            key={az}
            x1={cx}
            y1={cy}
            x2={end.x}
            y2={end.y}
            stroke={gridColor}
            strokeWidth={0.5}
          />
        );
      })}

      {/* Cardinal labels */}
      <text x={cx} y={8} textAnchor="middle" fontSize={10} fill={textColor}>N</text>
      <text x={size - 5} y={cy + 4} textAnchor="end" fontSize={10} fill={textColor}>E</text>
      <text x={cx} y={size - 3} textAnchor="middle" fontSize={10} fill={textColor}>S</text>
      <text x={8} y={cy + 4} textAnchor="start" fontSize={10} fill={textColor}>W</text>

      {/* Elevation labels */}
      <text x={cx + 3} y={cy - radius * (1 - 30 / 90) + 3} fontSize={8} fill={textColor}>30°</text>
      <text x={cx + 3} y={cy - radius * (1 - 60 / 90) + 3} fontSize={8} fill={textColor}>60°</text>

      {/* Satellite dots */}
      {satellites.map((sat, i) => {
        const { x, y } = toXY(sat.azimuth, sat.elevation);
        const color = SYSTEM_COLORS[sat.system] || '#868e96';
        return (
          <g key={`${sat.prn}-${i}`}>
            <circle
              cx={x}
              cy={y}
              r={sat.used ? 5 : 3}
              fill={sat.used ? color : 'none'}
              stroke={color}
              strokeWidth={1}
              opacity={sat.used ? 0.9 : 0.5}
            />
            <text
              x={x}
              y={y - 7}
              textAnchor="middle"
              fontSize={7}
              fill={color}
              fontWeight={sat.used ? 600 : 400}
            >
              {sat.prn}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
