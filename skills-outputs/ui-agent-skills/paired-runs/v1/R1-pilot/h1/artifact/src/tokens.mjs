export const TOKENS = Object.freeze({
  color: {
    surface: '#FFFFFF',
    text: '#1A1A1A',
    muted: '#5B6472',
    primary: '#1F5EFF',
    onPrimary: '#FFFFFF',
    danger: '#B42318',
    border: '#D0D5DD'
  },
  contrastPairs: [
    ['text', 'surface'],
    ['muted', 'surface'],
    ['primary', 'surface'],
    ['onPrimary', 'primary'],
    ['danger', 'surface']
  ],
  contrastThreshold: 4.5,
  space: [4, 8, 12, 20, 32],
  radius: { control: 8, card: 14 },
  font: { body: '15px/1.55', label: '13px/600' },
  motion: { state: '120ms ease-out' }
});

function channel(value) {
  const c = value / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(hex) {
  const raw = hex.replace('#', '');
  const r = Number.parseInt(raw.slice(0, 2), 16);
  const g = Number.parseInt(raw.slice(2, 4), 16);
  const b = Number.parseInt(raw.slice(4, 6), 16);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

export function contrastRatio(foreground, background) {
  const a = relativeLuminance(foreground);
  const b = relativeLuminance(background);
  const light = Math.max(a, b);
  const dark = Math.min(a, b);
  return (light + 0.05) / (dark + 0.05);
}
