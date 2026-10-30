Shader "LunarPilot/ACES" {Properties {_MainTex("HDR",2D)="white"{} _Exposure("Exposure",Float)=1.12}
SubShader {Cull Off ZWrite Off ZTest Always Pass {CGPROGRAM
#pragma vertex vert_img
#pragma fragment frag
#include "UnityCG.cginc"
sampler2D _MainTex;float _Exposure;
float4 frag(v2f_img i):SV_Target{float3 x=tex2D(_MainTex,i.uv).rgb*_Exposure;float3 c=saturate((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14));return float4(c,1);}
ENDCG}}}
