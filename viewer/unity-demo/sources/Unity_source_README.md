# 七类月面地形 Unity 贴图渲染

打开 `index.html`，或双击 `START_HERE.cmd` 查看同机位对照。页面完全离线，支持七类地形、低机位与俯视近景、六种新材质方案，以及并排或滑动叠图。`renders/` 保存 1920 × 1080 原图。`seven_terrain_overview.jpg` 是七类混合材质的低机位总览；各类另附 `*_comparison.jpg` 原材质与混合方案对照。

## 本轮范围

沿用既有七类场景，在 Unity 2022.3.62f3c1 中实际渲染。包括月海平原、极区坡面、坑缘、局部凹地、极区脊线、溅射起伏、天然沟槽。每场景 2 个机位 × 7 个材质（原材质重建、5 套包内材质、1 个混合方案），共 98 张。照明与材质参数沿用已认可的两个样板。原材质也是 Unity 内的重建基线，不代表与旧版浏览器画面逐像素相同。

使用 Unity Built-in、自定义 Standard PBR 着色器、线性颜色空间、HDR、ACES 色调映射及 4 倍 MSAA。每组对照固定地形、岩石、机位、太阳、曝光。太阳高度为 25 度，属于渲染设置，不是针对该地形采集时刻标定的月照条件。

## 打开 Unity 工程

工程目录为 `UnityProject/`。用本机 Unity 2022.3.62f3c1 打开，在 `Assets/Scenes/` 选择场景：`plain` 月海平原、`slope` 极区坡面、`rim` 坑缘、`depression` 局部凹地、`ridge` 极区脊线、`ejecta` 溅射起伏、`rille` 天然沟槽。点击 Play 后，左上角按钮切换材质；鼠标右键观察，WASD 移动，滚轮改变视场。Game 视图相机附有同参数 ACES 映射；Scene 视图由编辑器控制，颜色可能不同。太阳强度统一为 1.5，曝光统一为 0.8。

## 材质及数据边界

- 新材质按包内米制尺寸平铺：Moon 01 为 3.1 m；Moon 03、04 为 3.2 m；Flat Macro 01、Dusted 01 为 0.4 m。
- 混合方案以 Moon 01 为基底，加入 Flat Macro 近景细节及 Dusted 局部混合，是本轮设计的可调渲染方案。
- 颜色图以 sRGB 导入；法线按 Normal Map 导入；AO、粗糙度按线性数据读取。Unity 光滑度由 `1 - roughness` 得到，金属度为 0。法线来自包内 OpenGL 版本，未翻转绿通道。
- 新贴图没有启用位移；原 DEM 外形、既有合成微地形和岩石布局沿用原场景。坐标由源 `(x,y,z)` 转为 Unity `(x,z,y)`，保持米制并反转三角形绕序。原场景已有微地形不应描述成新增实测高程。
- 包内说明和清单将贴图归于 Poly Haven 的实验室模拟月壤材质，而非月面实测或 AI 生成。25 张原文件有包内 MD5 记录，另保留本地校验及 SHA256 记录。原始位移图未参与本轮渲染，打包的粗糙度/AO 与法线已生成 Unity 用派生文件。
- 岩石使用既有网格、位置、变换及贴图，Unity 采用原方案颜色归一化的重建材质。没有为新贴图重新摆放岩石。

## DLSS 5

本机显卡为 RTX 3060 Laptop 6 GB。本轮未启用 DLSS，也未使用 DLSS 5 输出。2026-10-28 查询 NVIDIA 官方支持表：DLSS 5 的 3D-Guided Neural Rendering 列在 RTX 50 系列，RTX 30 系列未列支持。这不等于 RTX 30 系列不支持其他 DLSS 功能。

官方来源：[NVIDIA DLSS 技术与硬件支持表](https://www.nvidia.com/en-us/geforce/technologies/dlss/)。

## 核验

`verification/unity_render_report.json` 是 Unity 实际写出的引擎版本、GPU、图像、机位记录；`source_conversion.json` 记录源场景及转换；`delivery_checks.json` 记录图片完整性、机位一致性、网格及索引检查；`texture_package_integrity.json` 保留上轮贴图包完整性记录。日志随工程一并附在 `verification/`。

这是外观试验，不是机器人实走或碰撞验证。新贴图不会凭法线产生可碰撞的凹凸；未附 Terrain/MeshCollider，也未运行遮挡或任务成功率评测。
