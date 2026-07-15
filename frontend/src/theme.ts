import { createTheme } from '@mantine/core';
import type { MantineColorsTuple, CSSVariablesResolver } from '@mantine/core';

// ── "A — Carbon / Azure" palette ───────────────────────────────────────────
// Drop-in replacement for frontend/src/theme.ts.
// Dark = near-black neutral graphite; Light = white pair. Accent = azure blue.
// Status colors (FIX green / FLOAT amber / ERROR red) live in index.css.

// Azure primary ramp. primaryShade picks [4] in dark (#4C8DFF) and [6] in light (#2563EB).
const blue: MantineColorsTuple = [
  '#E8F1FF', '#CFE0FF', '#9DBDFF', '#6A9BFF',
  '#4C8DFF', '#2F7BFF', '#2563EB', '#1D4ED8',
  '#1B46C2', '#173A9E',
];

// Neutral near-black dark ramp (NOT blue-tinted). Index roles preserved from the
// original theme so existing `dark.N` references keep their meaning.
const dark: MantineColorsTuple = [
  '#ECEEF1', // [0] text primary
  '#C7CCD2', // [1] text secondary
  '#9CA3AB', // [2] text muted
  '#2D333B', // [3] border strong
  '#262B32', // [4] border default
  '#1B1F24', // [5] border subtle / input bg
  '#13161A', // [6] Paper / Card bg
  '#0F1217', // [7] body bg
  '#0C0E12', // [8] deeper bg
  '#0A0C0F', // [9] deepest bg
];

export const theme = createTheme({
  fontFamily: "'IBM Plex Sans', sans-serif",
  fontFamilyMonospace: "'IBM Plex Mono', monospace",
  headings: {
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontWeight: '500',
  },
  primaryColor: 'blue',
  primaryShade: { light: 6, dark: 4 },
  colors: { blue, dark },
  defaultRadius: 'md',
  components: {
    Button: { defaultProps: { radius: 'md' } },
    Paper: { defaultProps: { radius: 'md', withBorder: true } },
    Card: { defaultProps: { radius: 'md', withBorder: true } },
    Code: { styles: { root: { fontFamily: "'IBM Plex Mono', monospace" } } },
  },
});

export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {},
  light: {
    '--mantine-color-body': '#F4F6F8',
    '--mantine-color-default': '#FFFFFF',
    '--mantine-color-default-hover': '#EDF0F3',
    '--app-surface': '#FFFFFF',
    '--app-card': '#FFFFFF',
    '--app-border': 'rgba(0, 0, 0, 0.08)',
  },
  dark: {
    '--mantine-color-body': '#0F1217',
    '--mantine-color-default': '#13161A',
    '--mantine-color-default-hover': '#1B1F24',
    '--app-surface': '#13161A',
    '--app-card': '#161A1F',
    '--app-border': 'rgba(255, 255, 255, 0.07)',
  },
});
