import type { PosEpoch, PosFileData, ReferencePosition } from './types';

/**
 * Parse the "% ref pos" line from a .pos file header.
 * Example: "% ref pos   : 35.326680366  139.466069646    46.4279"
 */
function parseHeaderRefPos(headerLines: string[]): ReferencePosition | null {
  for (const line of headerLines) {
    const match = line.match(/^%\s*ref\s+pos\s*:\s*([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)/);
    if (match) {
      const lat = parseFloat(match[1]);
      const lon = parseFloat(match[2]);
      const height = parseFloat(match[3]);
      if (!isNaN(lat) && !isNaN(lon) && !isNaN(height)) {
        return { lat, lon, height };
      }
    }
  }
  return null;
}

/**
 * Parse RTKLIB .pos file content into structured data.
 *
 * Expected format (space-separated, header lines start with '%'):
 *   %  GPST          latitude(deg)  longitude(deg)  height(m)  Q  ns  sdn  sde  sdu  sdne  sdeu  sdun  age  ratio
 *   2024/01/15 00:00:00.000   35.12345678  139.12345678   45.1234   1  12  0.0012  0.0010  0.0025  0.0001  -0.0003  0.0002  0.00  999.9
 */
export function parsePosFile(content: string): PosFileData {
  const lines = content.split('\n');
  const headerLines: string[] = [];
  const epochs: PosEpoch[] = [];

  for (const line of lines) {
    // Collect header lines
    if (line.startsWith('%')) {
      headerLines.push(line);
      continue;
    }

    if (line.trim() === '') continue;

    const parts = line.trim().split(/\s+/);
    // Need at least 7 fields
    if (parts.length < 7) continue;

    let time: Date;
    let dataOffset: number; // index where lat starts

    // Detect time format:
    // Format A: "YYYY/MM/DD HH:MM:SS.sss" (2 fields for time)
    // Format B: "WEEK TOW.sss" (2 fields for time, week is integer)
    if (parts[0].includes('/')) {
      // Format A: calendar date+time
      const dateStr = parts[0];
      const timeStr = parts[1];
      time = new Date(`${dateStr.replace(/\//g, '-')}T${timeStr}Z`);
      dataOffset = 2;
    } else {
      // Format B: GPS Week + ToW
      const week = parseInt(parts[0], 10);
      const tow = parseFloat(parts[1]);
      if (isNaN(week) || isNaN(tow)) continue;
      // GPS epoch: 1980-01-06T00:00:00Z
      const GPS_EPOCH_MS = Date.UTC(1980, 0, 6);
      // Approximate: assume current leap seconds (18s offset GPS→UTC)
      const utcMs = GPS_EPOCH_MS + (week * 604800 + tow - 18) * 1000;
      time = new Date(utcMs);
      dataOffset = 2;
    }

    if (isNaN(time.getTime())) continue;

    const lat = parseFloat(parts[dataOffset]);
    const lon = parseFloat(parts[dataOffset + 1]);
    const height = parseFloat(parts[dataOffset + 2]);

    // Skip rows with NaN coordinates
    if (isNaN(lat) || isNaN(lon) || isNaN(height)) continue;

    const qi = dataOffset + 3;
    epochs.push({
      time,
      timeUnix: time.getTime() / 1000,
      lat,
      lon,
      height,
      Q: parseInt(parts[qi], 10) || 0,
      ns: parseInt(parts[qi + 1], 10) || 0,
      sdn: parts.length > qi + 2 ? parseFloat(parts[qi + 2]) || 0 : 0,
      sde: parts.length > qi + 3 ? parseFloat(parts[qi + 3]) || 0 : 0,
      sdu: parts.length > qi + 4 ? parseFloat(parts[qi + 4]) || 0 : 0,
      // parts[qi+5..qi+7] are sdne, sdeu, sdun — skipped
      age: parts.length > qi + 8 ? parseFloat(parts[qi + 8]) || 0 : 0,
      ratio: parts.length > qi + 9 ? parseFloat(parts[qi + 9]) || 0 : 0,
    });
  }

  return {
    epochs,
    headerRefPos: parseHeaderRefPos(headerLines),
  };
}
