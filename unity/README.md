# Unity 小体积源码快照

这里保留完整工程中的 C# 脚本、着色器、对应 `.meta`、Packages 和 ProjectSettings，方便查看与版本比较。目录结构与 Release 的 `UnityProject/` 对应。

**本目录不含地形网格、岩石、贴图、材质和场景文件，不能作为完整 Unity 工程直接运行。**

下载可编辑的完整工程：

```powershell
python tools/download_unity_project.py
```

下载器校验 Release 的 SHA-256 和 ZIP 内容后，解压到仓库内 `projects/Lunar_Unity_Project/`；在 Unity Hub 中选择其 `UnityProject/`，使用 Unity **2022.3.62f3c1** 打开。

详细的下载、操作与数据范围见 [Unity 工程说明](../docs/unity-project.md)。
