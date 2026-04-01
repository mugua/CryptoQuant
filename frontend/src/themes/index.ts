import { lightTheme, lightThemeTokens } from './lightTheme';
import { darkTheme, darkThemeTokens } from './darkTheme';

export { lightTheme, lightThemeTokens, darkTheme, darkThemeTokens };

export function getThemeConfig(resolvedTheme: 'light' | 'dark') {
  return resolvedTheme === 'dark' ? darkTheme : lightTheme;
}

export function getThemeTokens(resolvedTheme: 'light' | 'dark') {
  return resolvedTheme === 'dark' ? darkThemeTokens : lightThemeTokens;
}

export function getChartTheme(resolvedTheme: 'light' | 'dark') {
  const t = getThemeTokens(resolvedTheme);
  return {
    background: t.chartBgColor,
    textColor: t.colorText,
    gridColor: t.chartGridColor,
    crosshairColor: t.chartCrosshairColor,
    upColor: t.chartUpColor,
    downColor: t.chartDownColor,
    wickUpColor: t.chartUpColor,
    wickDownColor: t.chartDownColor,
  };
}
