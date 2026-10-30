Shader "LunarPilot/Ground" {
 Properties {
  _MainTex("Color",2D)="white"{} _NormalTex("Normal",2D)="bump"{} _SurfaceTex("AO and roughness",2D)="white"{}
  _FineTex("Fine color",2D)="white"{} _FineNormal("Fine normal",2D)="bump"{}
  _DustTex("Dust color",2D)="white"{} _DustNormal("Dust normal",2D)="bump"{} _DustSurface("Dust surface",2D)="white"{}
  _SecondTex("Original second color",2D)="white"{} _SecondNormal("Original second normal",2D)="bump"{} _SecondAO("Original second AO",2D)="white"{}
  _LocalNormal("Original local detail",2D)="bump"{}
  _Width("Tile width in meters",Float)=3.1 _Strength("Normal strength",Float)=.65 _Mixed("Mixed",Float)=0 _Original("Original",Float)=0
  _Offset("Source origin",Vector)=(0,0,0,0) _Focus("Source detail center",Vector)=(0,0,0,0)
 }
 SubShader { Tags {"RenderType"="Opaque"} LOD 300
 CGPROGRAM
 #pragma surface surf Standard fullforwardshadows addshadow nolightmap nodynlightmap nofog
 #pragma target 3.5
 #include "UnityCG.cginc"
 sampler2D _MainTex,_NormalTex,_SurfaceTex,_FineTex,_FineNormal,_DustTex,_DustNormal,_DustSurface,_SecondTex,_SecondNormal,_SecondAO,_LocalNormal;
 float _Width,_Strength,_Mixed,_Original;float4 _Offset,_Focus;
 struct Input {float3 worldPos;float3 viewDir;};
 void surf(Input IN,inout SurfaceOutputStandard o){
  float2 xy=IN.worldPos.xz+_Offset.xy;
  float2 uv=xy/_Width,fu=xy/.4;
  float distanceToEye=length(_WorldSpaceCameraPos-IN.worldPos);
  float fineFade=1-smoothstep(2.5,12,distanceToEye);
  float w=_Mixed*(.08+.13*smoothstep(-.35,.55,sin(xy.x*.37+xy.y*.23)*cos(xy.y*.29)));
  float3 col=lerp(tex2D(_MainTex,uv).rgb,tex2D(_DustTex,fu).rgb,w);
  float fg=dot(tex2D(_FineTex,fu).rgb,float3(.2126,.7152,.0722));
  col*=lerp(1,clamp(sqrt(max(fg,.002)/.10),.72,1.28),_Mixed*fineFade*.22);
  float2 ar=lerp(tex2D(_SurfaceTex,uv).rg,tex2D(_DustSurface,fu).rg,w);
  float3 n=normalize(lerp(UnpackNormal(tex2D(_NormalTex,uv)),UnpackNormal(tex2D(_DustNormal,fu)),w));
  float3 fn=UnpackNormal(tex2D(_FineNormal,fu));n=normalize(float3(n.xy+fn.xy*_Mixed*fineFade*.3,n.z));
  if(_Original>.5){
   float blendWeight=.32+.19*sin(xy.x*.37+xy.y*.23)*cos(xy.y*.29-xy.x*.17);
   float3 scanned=lerp(tex2D(_MainTex,uv).rgb,tex2D(_SecondTex,uv).rgb,blendWeight);
   float ao=lerp(tex2D(_SurfaceTex,uv).r,tex2D(_SecondAO,uv).r,blendWeight);
   float gain=clamp(sqrt(max(dot(scanned,float3(.333333,.333333,.333333)),.001)/.19),.48,1.65);
   float fade=1-smoothstep(12,50,distanceToEye);
   col=float3(.3005,.3005,.2789)*lerp(1,gain*lerp(.66,1,ao),fade);
   n=normalize(lerp(UnpackNormal(tex2D(_NormalTex,uv)),UnpackNormal(tex2D(_SecondNormal,uv)),blendWeight));
   n.xy*=.65*fade;
   float2 localUV=(xy-_Focus.xy)/12+.5;
   if(all(localUV>=0)&&all(localUV<=1))n=UnpackNormal(tex2D(_LocalNormal,localUV));
   ar=float2(1,1);
  }else{n.xy*=_Strength*(1-smoothstep(15,65,distanceToEye));}
  o.Albedo=col;o.Normal=normalize(n);o.Metallic=0;o.Smoothness=1-clamp(ar.y,.12,1);o.Occlusion=lerp(.72,1,ar.x);o.Alpha=1;
 }
 ENDCG
 } FallBack "Diffuse"
}
