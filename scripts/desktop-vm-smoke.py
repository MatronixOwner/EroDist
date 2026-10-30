#!/usr/bin/env python3
"""Boot the real ISO with QEMU; publish exact observations, never infer Hyper-V/install success."""
import json,os,socket,subprocess,time
from pathlib import Path
work=Path('build/vm-smoke').resolve();work.mkdir(parents=True,exist_ok=True)
out=Path('artifacts/desktop-iso');iso=next(out.glob('*.iso')).resolve()
report={'hyper_v_tested':False,'disk_install_tested':False,'live_boot_observed':False,'center_observed':False,'wine_gui_observed':False,'login_branding_observed':False}
qmp=work/'qmp.sock'
accel='kvm' if os.access('/dev/kvm',os.R_OK|os.W_OK) else 'tcg'
report['accelerator']=accel
command=['qemu-system-x86_64','-machine','q35','-accel',accel,'-m','4096','-smp','2','-vga','virtio','-display','none','-no-reboot','-boot','d','-cdrom',str(iso),'-qmp','unix:'+str(qmp)+',server=on,wait=off','-serial','file:'+str(work/'serial.log'),'-device','qemu-xhci','-device','usb-tablet','-nic','user,model=virtio-net-pci']
command+=['-cpu','host' if accel=='kvm' else 'max']
vm=subprocess.Popen(command,stdout=open(work/'qemu.log','w'),stderr=subprocess.STDOUT)
connection=None
try:
 deadline=time.monotonic()+30
 while not qmp.exists() and time.monotonic()<deadline:
  if vm.poll() is not None:
   if accel=='kvm':
    report['kvm_fallback_reason']=(work/'qemu.log').read_text()[-1500:]
    accel='tcg';report['accelerator']=accel
    command[command.index('-accel')+1]='tcg';command[command.index('-cpu')+1]='max'
    vm=subprocess.Popen(command,stdout=open(work/'qemu.log','w'),stderr=subprocess.STDOUT)
   else:raise RuntimeError('QEMU stopped: '+(work/'qemu.log').read_text())
  time.sleep(.2)
 connection=socket.socket(socket.AF_UNIX);connection.settimeout(30);connection.connect(str(qmp));stream=connection.makefile('rwb',buffering=0)
 json.loads(stream.readline())
 def call(name,args=None):
  stream.write((json.dumps({'execute':name,'arguments':args or {}})+'\n').encode())
  while True:
   reply=json.loads(stream.readline())
   if 'error' in reply:raise RuntimeError(reply['error'])
   if 'return' in reply:return reply['return']
 call('qmp_capabilities')
 def key(name):call('human-monitor-command',{'command-line':'sendkey '+name+' 30'});time.sleep(.07)
 def type_command(text):
  mapping={' ':'spc','-':'minus','/':'slash','=':'equal',',':'comma','.':'dot','_':'shift-minus'}
  key('alt-f2');time.sleep(2)
  for char in text:key('shift-'+char.lower() if char.isupper() else mapping.get(char,char))
  key('ret')
 def screenshot(name):
  ppm=work/(name+'.ppm');call('screendump',{'filename':str(ppm)})
  from PIL import Image
  Image.open(ppm).save(out/(name+'.png'))
  text=subprocess.run(['tesseract',str(out/(name+'.png')),'stdout','-l','eng+rus','--psm','11'],capture_output=True,text=True,timeout=45).stdout
  (work/(name+'.txt')).write_text(text)
  return text.casefold()
 # Leave the normal ISO menu/firmware path intact; selecting its default is explicit.
 time.sleep(12);key('ret')
 time.sleep(90 if accel=='kvm' else 240)
 for attempt in range(4):
  if vm.poll() is not None:raise RuntimeError('VM exited during boot')
  type_command('erodist-control-center');time.sleep(25)
  text=screenshot('vm-center-'+str(attempt))
  print('VM OCR center',attempt,repr(text[-2000:]),flush=True)
  if 'erodist' in text and ('настроек' in text or 'settings' in text):
   report.update(live_boot_observed=True,center_observed=True);break
  time.sleep(40)
 if report['center_observed']:
  key('alt-f4')
  type_command('env WINEDLLOVERRIDES=mscoree,mshtml= winecfg')
  time.sleep(40)
  text=screenshot('vm-wine')
  report['wine_gui_observed']='wine' in text and any(term in text for term in ('graphics','applications','libraries','графика','приложения','библиотеки'))
  key('alt-f4')
  type_command('qdbus6 org.kde.Shutdown /Shutdown logout');time.sleep(30);key('shift');time.sleep(3)
  text=screenshot('vm-login')
  report['login_branding_observed']='erodist' in text and any(term in text for term in ('password','sign in','log in','пароль','войти'))
except Exception as exc:
 report['error']=str(exc)
 print('VM smoke observation failed:',exc,flush=True)
finally:
 if connection:connection.close()
 vm.terminate()
 try:vm.wait(timeout=15)
 except subprocess.TimeoutExpired:vm.kill();vm.wait()
 (out/'VM-SMOKE.json').write_text(json.dumps(report,indent=2)+'\n')
 print('VM OBSERVATIONS:',json.dumps(report),flush=True)
