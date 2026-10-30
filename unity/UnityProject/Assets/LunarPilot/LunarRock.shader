Shader "LunarPilot/Rock" {
 Properties {_MainTex("Source texture",2D)="white"{} _Mean("Source mean",Float)=.2}
 SubShader {Tags {"RenderType"="Opaque"} LOD 200
 CGPROGRAM
 #pragma surface surf Standard fullforwardshadows addshadow nolightmap nodynlightmap nofog
 #pragma target 3.0
 sampler2D _MainTex;float _Mean;
 struct Input {float2 uv_MainTex;float3 worldNormal;};
 void surf(Input IN,inout SurfaceOutputStandard o){float3 c=tex2D(_MainTex,IN.uv_MainTex).rgb;float lum=dot(c,float3(.2126,.7152,.0722));float g=clamp(pow(max(lum,.002)/max(_Mean,.003),.62),.48,1.6);float3 tint=lerp(1,c/max(lum,.003),.1);float3 rock=float3(.180,.176,.166)*g*tint;float dust=.22*smoothstep(.1,.85,IN.worldNormal.y);o.Albedo=lerp(rock,float3(.190,.186,.174)*(.8+.2*g),dust);o.Smoothness=.02;o.Metallic=0;o.Alpha=1;}
 ENDCG
 }FallBack "Diffuse"
}
