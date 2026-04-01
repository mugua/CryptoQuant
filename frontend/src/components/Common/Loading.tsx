import React from 'react';
import { Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

interface LoadingProps {
  fullPage?: boolean;
  tip?: string;
}

const Loading: React.FC<LoadingProps> = ({ fullPage = false, tip }) => {
  if (!fullPage) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 48 }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} tip={tip} />
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 9999,
        background: 'inherit',
      }}
    >
      <div
        style={{
          fontSize: 28,
          fontWeight: 700,
          marginBottom: 24,
          background: 'linear-gradient(135deg, #42a5f5 0%, #7c4dff 50%, #26a69a 100%)',
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          userSelect: 'none',
        }}
      >
        CryptoQuant
      </div>
      <Spin
        indicator={<LoadingOutlined style={{ fontSize: 36 }} spin />}
        tip={tip}
        size="large"
      />
    </div>
  );
};

export default Loading;
