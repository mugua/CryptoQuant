import React from 'react';
import { Segmented, Tooltip } from 'antd';
import { SunOutlined, MoonOutlined, DesktopOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../../store';
import type { ThemeMode } from '../../types';

const ThemeSwitch: React.FC = () => {
  const { t } = useTranslation();
  const themeMode = useAppStore((s) => s.themeMode);
  const setThemeMode = useAppStore((s) => s.setThemeMode);

  const options = [
    {
      value: 'light',
      icon: (
        <Tooltip title={t('userCenter.light')}>
          <SunOutlined />
        </Tooltip>
      ),
    },
    {
      value: 'dark',
      icon: (
        <Tooltip title={t('userCenter.dark')}>
          <MoonOutlined />
        </Tooltip>
      ),
    },
    {
      value: 'auto',
      icon: (
        <Tooltip title={t('userCenter.auto')}>
          <DesktopOutlined />
        </Tooltip>
      ),
    },
  ];

  return (
    <Segmented
      size="small"
      value={themeMode}
      onChange={(value) => setThemeMode(value as ThemeMode)}
      options={options}
    />
  );
};

export default ThemeSwitch;
