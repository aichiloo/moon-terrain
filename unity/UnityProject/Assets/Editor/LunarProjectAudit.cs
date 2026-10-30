using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

// Explicit entry point only: -batchmode -executeMethod LunarProjectAudit.RunBatch
// Do not pass -quit: this audit enters Play Mode and exits after its update loop finishes.
[InitializeOnLoad]
public static class LunarProjectAudit
{
    const string Key = "LunarProjectAudit.";
    static readonly string[] Ids = { "plain", "slope", "rim", "depression", "ridge", "ejecta", "rille" };
    static readonly string[] CommonTextures = { "_MainTex", "_NormalTex", "_SurfaceTex", "_FineTex", "_FineNormal", "_DustTex", "_DustNormal", "_DustSurface" };
    static readonly string[] OriginalTextures = { "_SecondTex", "_SecondNormal", "_SecondAO", "_LocalNormal" };

    [Serializable] public class MeshInfo { public string file; public int vertices, triangles; }
    [Serializable] public class RockType : MeshInfo { public int id; public string texture; }
    [Serializable] public class Rock { public int type; public float[] matrix; }
    [Serializable] public class Region { public string id; public MeshInfo[] meshes; public Rock[] rocks; public int rock_count; }
    [Serializable] public class Source { public Region[] regions; public RockType[] rockTypes; }
    [Serializable] public class SceneCheck
    {
        public string scene, phase;
        public int terrainMeshes, terrainVertices, rockInstances, materialVariants, materialSwitches;
        public bool referencesComplete, startCameraReady, orbitViewPassed, lowViewResetPassed, materialCameraUnchanged;
    }
    [Serializable] public class ImageCheck
    {
        public string scene, file, sha256;
        public int width, height;
        public float nonBlackFraction;
        public bool activeACES;
    }
    [Serializable] public class AuditReport
    {
        public string status, startedUtc, completedUtc, unityVersion, projectPath, graphicsAPI, gpu;
        public string scope = "Saved-asset reference checks and actual Play Mode scene/material/camera smoke test; no walking, contact, or occlusion validation.";
        public bool enteredPlayMode, graphicsAvailable;
        public int enabledSceneCount;
        public List<SceneCheck> editScenes = new List<SceneCheck>();
        public List<SceneCheck> playScenes = new List<SceneCheck>();
        public List<ImageCheck> images = new List<ImageCheck>();
        public List<string> errors = new List<string>();
    }

    static Source source;
    static AuditReport report;
    static bool finishing;
    static string ProjectRoot { get { return Directory.GetParent(Application.dataPath).FullName; } }
    static string Verification { get { return Path.Combine(ProjectRoot, "Outputs", "verification"); } }
    static string ReportPath { get { return Path.Combine(Verification, "portable_project_audit.json"); } }
    static bool Active { get { return SessionState.GetBool(Key + "active", false); } }

    static LunarProjectAudit()
    {
        // SessionState survives the domain reload caused by entering Play Mode.
        if (!Active) return;
        try { Hook(); EditorApplication.delayCall += Tick; }
        catch (Exception ex) { Fail(ex); }
    }

