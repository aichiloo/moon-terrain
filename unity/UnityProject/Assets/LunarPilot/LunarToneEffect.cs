using UnityEngine;
[ExecuteAlways]
[RequireComponent(typeof(Camera))]
public class LunarToneEffect : MonoBehaviour {
 public Shader toneShader;
 public float exposure=.8f;
 Material tone;
 void OnRenderImage(RenderTexture src,RenderTexture dst){
  if(toneShader==null){Graphics.Blit(src,dst);return;}
  if(tone==null)tone=new Material(toneShader){hideFlags=HideFlags.HideAndDontSave};
  tone.SetFloat("_Exposure",exposure);
  Graphics.Blit(src,dst,tone);
 }
 void OnDisable(){if(tone!=null){if(Application.isPlaying)Destroy(tone);else DestroyImmediate(tone);}}
}
