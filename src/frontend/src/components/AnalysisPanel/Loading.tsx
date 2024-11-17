import React from 'react';
import { Overlay, Spinner, SpinnerSize } from '@fluentui/react';
import './Loading.css';

const Loading: React.FC = () => {
  return (
    <Overlay className="loading-overlay">
      <Spinner
        size={SpinnerSize.large}
        label="Loading..."
        styles={{
          root: { height: 'auto' },
          circle: { width: 100, height: 100, borderWidth: 4 },
          label: { fontSize: 20, fontWeight: 'bold', marginTop: 20 },
        }}
      />
    </Overlay>
  );
};

export default Loading;