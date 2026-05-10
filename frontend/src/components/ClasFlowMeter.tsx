import { Card, Group, Stack, Text } from '@mantine/core';

export interface FlowStats {
  bytes_total: number;
  blocks_total: number;
  bytes_per_sec: number;
  msg_per_sec: number;
  last_block_at: string | null;
  last_pvt_at: string | null;
}

interface ClasFlowMeterProps {
  stats: FlowStats | null;
}

const MONO = "var(--mantine-font-family-monospace)";

function formatBytes(n: number): string {
  if (n < 1024) return `${n.toFixed(0)} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KiB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(2)} MiB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GiB`;
}

function formatRate(bps: number): string {
  if (bps < 1024) return `${bps.toFixed(0)} B/s`;
  if (bps < 1024 * 1024) return `${(bps / 1024).toFixed(1)} KiB/s`;
  return `${(bps / 1024 / 1024).toFixed(2)} MiB/s`;
}

function formatRelativeAge(iso: string | null): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  const dt = (Date.now() - t) / 1000;
  if (dt < 1) return 'just now';
  if (dt < 60) return `${dt.toFixed(0)} s ago`;
  if (dt < 3600) return `${(dt / 60).toFixed(1)} min ago`;
  return `${(dt / 3600).toFixed(1)} h ago`;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap={2} style={{ minWidth: 0 }}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm" fw={600} style={{ fontFamily: MONO }}>
        {value}
      </Text>
    </Stack>
  );
}

export function ClasFlowMeter({ stats }: ClasFlowMeterProps) {
  if (!stats) {
    return (
      <Card withBorder p="sm">
        <Text size="xs" c="dimmed">
          Waiting for SBF stream…
        </Text>
      </Card>
    );
  }
  return (
    <Card withBorder p="sm">
      <Group gap="xl" wrap="wrap">
        <Stat label="Throughput" value={formatRate(stats.bytes_per_sec)} />
        <Stat label="SBF blocks/s" value={stats.msg_per_sec.toFixed(1)} />
        <Stat label="Total bytes" value={formatBytes(stats.bytes_total)} />
        <Stat label="Total blocks" value={stats.blocks_total.toString()} />
        <Stat label="Last SBF" value={formatRelativeAge(stats.last_block_at)} />
        <Stat label="Last PVT" value={formatRelativeAge(stats.last_pvt_at)} />
      </Group>
    </Card>
  );
}
