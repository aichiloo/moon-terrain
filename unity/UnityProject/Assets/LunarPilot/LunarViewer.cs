using UnityEngine;
using UnityEngine.SceneManagement;
public class LunarViewer:MonoBehaviour {
 public Material[] materials;public Renderer[] ground;public Camera viewCamera;public Transform orbitTarget;public string sceneLabel;
 int selected=1;Vector2 angles;Vector3 initialPosition;Quaternion initialRotation;float initialFieldOfView;Font uiFont;
 readonly string[] sceneIds={"plain","slope","rim","depression","ridge","ejecta","rille"};
 readonly string[] sceneNames={"月海平原","极区坡面","坑缘","局部凹地","极区脊线","溅射起伏","天然沟槽"};
 readonly string[] materialNames={"原材质（Unity 重建）","新贴图混合方案","Moon 01","Moon 03","Moon 04","Flat Macro 01","Dusted 01"};
 void Start(){if(viewCamera==null)viewCamera=Camera.main;initialPosition=viewCamera.transform.position;initialRotation=viewCamera.transform.rotation;initialFieldOfView=viewCamera.fieldOfView;SyncAngles();uiFont=Font.CreateDynamicFontFromOSFont(new[]{"Microsoft YaHei","SimHei","Arial"},16);}
 void SyncAngles(){angles=new Vector2(viewCamera.transform.eulerAngles.y,viewCamera.transform.eulerAngles.x);if(angles.y>180)angles.y-=360;}
 public void LowView(){viewCamera.transform.SetPositionAndRotation(initialPosition,initialRotation);viewCamera.fieldOfView=initialFieldOfView;SyncAngles();}
 public void OrbitView(){var focus=orbitTarget.position;viewCamera.transform.position=focus+new Vector3(Mathf.Cos(2.35f)*Mathf.Cos(.8f),Mathf.Sin(.8f),Mathf.Sin(2.35f)*Mathf.Cos(.8f))*15;viewCamera.transform.LookAt(focus);viewCamera.fieldOfView=52;SyncAngles();}
 public void SelectMaterial(int n){selected=n;foreach(var r in ground)r.sharedMaterial=materials[n];}
 void Update(){if(Input.GetMouseButton(1)){angles.x+=Input.GetAxis("Mouse X")*2;angles.y-=Input.GetAxis("Mouse Y")*2;angles.y=Mathf.Clamp(angles.y,-80,80);viewCamera.transform.rotation=Quaternion.Euler(angles.y,angles.x,0);}
  float s=3*Time.deltaTime;if(Input.GetKey(KeyCode.W))viewCamera.transform.position+=viewCamera.transform.forward*s;if(Input.GetKey(KeyCode.S))viewCamera.transform.position-=viewCamera.transform.forward*s;if(Input.GetKey(KeyCode.A))viewCamera.transform.position-=viewCamera.transform.right*s;if(Input.GetKey(KeyCode.D))viewCamera.transform.position+=viewCamera.transform.right*s;
  viewCamera.fieldOfView=Mathf.Clamp(viewCamera.fieldOfView-Input.mouseScrollDelta.y*2,28,90);
 }
 void OnGUI(){
  var previousFont=GUI.skin.font;if(uiFont!=null)GUI.skin.font=uiFont;
  GUI.Box(new Rect(12,12,265,510),"七类月面地形 · Unity 实时预览");
  GUI.Label(new Rect(22,42,240,24),"地形");
  for(int i=0;i<sceneIds.Length;i++){
   GUI.backgroundColor=sceneLabel==sceneIds[i]?new Color(.5f,.9f,.65f):Color.white;
   if(GUI.Button(new Rect(22,68+i*25,245,23),sceneNames[i])&&sceneLabel!=sceneIds[i])SceneManager.LoadScene(sceneIds[i]);
  }
  GUI.backgroundColor=Color.white;GUI.Label(new Rect(22,247,240,24),"材质");
  for(int i=0;i<materials.Length;i++){
   GUI.backgroundColor=selected==i?new Color(.5f,.9f,.65f):Color.white;
   if(GUI.Button(new Rect(22,273+i*25,245,23),i<materialNames.Length?materialNames[i]:materials[i].name))SelectMaterial(i);
  }
  GUI.backgroundColor=Color.white;
  if(GUI.Button(new Rect(22,467,117,30),"低机位 / 复位"))LowView();
  if(GUI.Button(new Rect(150,467,117,30),"俯视近景"))OrbitView();
  GUI.Label(new Rect(16,Screen.height-32,850,28),"鼠标右键观察 · WASD 移动 · 滚轮缩放 · 低机位按钮恢复初始位置");
  GUI.skin.font=previousFont;
 }
 void OnDestroy(){if(uiFont!=null)Destroy(uiFont);}
}

