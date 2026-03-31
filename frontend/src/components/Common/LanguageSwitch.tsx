import React from 'react';
import { Dropdown, Button } from 'antd';
import { GlobalOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../../store';
import type { Language } from '../../types';
import axios from 'axios';

const languageLabels: Record<Language, string> = {
  'zh-CN': '🇨🇳 中文',
  'en-US': '🇺🇸 English',
};

const LanguageSwitch: React.FC = () => {
  const { i18n } = useTranslation();
  const language = useAppStore((s) => s.language);
  const setLanguage = useAppStore((s) => s.setLanguage);
  const isAuthenticated = useAppStore((s) => s.isAuthenticated);
  const accessToken = useAppStore((s) => s.accessToken);

  const handleChange = async (lang: Language) => {
    setLanguage(lang);
    await i18n.changeLanguage(lang);

    if (isAuthenticated && accessToken) {
      try {
        await axios.patch(
          '/api/v1/user/settings',
          { language: lang },
          { headers: { Authorization: `Bearer ${accessToken}` } }
        );
      } catch {
        // Silently ignore sync failure
      }
    }
  };

  const items = (Object.keys(languageLabels) as Language[]).map((lang) => ({
    key: lang,
    label: languageLabels[lang],
    onClick: () => handleChange(lang),
  }));

  return (
    <Dropdown menu={{ items, selectedKeys: [language] }} trigger={['click']}>
      <Button type="text" size="small" icon={<GlobalOutlined />}>
        {language === 'zh-CN' ? '中文' : 'EN'}
      </Button>
    </Dropdown>
  );
};

export default LanguageSwitch;
