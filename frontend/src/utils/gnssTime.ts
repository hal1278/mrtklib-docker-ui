/**
 * GNSS time conversion utilities.
 * Pure functions — no external dependencies.
 */

const GPS_EPOCH = new Date('1980-01-06T00:00:00Z');
const GPS_EPOCH_MS = GPS_EPOCH.getTime();
const SECS_PER_WEEK = 604800;

const LEAP_SECONDS: { utc: Date; leapSeconds: number }[] = [
  { utc: new Date('1980-01-06T00:00:00Z'), leapSeconds: 19 },
  { utc: new Date('1981-07-01T00:00:00Z'), leapSeconds: 20 },
  { utc: new Date('1982-07-01T00:00:00Z'), leapSeconds: 21 },
  { utc: new Date('1983-07-01T00:00:00Z'), leapSeconds: 22 },
  { utc: new Date('1985-07-01T00:00:00Z'), leapSeconds: 23 },
  { utc: new Date('1988-01-01T00:00:00Z'), leapSeconds: 24 },
  { utc: new Date('1990-01-01T00:00:00Z'), leapSeconds: 25 },
  { utc: new Date('1991-01-01T00:00:00Z'), leapSeconds: 26 },
  { utc: new Date('1992-07-01T00:00:00Z'), leapSeconds: 27 },
  { utc: new Date('1993-07-01T00:00:00Z'), leapSeconds: 28 },
  { utc: new Date('1994-07-01T00:00:00Z'), leapSeconds: 29 },
  { utc: new Date('1996-01-01T00:00:00Z'), leapSeconds: 30 },
  { utc: new Date('1997-07-01T00:00:00Z'), leapSeconds: 31 },
  { utc: new Date('1999-01-01T00:00:00Z'), leapSeconds: 32 },
  { utc: new Date('2006-01-01T00:00:00Z'), leapSeconds: 33 },
  { utc: new Date('2009-01-01T00:00:00Z'), leapSeconds: 34 },
  { utc: new Date('2012-07-01T00:00:00Z'), leapSeconds: 35 },
  { utc: new Date('2015-07-01T00:00:00Z'), leapSeconds: 36 },
  { utc: new Date('2017-01-01T00:00:00Z'), leapSeconds: 37 },
];

/** Get the number of leap seconds in effect for a given UTC date. */
export function getLeapSeconds(utc: Date): number {
  let ls = 19;
  for (const entry of LEAP_SECONDS) {
    if (utc >= entry.utc) ls = entry.leapSeconds;
    else break;
  }
  return ls;
}

/** Convert UTC date to GPS Week and Time of Week (seconds). */
export function utcToGps(utc: Date): { week: number; tow: number } {
  const ls = getLeapSeconds(utc);
  const gpsSeconds = (utc.getTime() - GPS_EPOCH_MS) / 1000 + (ls - 19);
  const week = Math.floor(gpsSeconds / SECS_PER_WEEK);
  const tow = gpsSeconds - week * SECS_PER_WEEK;
  return { week, tow };
}

/** Convert GPS Week and Time of Week to UTC date. */
export function gpsToUtc(week: number, tow: number): Date {
  // Iterative: guess UTC, check leap seconds, adjust
  const gpsSeconds = week * SECS_PER_WEEK + tow;
  let utcMs = GPS_EPOCH_MS + (gpsSeconds + 19 - 19) * 1000; // initial guess without leap offset
  // First pass: get leap seconds for this approximate UTC
  let ls = getLeapSeconds(new Date(utcMs));
  utcMs = GPS_EPOCH_MS + (gpsSeconds - (ls - 19)) * 1000;
  // Second pass: refine if leap second boundary crossed
  const ls2 = getLeapSeconds(new Date(utcMs));
  if (ls2 !== ls) {
    utcMs = GPS_EPOCH_MS + (gpsSeconds - (ls2 - 19)) * 1000;
  }
  return new Date(utcMs);
}

/** Convert UTC date to Year, Day of Year (1-indexed), and Hour. */
export function utcToDoy(utc: Date): { year: number; doy: number; hour: number } {
  const year = utc.getUTCFullYear();
  const janFirst = new Date(Date.UTC(year, 0, 1));
  const doy = Math.floor((utc.getTime() - janFirst.getTime()) / 86400000) + 1;
  const hour = utc.getUTCHours();
  return { year, doy, hour };
}

/** Convert Year, Day of Year, and Hour to UTC date. */
export function doyToUtc(year: number, doy: number, hour: number): Date {
  const janFirst = new Date(Date.UTC(year, 0, 1));
  return new Date(janFirst.getTime() + (doy - 1) * 86400000 + hour * 3600000);
}

/** Convert hour (0-23) to RINEX session letter ('a'-'x'). */
export function hourToSession(hour: number): string {
  return String.fromCharCode(97 + Math.max(0, Math.min(23, hour)));
}

/** Get the maximum day-of-year for a given year. */
export function maxDoy(year: number): number {
  const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  return isLeap ? 366 : 365;
}

/** Convert UTC date to GPS Time date (UTC + leap offset). */
export function utcToGpsTime(utc: Date): Date {
  const ls = getLeapSeconds(utc);
  return new Date(utc.getTime() + (ls - 19) * 1000);
}

/** Convert GPS Time date back to UTC date. */
export function gpsTimeToUtc(gpsTime: Date): Date {
  // Approximate: use GPS time to estimate UTC, then refine
  const approxUtc = new Date(gpsTime.getTime() - 18 * 1000); // rough guess
  const ls = getLeapSeconds(approxUtc);
  return new Date(gpsTime.getTime() - (ls - 19) * 1000);
}

/** GPS Week/ToW directly from GPS Time (no leap second needed). */
export function gpsTimeToWeekTow(gpsTime: Date): { week: number; tow: number } {
  const gpsSeconds = (gpsTime.getTime() - GPS_EPOCH_MS) / 1000;
  const week = Math.floor(gpsSeconds / SECS_PER_WEEK);
  const tow = gpsSeconds - week * SECS_PER_WEEK;
  return { week, tow };
}

/** GPS Week/ToW to GPS Time date. */
export function weekTowToGpsTime(week: number, tow: number): Date {
  return new Date(GPS_EPOCH_MS + (week * SECS_PER_WEEK + tow) * 1000);
}

/** DoY from GPS Time (using GPS Time calendar, not UTC). */
export function gpsTimeToDoy(gpsTime: Date): { year: number; doy: number; hour: number } {
  const year = gpsTime.getUTCFullYear();
  const janFirst = new Date(Date.UTC(year, 0, 1));
  const doy = Math.floor((gpsTime.getTime() - janFirst.getTime()) / 86400000) + 1;
  const hour = gpsTime.getUTCHours();
  return { year, doy, hour };
}

/** DoY to GPS Time date. */
export function doyToGpsTime(year: number, doy: number, hour: number): Date {
  const janFirst = new Date(Date.UTC(year, 0, 1));
  return new Date(janFirst.getTime() + (doy - 1) * 86400000 + hour * 3600000);
}
