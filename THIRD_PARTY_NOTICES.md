# 第三方来源与许可

本仓库与发布包同时包含原创处理代码和第三方素材；第三方内容保留其原有许可，不因上传到此仓库而变更。

- **LROC DEM**：LINNECRATER、SHACKRDGE02、MERSENIUS1。原始来源、PDS 标签、获取记录与哈希见 [docs/sources/dem_sources.json](docs/sources/dem_sources.json)。分辨率和合成层边界见 README。
- **Poly Haven**：`moon_01`、`moon_02` 等地球月壤模拟实验扫描和地球岩石素材，获取清单声明 CC0；见 [V3_acquisition.json](docs/sources/V3_acquisition.json)。不能称为当前月面地点的原位扫描。
- **Apollo 样品形状资产**：沿用 Space Robotics Bench 资产记录中的 NASA Johnson Space Center / Astromaterials3D Apollo Samples 署名及 CC0 记录；详见 [原始署名清单](docs/sources/V3_SRB-ATTRIBUTIONS.md)。该原始清单也包含本项目未使用的其他资产，不表示全部都被本项目使用。
- **Apollo 参考照片**：完整包中的 Apollo 11 / Apollo 17 图片只作为视觉参考，没有提供对应 DEM 地点的纹理或高程测量。
- **Three.js**：MIT，Copyright 2010–2023 Three.js Authors。随源码保留原始许可头和完整许可文本 `viewer/shared/THREE-LICENSE.txt`。

本仓库的原创代码尚未指定单独的开源许可。素材的具体来源记录优先于概括性描述。

## v0.2.0 新增材质记录

本轮还使用 Moon 01、Moon 03、Moon 04、Flat Macro 01、Dusted 01 的扫描贴图，按 Poly Haven 原始素材记录保留来源；制作时已核对素材包中文件与官方载荷哈希。详见 [逐文件来源记录](viewer/unity-demo/evidence/texture_package_integrity.json)。这些是地面模拟物素材，不是目标地点的月面原位扫描。Three.js 仍适用 MIT，完整离线包保留许可证。
