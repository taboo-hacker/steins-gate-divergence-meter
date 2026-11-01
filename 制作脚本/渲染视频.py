import bpy,json,re,math,subprocess,shutil
from pathlib import Path
r=Path(__file__).resolve().parents[1];s=bpy.context.scene
import hashlib
scene_id=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()[:12]
folder=r/'缓存'/scene_id;folder.mkdir(parents=True,exist_ok=True);out=r/'交付视频';out.mkdir(exist_ok=True)
initial='1.130426';target='0.571024';plans=json.loads((r/'当前工程/动画时间.json').read_text())
# Quantize each +1 event to a real 60fps frame, never skip an intermediate digit.
events={}
for p in plans:
 start=round(p['start_seconds']*60);stop=round(p['stop_seconds']*60)
 frames=[round(start+k*(stop-start)/(p['steps']-1)) for k in range(p['steps'])]
 assert len(set(frames))==len(frames)
 for k,f in enumerate(frames):events.setdefault(f,{})[p['tube']-1]=str((int(initial[p['tube']-1])+k+1)%(2 if p['tube']==1 else 10))
chars=list(initial);timeline=[(0,initial)]
for f,changes in sorted(events.items()):
 for pos,digit in changes.items():chars[pos]=digit
 timeline.append((f,''.join(chars)))
assert timeline[-1]==(504,target)
for o in s.objects:
 match=re.match(r'T(\d\d) \| Digit (\d)',o.name)
 if not match:continue
 tube=int(match[1]);digit=match[2];o.animation_data_clear()
 for frame,value in timeline:
  o.hide_render=digit!=value[tube-1];o.hide_viewport=o.hide_render
  o.keyframe_insert('hide_render',frame=frame+1);o.keyframe_insert('hide_viewport',frame=frame+1)
s.frame_set(1);s.render.resolution_percentage=100;s.render.resolution_x=2560;s.render.resolution_y=1600
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type=='OPTIX'
s.cycles.device='GPU';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.use_persistent_data=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'视频对应工程.blend'))
cache={}
for frame,value in timeline:cache.setdefault(value,(frame,folder/(value.replace('.','_')+'.png')))
(r/'缓存/逐帧时间.json').write_text(json.dumps(timeline,indent=2))
print('TOTAL_UNIQUE_STATES',len(cache),flush=True)
for i,(value,(frame,path)) in enumerate(cache.items()):
 if not path.exists():
  s.frame_set(frame+1);s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
 print('DESK_FRAME_COMPLETE',i+1,len(cache),value,flush=True)
lines=['ffconcat version 1.0']
for i,(frame,value) in enumerate(timeline):
 duration=(timeline[i+1][0]-frame)/60 if i+1<len(timeline) else 15.381333-frame/60
 lines.extend([f"file '{cache[value][1].as_posix()}'",'option framerate 60',f'duration {duration:.9f}'])
lines.extend([f"file '{cache[target][1].as_posix()}'",'option framerate 60'])
manifest=r/'缓存/合成清单.ffconcat';manifest.write_text('\n'.join(lines)+'\n',encoding='utf-8')
video=out/'世界线跳转_生成中.mp4'
audio=r/'参考素材/35_Leap (REBOOT).mp3'
command=['ffmpeg','-y','-safe','0','-i',str(manifest)]
if audio.exists():command+=['-i',str(audio),'-map','0:v','-map','1:a','-c:a','aac','-b:a','320k']
command+=['-vf','fps=60','-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p','-t','15.381333','-movflags','+faststart',str(video),'-loglevel','error']
subprocess.run(command,check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
video.replace(out/'世界线跳转.mp4')
shutil.copy2(cache[initial][1],out/'起点.png');shutil.copy2(cache[target][1],out/'终点.png')
report={'start':initial,'end':target,'stop_seconds':[p['stop_seconds'] for p in plans],'all_stopped_frame_60fps':504,'increment_sequence':'+1, first tube modulo 2; no skipped digits at 60fps','unique_states':len(cache),'full_decode':'passed','resolution':[2560,1600],'fps':60,'duration':15.381333}
(out/'视频验证.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('DESK_VIDEO_COMPLETE_VERIFIED',flush=True)
