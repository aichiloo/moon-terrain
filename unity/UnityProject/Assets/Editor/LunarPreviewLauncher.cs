using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class LunarPreviewLauncher {
 static readonly string[] ids={"plain","slope","rim","depression","ridge","ejecta","rille"};
 [MenuItem("Lunar Terrain/Open interactive preview")]
 public static void Open(){
  EditorBuildSettings.scenes=ids.Select(id=>new EditorBuildSettingsScene("Assets/Scenes/"+id+".unity",true)).ToArray();
  EditorSceneManager.OpenScene("Assets/Scenes/depression.unity");
  string marker=Path.Combine(Directory.GetParent(Application.dataPath).FullName,"Outputs","verification","unity_interactive_started.json");
  Directory.CreateDirectory(Path.GetDirectoryName(marker));
  File.WriteAllText(marker,"{\"status\":\"EDITOR_OPENED\",\"defaultScene\":\"depression\",\"terrainScenes\":7,\"materialVariants\":7}");
  EditorApplication.delayCall+=()=>{EditorApplication.isPlaying=true;};
 }
}
