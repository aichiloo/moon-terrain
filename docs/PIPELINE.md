# 制作流程与复现边界

## 当前可独立执行的工作

1. `python tools/download_demo.py` 下载固定版本完整包并检查 SHA-256；也可指定 `--archive 本地ZIP`。
2. `python tools/verify_demo.py` 对解压结果逐文件核对随包哈希。
3. `python tools/serve.py` 启动只监听本机的浏览页面。

`viewer/` 只存页面与渲染源码。`shared/assets.js`、地形 `data/*.js`、导出网格与贴图在完整包中；不要直接把源码目录当成完整离线包。

## 数值制作代码

`src/build_pilot.py` 为平坦与坡面生成局部细节，`src/build_regions.py` 将流程扩展到其余五类。代码使用 NumPy、SciPy、Pillow；保留原有数值算法，并将历史机器上的固定目录改为环境变量。

输入变量：

| 变量 | 默认位置 | 输入内容 |
| --- | --- | --- |
| MOON_TERRAIN_BASE_LIBRARY | inputs/base_library | 前序区域库：shared/assets.js、shared/three.min.js、regions/<类别>/region_data.js、gravel.js、metadata.json、data/native_dem.npz 及 sources/ 来源文件 |
| MOON_TERRAIN_APPROVED_PILOT | build/pilot | 两类初始样板输出及扩展流程的输入 |
| MOON_TERRAIN_OUTPUT | build/regions | 五类扩展输出及接地、接缝检查所用目录 |
| MOON_TERRAIN_REFERENCE_ROOT | inputs | 其下 references/ 可放 Apollo 参考 JPG |

制作阶段为：前序区域库 → 两类样板 → 将样板 shared/data/exports/sources/references 复制到扩展输出 → 五类扩展 → 页面整合、网格边缘衔接 → 沟谷接地修正 → 视角选择 → 数值与浏览器检查 → 打包。

本仓库存档了数值生成、沟谷接地与接缝检查的主要代码，**没有提供前序区域库，也未把所有历史页面整合与相机选择步骤改写为一键流水线**。因此当前明确支持成果浏览与校验，完整原始数据重建仍需补齐前序输入和编排。不要用这些脚本覆盖唯一的已验证成果；建议输出到 build/。

## 几何和法线

局部 12×12 米网格的间距为 0.02 米，601×601 个顶点。原始 DEM 为 2 米或 3.5 米采样。低频凸起改变真实网格；细颗粒主要用法线表达。凸起启用时使用 fine normal，避免重复叠加低频坡度。局部边缘进行衰减，与显示的周边三角形接合。

## 岩石接地

`audit_rille_seating.py` 在实际显示的远景、周边、局部三角形上采样。`fix_rille_seating.py` 调整垂直位置及少量埋入，对大岩石增加底面覆盖采样；不修改地形或水平位置。这里验证静态几何，不验证动态平衡。

## 输出

完整包包含 GLB 局部网格、16 位细节高度图、OpenGL / DirectX 法线图、分层 NPZ、岩石实例 JSON、原始 DEM 副本和来源说明。GLB 为米制、Y 轴向上；原始岩石实例为米制、Z 轴向上。元数据记载坐标转换与高度解码公式。
