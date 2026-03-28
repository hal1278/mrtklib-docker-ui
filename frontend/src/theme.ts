import { createTheme } from '@mantine/core';
import type { MantineColorsTuple, CSSVariablesResolver } from '@mantine/core';

const blue: MantineColorsTuple = [
  '#e6f0ff', '#bdd4fc', '#90b8f8', '#5e9af4',
  '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af',
  '#1e3a8a', '#172554',
];

// Blue-tinted dark ramp replacing Mantine's default gray-dark palette.
const dark: MantineColorsTuple = [
  '#c8cae0',  // [0] text primary
  '#a8aac8',  // [1] text secondary
  '#8890b0',  // [2] text muted
  '#4a4d6e',  // [3] border strong
  '#32344e',  // [4] border default
  '#272840',  // [5] border subtle / input bg
  '#1a1b2e',  // [6] Paper / Card bg
  '#13141f',  // [7] body bg
  '#0e0f18',  // [8] deeper bg
  '#090a12',  // [9] deepest bg
];

export const theme = createTheme({
  fontFamily: "'IBM Plex Sans', sans-serif",
  fontFamilyMonospace: "'IBM Plex Mono', monospace",
  headings: {
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontWeight: '500',
  },
  primaryColor: 'blue',
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
    '--mantine-color-body': '#f8f9fc',
    '--mantine-color-default': '#ffffff',
    '--mantine-color-default-hover': '#f1f4f9',
    '--app-surface': '#ffffff',
    '--app-card': '#ffffff',
    '--app-border': 'rgba(0, 0, 0, 0.08)',
  },
  dark: {
    '--mantine-color-body': '#13141f',
    '--mantine-color-default': '#1a1b2e',
    '--mantine-color-default-hover': '#252640',
    '--app-surface': '#1a1b2e',
    '--app-card': '#20213a',
    '--app-border': 'rgba(255, 255, 255, 0.07)',
  },
});
