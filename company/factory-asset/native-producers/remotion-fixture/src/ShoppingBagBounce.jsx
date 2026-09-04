import React from 'react';
import {AbsoluteFill, interpolate, random, useCurrentFrame} from 'remotion';
import contract from './composition-contract.json';

const bagLayer = contract.layers.find((layer) => layer.layer_id === 'bag-shape');
const series = (property) => bagLayer.keyframes.filter((keyframe) => keyframe.property === property);
const interpolateSeries = (frame, property) => {
  const points = series(property);
  return interpolate(frame, points.map((x) => x.frame), points.map((x) => x.value), {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
};

export const ShoppingBagBounce = ({seed}) => {
  const frame = useCurrentFrame();
  const y = interpolateSeries(frame, 'Y');
  const rotation = interpolateSeries(frame, 'ROTATION');
  const accent = random(`shopping-bag-accent-${seed}`) > 0.5 ? '#8B6F47' : '#2563EB';

  return (
    <AbsoluteFill style={{backgroundColor: contract.canvas.background_color, fontFamily: 'Arial, sans-serif'}}>
      <div style={{position:'absolute',left:contract.canvas.width/2,top:y,width:320,height:360,transform:`translate(-50%, -50%) rotate(${rotation}deg)`,transformOrigin:'center center'}}>
        <div style={{position:'absolute',left:40,right:40,top:90,bottom:20,borderRadius:20,backgroundColor:'#F4F0E8',border:'16px solid #262626',boxSizing:'border-box'}} />
        <div style={{position:'absolute',left:95,top:20,width:130,height:130,border:'16px solid #262626',borderBottom:'none',borderRadius:'72px 72px 0 0',boxSizing:'border-box'}} />
        <div style={{position:'absolute',left:128,top:185,width:64,height:64,transform:'rotate(45deg)',backgroundColor:accent}} />
      </div>
      <div style={{position:'absolute',left:0,right:0,bottom:72,textAlign:'center',color:'#262626',fontSize:34,fontWeight:700,letterSpacing:2}}>SHOPPING BAG</div>
    </AbsoluteFill>
  );
};