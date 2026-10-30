# 完整 Unity 月面地形工程

v0.3.0 提供可在 Unity Hub 打开的完整地形工程。它包含七个已保存场景、完整地形与岩石网格、贴图、材质、着色器、脚本、工程配置和 `.meta` 文件。Git 中的 `unity/` 仅保留小体积源码快照；大型资源随 Release ZIP 提供。

## 下载并打开

在仓库根目录运行，使用 Python 3.9 或更新版本，无需额外 Python 包：

```powershell
python tools/download_unity_project.py
```

下载文件为 [Lunar_Unity_Project_v0.3.0.zip](https://github.com/moonspace123/moon-terrain/releases/download/v0.3.0/Lunar_Unity_Project_v0.3.0.zip)，校验文件为 [同名 .zip.sha256](https://github.com/moonspace123/moon-terrain/releases/download/v0.3.0/Lunar_Unity_Project_v0.3.0.zip.sha256)。缓存位于 `build/`，默认解压位置为：

```text
projects/Lunar_Unity_Project/
├── UnityProject/       ← 在 Unity Hub 中选择这个文件夹
├── Evidence/           ← 来源、转换及已有检查记录
├── README.md
└── THIRD_PARTY_NOTICES.md
```

使用 **Unity 2022.3.62f3c1** 打开。`Library/` 等本机缓存未放入压缩包，首次打开时 Unity 会重新导入资源，需要一些时间。工程使用 Built-in 渲染管线和 Unity 内置模块，不需要安装 URP 或 HDRP。

也可从 [v0.3.0 Release 页面](https://github.com/moonspace123/moon-terrain/releases/tag/v0.3.0)手动下载 ZIP 和 SHA-256 文件，然后运行：

```powershell
python tools/download_unity_project.py --archive "D:\Downloads\Lunar_Unity_Project_v0.3.0.zip" --sha256-file "D:\Downloads\Lunar_Unity_Project_v0.3.0.zip.sha256"
```

只检查完整性、暂不解压：

```powershell
python tools/download_unity_project.py --verify-only
```

下载器会复用完整的缓存文件，并重试、续传中断的 `.part` 文件。它验证 SHA-256、安全路径和全部 ZIP CRC，再在临时目录解压。重复运行会保留已经下载并解压的工程；不会覆盖其中的本地修改。遇到其他非空目标目录时会停止，使用 `--destination "D:\Projects\Lunar_Unity_Project"` 可选择新的空目录。`projects/` 和 `build/` 用于本地大文件，不应加入 Git 提交。

## 现场预览

打开工程后，在菜单选择 **Lunar Terrain → Open interactive preview**。它会打开局部凹地并进入 Play。七个场景已启用在 Build Settings 中，也可以直接在 `Assets/Scenes/` 双击场景后运行。

| 场景 | 内容 |
|---|---|
| `plain` | 月海平原、平坦岩块区 |
| `slope` | 极区连续坡面 |
| `rim` | 完整坑区与坑缘 |
| `depression` | 局部凹地 |
| `ridge` | 天然坡折与脊线 |
| `ejecta` | 坑外连续起伏 |
| `rille` | 天然沟槽与两岸 |

Game 窗口左上角可切换七类地形与七种材质：原材质重建、当前混合方案、Moon 01、Moon 03、Moon 04、Flat Macro 01、Dusted 01。当前混合方案由 Moon 01 底层、Flat Macro 近景细节和 Dusted 局部覆尘组成。

| 操作 | 效果 |
|---|---|
| 按住鼠标右键并移动 | 转动视线 |
| WASD | 自由移动观察相机 |
| 鼠标滚轮 | 调整视场角 |
| 低机位／复位 | 返回场景初始观察位置 |
| 俯视近景 | 观察局部结构与岩石布局 |

这是自由观察相机，不是机器人运动控制。Game 视图应用 ACES 色调映射；Editor 的 Scene 视图由编辑器显示设置控制，外观可能不同。

## 工程与源码目录

完整工程保留已有场景引用的 `Assets/LunarPilot/Generated/` 网格与材质、`Meshes/` 二进制输入、`Textures/`、`scene_data.json` 及场景文件。Git 中的 `unity/UnityProject/` 只保留脚本、着色器、`.meta`、Packages 与 ProjectSettings，不能替代 Release 的完整工程。

v0.3.0 交付副本修复了可移植性：七个场景显式写入 Build Settings；预览标记、重建渲染图和报告均写入工程内的 `UnityProject/Outputs/`。这些本地输出无需加入 Git。

`LunarPilotBuilder.Run` 是可选的批量重建与渲染入口，会重写生成的网格、材质和场景，并在结束后退出 Editor。日常预览直接打开已有场景即可；需要重新生成时，在工程副本上调用。包内保留这一步所需的二进制网格与场景数据，但不提供从原始大幅 DEM 重新完成全部上游处理的一键重建承诺。

`Assets/Editor/LunarProjectAudit.cs` 是显式执行的检查工具，普通打开工程不会自动触发。已有渲染与来源记录随包保存在 `Evidence/`；具体通过范围应以记录内容为准。

## 数据与验证范围

宏观地形来自 LROC 的真实 DEM 产品，包括 LINNECRATER、SHACKRDGE02 和 MERSENIUS1，原始采样间距约为 **2 m 或 3.5 m**。近景微地形、插值网格及岩石的位置、尺度和部分布局属于后加的合成增强层，分别保留来源与参数。

**2 cm 是局部网格的建模密度，不是月面观测分辨率。** 材质采用地面模拟月壤等扫描素材，不是所选月球地点的原位材质测量。本轮材质比较没有通过新贴图添加真实地形位移，原有的合成微地形仍保留在几何层中。

既有 Unity 记录覆盖七类地形、两种固定机位、七种材质，共 98 张 1920 × 1080 实渲染图。比较时固定地形、岩石、机位、光照和曝光；太阳高度 25°、强度 1.5、曝光约 0.8 是展示设置。

当前工程交付证明的是地形资产、可编辑项目和外观展示。**机器人行走、碰撞、接触动力学、机械臂以及正式 TASK3／遮挡实验未由本工程交付验证。** 七类真实地形也不自动等于十二类实验机制已覆盖。来源许可和第三方说明见包内 `THIRD_PARTY_NOTICES.md` 与 `Evidence/`。

面向老师的便捷网页展示仍见 [Unity 网页演示说明](UNITY_DEMO.md)：其中 Unity 静态图和 Three.js 可交互三维观察均有单独标注。