    public static void RunBatch()
    {
        try
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("RunBatch must start in Edit Mode.");
            Directory.CreateDirectory(Verification);
            report = new AuditReport {
                status = "EDIT_CHECK_STARTED", startedUtc = DateTime.UtcNow.ToString("o"),
                unityVersion = Application.unityVersion, projectPath = ProjectRoot,
                graphicsAPI = SystemInfo.graphicsDeviceType.ToString(), gpu = SystemInfo.graphicsDeviceName,
                graphicsAvailable = SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null
            };
            Save();
            SessionState.SetBool(Key + "active", true);
            Hook();
            LoadSource();
            var enabled = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
            report.enabledSceneCount = enabled.Length;
            Require(Ids.All(id => enabled.Contains("Assets/Scenes/" + id + ".unity")), "All seven scenes must be enabled in Build Settings.");
            foreach (string shaderName in new[] { "LunarPilot/Ground", "LunarPilot/Rock", "LunarPilot/ACES" })
            {
                Shader shader = Shader.Find(shaderName);
                Require(shader != null, "Missing shader: " + shaderName);
                Require(!ShaderUtil.ShaderHasError(shader), "Shader compilation errors: " + shaderName);
                if (report.graphicsAvailable) Require(shader.isSupported, "Unsupported shader: " + shaderName);
            }
            foreach (string id in Ids)
            {
                EditorSceneManager.OpenScene("Assets/Scenes/" + id + ".unity", OpenSceneMode.Single);
                report.editScenes.Add(CheckScene(id, false));
                Save();
            }
            EditorSceneManager.OpenScene("Assets/Scenes/plain.unity", OpenSceneMode.Single);
            report.status = "ENTERING_PLAY_MODE";
            Save();
            SessionState.SetString(Key + "phase", "enter");
            SessionState.SetInt(Key + "index", 0);
            SessionState.SetFloat(Key + "playStart", (float)EditorApplication.timeSinceStartup);
            EditorApplication.isPlaying = true;
            EditorApplication.QueuePlayerLoopUpdate();
            Debug.Log("LUNAR_AUDIT_ENTER_PLAY");
        }
        catch (Exception ex) { Fail(ex); }
    }

    static void Hook()
    {
        EditorApplication.update -= Tick; EditorApplication.update += Tick;
        Application.logMessageReceived -= OnLog; Application.logMessageReceived += OnLog;
        CompilationPipeline.assemblyCompilationFinished -= OnCompilation;
        CompilationPipeline.assemblyCompilationFinished += OnCompilation;
    }
    static void LoadSource()
    {
        if (source != null) return;
        source = JsonUtility.FromJson<Source>(File.ReadAllText(Path.Combine(Application.dataPath, "LunarPilot", "scene_data.json")));
        Require(source != null && source.regions != null && source.regions.Length == 7, "scene_data.json must contain seven regions.");
        Require(source.rockTypes != null && source.rockTypes.Length == 9, "scene_data.json must contain nine rock types.");
        foreach (Region r in source.regions)
            foreach (MeshInfo m in r.meshes)
                Require(File.Exists(Path.Combine(Application.dataPath, "LunarPilot", m.file)), "Missing terrain source: " + m.file);
        foreach (RockType r in source.rockTypes)
        {
            Require(File.Exists(Path.Combine(Application.dataPath, "LunarPilot", r.file)), "Missing rock source: " + r.file);
            Require(File.Exists(Path.Combine(Application.dataPath, "LunarPilot", r.texture)), "Missing rock texture: " + r.texture);
        }
    }
    static void LoadReport()
    {
        if (report == null && File.Exists(ReportPath)) report = JsonUtility.FromJson<AuditReport>(File.ReadAllText(ReportPath));
        if (report == null) throw new InvalidOperationException("Audit state was not recovered after domain reload.");
    }

    static SceneCheck CheckScene(string id, bool playing)
    {
        LoadSource();
        Require(SceneManager.GetActiveScene().name == id, "Wrong active scene: " + id);
        Region expected = source.regions.Single(r => r.id == id);
        LunarViewer viewer = UnityEngine.Object.FindObjectOfType<LunarViewer>();
        Require(viewer != null && viewer.sceneLabel == id, "Missing or wrong LunarViewer: " + id);
        Require(viewer.ground != null && viewer.ground.Length == 3 && expected.meshes.Length == 3, "Expected three terrain renderers: " + id);
        Require(viewer.materials != null && viewer.materials.Length == 7, "Expected seven material variants: " + id);
        int vertices = 0;
        for (int i = 0; i < 3; i++)
        {
            Renderer renderer = viewer.ground[i];
            Require(renderer != null, "Missing ground renderer: " + id);
            MeshFilter filter = renderer.GetComponent<MeshFilter>();
            Require(filter != null && filter.sharedMesh != null, "Missing ground mesh: " + id);
            Mesh mesh = filter.sharedMesh;
            Require(mesh.name == Path.GetFileNameWithoutExtension(expected.meshes[i].file), "Ground mesh order differs from JSON: " + id);
            Require(mesh.vertexCount == expected.meshes[i].vertices, "Ground vertex count differs from JSON: " + id);
            Require(mesh.triangles.Length / 3 == expected.meshes[i].triangles, "Ground triangle count differs from JSON: " + id);
            vertices += mesh.vertexCount;
        }
        for (int i = 0; i < viewer.materials.Length; i++)
        {
            Material mat = viewer.materials[i];
            Require(mat != null && mat.shader != null && mat.shader.name == "LunarPilot/Ground", "Missing ground material/shader: " + id);
            foreach (string property in CommonTextures)
                Require(mat.HasProperty(property) && mat.GetTexture(property) != null, "Missing texture " + property + " in " + id + "/" + i);
            if (i == 0) foreach (string property in OriginalTextures)
                Require(mat.GetTexture(property) != null, "Missing original texture " + property + " in " + id);
        }
        GameObject rockRoot = GameObject.Find("Original rock instances");
        Require(rockRoot != null, "Missing rock instances root: " + id);
        Require(expected.rocks != null && expected.rock_count == expected.rocks.Length && rockRoot.transform.childCount == expected.rocks.Length, "Rock count differs from JSON: " + id);
        for (int i = 0; i < expected.rocks.Length; i++)
        {
            Transform rock = rockRoot.transform.GetChild(i);
            Rock rec = expected.rocks[i];
            RockType type = source.rockTypes.Single(t => t.id == rec.type);
            MeshFilter filter = rock.GetComponent<MeshFilter>();
            Renderer renderer = rock.GetComponent<Renderer>();
            Require(filter != null && filter.sharedMesh != null && filter.sharedMesh.vertexCount == type.vertices, "Missing/wrong rock mesh: " + id + "/" + i);
            Require(filter.sharedMesh.name == Path.GetFileNameWithoutExtension(type.file), "Wrong rock type: " + id + "/" + i);
            Require(renderer != null && renderer.sharedMaterial != null && renderer.sharedMaterial.shader != null && renderer.sharedMaterial.shader.name == "LunarPilot/Rock", "Missing rock material: " + id + "/" + i);
            Require(renderer.sharedMaterial.GetTexture("_MainTex") != null, "Missing rock texture: " + id + "/" + i);
            Require(rec.matrix != null && rec.matrix.Length == 16, "Invalid rock matrix: " + id + "/" + i);
            Require(Vector3.Distance(rock.position, new Vector3(rec.matrix[12], rec.matrix[13], rec.matrix[14])) < .002f, "Rock position differs from JSON: " + id + "/" + i);
        }
        Camera cam = viewer.viewCamera;
        Require(cam != null && cam == Camera.main && viewer.orbitTarget != null, "Missing main camera or focus: " + id);
        LunarToneEffect tone = cam.GetComponent<LunarToneEffect>();
        Require(tone != null && tone.enabled && tone.toneShader != null && tone.toneShader.name == "LunarPilot/ACES" && Mathf.Abs(tone.exposure - .8f) < .0001f, "Missing active ACES effect: " + id);
        return new SceneCheck { scene = id, phase = playing ? "actual_play_mode" : "saved_scene", terrainMeshes = 3, terrainVertices = vertices, rockInstances = expected.rocks.Length, materialVariants = 7, referencesComplete = true };
    }

    static void Tick()
    {
        if (!Active || finishing) return;
        try
        {
            LoadReport();
            double now = EditorApplication.timeSinceStartup;
            Require(now - SessionState.GetFloat(Key + "playStart", (float)now) <= 120, "Play Mode audit timed out after 120 seconds.");
            string phase = SessionState.GetString(Key + "phase", "");
            if (phase == "enter")
            {
                if (!EditorApplication.isPlaying) return;
                report.enteredPlayMode = true; report.status = "PLAY_CHECK_STARTED"; Save();
                SessionState.SetString(Key + "phase", "load");
                return;
            }
            if (phase != "load" && phase != "settle") return;
            Require(EditorApplication.isPlaying, "Play Mode ended before the audit completed.");
            int index = SessionState.GetInt(Key + "index", 0);
            if (phase == "load")
            {
                SceneManager.LoadScene(Ids[index], LoadSceneMode.Single);
                SessionState.SetInt(Key + "frame", Time.frameCount);
                SessionState.SetFloat(Key + "settleUntil", (float)now + .3f);
                SessionState.SetString(Key + "phase", "settle");
                EditorApplication.QueuePlayerLoopUpdate();
                return;
            }
            EditorApplication.QueuePlayerLoopUpdate();
            if (now < SessionState.GetFloat(Key + "settleUntil", 0) || Time.frameCount < SessionState.GetInt(Key + "frame", 0) + 2) return;
            string id = Ids[index];
            SceneCheck check = CheckScene(id, true);
            LunarViewer viewer = UnityEngine.Object.FindObjectOfType<LunarViewer>();
            Camera cam = viewer.viewCamera;
            Vector3 initialPosition = cam.transform.position;
            Quaternion initialRotation = cam.transform.rotation;
            float initialFov = cam.fieldOfView;
            Require(Vector3.Distance(initialPosition, new Vector3(0, .55f, 0)) < .002f && Mathf.Abs(initialFov - 66) < .001f, "Start camera was not initialized to saved low view: " + id);
            check.startCameraReady = true;
            for (int material = 0; material < 7; material++)
            {
                viewer.SelectMaterial(material);
                Require(viewer.ground.All(r => r.sharedMaterial == viewer.materials[material]), "Runtime material switch failed: " + id + "/" + material);
                Require(Vector3.Distance(cam.transform.position, initialPosition) < .0001f && Quaternion.Angle(cam.transform.rotation, initialRotation) < .001f, "Material switch moved the camera: " + id);
                check.materialSwitches++;
            }
            check.materialCameraUnchanged = true;
            viewer.OrbitView();
            Vector3 expectedOrbit = viewer.orbitTarget.position + new Vector3(Mathf.Cos(2.35f) * Mathf.Cos(.8f), Mathf.Sin(.8f), Mathf.Sin(2.35f) * Mathf.Cos(.8f)) * 15;
            Require(Vector3.Distance(cam.transform.position, expectedOrbit) < .002f && Mathf.Abs(cam.fieldOfView - 52) < .001f, "Orbit view failed: " + id);
            check.orbitViewPassed = true;
            viewer.LowView();
            Require(Vector3.Distance(cam.transform.position, initialPosition) < .0001f && Quaternion.Angle(cam.transform.rotation, initialRotation) < .001f && Mathf.Abs(cam.fieldOfView - initialFov) < .001f, "Low view reset failed: " + id);
            check.lowViewResetPassed = true;
            viewer.SelectMaterial(1);
            if (report.graphicsAvailable && (id == "plain" || id == "depression")) report.images.Add(SaveCamera(cam, id));
            report.playScenes.Add(check); Save();
            Debug.Log("LUNAR_AUDIT_PLAY_SCENE_PASS " + id);
            if (index + 1 == Ids.Length) { Finish(report.errors.Count == 0); return; }
            SessionState.SetInt(Key + "index", index + 1);
            SessionState.SetString(Key + "phase", "load");
        }
        catch (Exception ex) { Fail(ex); }
    }

    static ImageCheck SaveCamera(Camera cam, string id)
    {
        const int width = 1920, height = 1080;
        RenderTexture previousTarget = cam.targetTexture, previousActive = RenderTexture.active;
        var target = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
        var image = new Texture2D(width, height, TextureFormat.RGB24, false);
        try
        {
            target.Create(); cam.targetTexture = target;
            // The saved scene's enabled LunarToneEffect executes during Camera.Render.
            cam.Render(); RenderTexture.active = target;
            image.ReadPixels(new Rect(0, 0, width, height), 0, 0); image.Apply();
            Color32[] pixels = image.GetPixels32();
            int nonBlack = 0;
            foreach (Color32 pixel in pixels) if (Math.Max(pixel.r, Math.Max(pixel.g, pixel.b)) > 4) nonBlack++;
            float fraction = (float)nonBlack / pixels.Length;
            Require(fraction > .01f, "Camera render is nearly black: " + id);
            byte[] png = image.EncodeToPNG();
            string filename = "portable_" + id + "_play_mixed.png";
            File.WriteAllBytes(Path.Combine(Verification, filename), png);
            string hash;
            using (SHA256 sha = SHA256.Create()) hash = BitConverter.ToString(sha.ComputeHash(png)).Replace("-", "").ToLowerInvariant();
            return new ImageCheck { scene = id, file = filename, sha256 = hash, width = width, height = height, nonBlackFraction = fraction, activeACES = cam.GetComponent<LunarToneEffect>().enabled };
        }
        finally
        {
            cam.targetTexture = previousTarget; RenderTexture.active = previousActive;
            target.Release(); UnityEngine.Object.DestroyImmediate(target); UnityEngine.Object.DestroyImmediate(image);
        }
    }
    static void OnLog(string condition, string stackTrace, LogType type)
    {
        if (!Active || finishing || (type != LogType.Error && type != LogType.Exception && type != LogType.Assert)) return;
        try { LoadReport(); if (report.errors.Count < 100) report.errors.Add(type + ": " + condition + "\n" + stackTrace); Save(); }
        catch { /* The external Unity log remains the fallback if report I/O itself fails. */ }
    }
    static void OnCompilation(string assemblyPath, CompilerMessage[] messages)
    {
        if (!Active) return;
        var errors = messages.Where(m => m.type == CompilerMessageType.Error).ToArray();
        if (errors.Length > 0) Fail(new Exception("Compilation failed in " + assemblyPath + ":\n" + string.Join("\n", errors.Select(m => m.file + ":" + m.line + " " + m.message).ToArray())));
    }
    static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    static void Save() { Directory.CreateDirectory(Verification); File.WriteAllText(ReportPath, JsonUtility.ToJson(report, true)); }
    static void Fail(Exception ex)
    {
        try
        {
            if (report == null && File.Exists(ReportPath)) report = JsonUtility.FromJson<AuditReport>(File.ReadAllText(ReportPath));
            if (report == null) report = new AuditReport { projectPath = ProjectRoot, unityVersion = Application.unityVersion, startedUtc = DateTime.UtcNow.ToString("o") };
            report.errors.Add(ex.ToString());
            File.WriteAllText(Path.Combine(Verification, "portable_project_audit_error.txt"), ex.ToString());
            Finish(false);
        }
        catch (Exception fatal) { Debug.LogError("LUNAR_AUDIT_FATAL " + fatal); SessionState.SetBool(Key + "active", false); EditorApplication.Exit(1); }
    }
    static void Finish(bool passed)
    {
        if (finishing) return;
        finishing = true;
        report.status = passed ? (report.graphicsAvailable ? "PORTABLE_PLAY_AND_RENDER_PASS" : "PORTABLE_PLAY_PASS_NO_GPU_RENDER") : "FAILED";
        report.completedUtc = DateTime.UtcNow.ToString("o");
        Save();
        SessionState.SetBool(Key + "active", false);
        EditorApplication.update -= Tick; Application.logMessageReceived -= OnLog;
        CompilationPipeline.assemblyCompilationFinished -= OnCompilation;
        Debug.Log("LUNAR_AUDIT_COMPLETE " + report.status + " " + ReportPath);
        EditorApplication.Exit(passed ? 0 : 1);
    }
}
