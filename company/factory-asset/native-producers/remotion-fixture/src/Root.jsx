import React from 'react';
import {Composition} from 'remotion';
import {ShoppingBagBounce} from './ShoppingBagBounce.jsx';
import contract from './composition-contract.json';

export const RemotionRoot = () => (
  <>
    <Composition
      id="ShoppingBagBounce"
      component={ShoppingBagBounce}
      durationInFrames={contract.frame_count}
      fps={contract.fps}
      width={contract.canvas.width}
      height={contract.canvas.height}
      defaultProps={{seed: contract.seed}}
    />
  </>
);