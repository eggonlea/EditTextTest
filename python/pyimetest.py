import argparse
import os
import shlex
import subprocess

from time import sleep
from uiautomator import device as d

TIMEOUT = 10
CORPUS = '/sdcard/asr_corpus'
PROP = 'debug.dsasr.wav'
DONE = 'done'
RESULT = 'dsasr_result.txt'

def execute(cmd, silent=False):
  if not silent:
    print(cmd)
  proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out = proc.communicate()[0]
  ret = proc.returncode
  return out, ret

def launch(app):
  execute('adb shell am start -n {}'.format(app))
  sleep(1)

def unlock(timeout=0):
  execute('adb shell input keyevent KEYCODE_MENU')
  if timeout > 0:
    execute('adb shell settings put system screen_off_timeout {}'.format(timeout))
  sleep(.5)

def screen_on():
  if d.screen == 'off':
    d.screen.on()
  sleep(.5)

def adb_root():
  execute('adb root')
  sleep(.5)

def voice_input(wav=None):
  edit = d(resourceId='com.example.edittexttest:id/editText')
  mic = d(resourceId='com.google.android.inputmethod.latin:id/key_pos_header_voice')
  voice = d(resourceId='com.google.android.inputmethod.latin:id/voiceime_circle_bar')
  label = d(resourceId='com.google.android.inputmethod.latin:id/voiceime_label')
  
  execute('adb shell setprop {} {}'.format(PROP, wav), True)
  edit.clear_text()
  edit.click()
  mic.click()

  timeout = 0
  while label.exists and timeout < TIMEOUT:
    status, _ = execute('adb shell getprop {}'.format(PROP), True)
    if status.decode().startswith(DONE):
      break
    sleep(1)
    timeout += 1

  sleep(.5)
  if voice.exists:
    voice.click()

  sleep(2)
  result = edit.text if edit.text else ''
  return result

def parse_args():
  parser = argparse.ArgumentParser(description='Speech To Text')
  parser.add_argument('--input', required=False, help='Previous dsasr result')
  return parser.parse_args()

if __name__ == "__main__":
  args = parse_args()
  adb_root()
  execute('adb shell setenforce 0')
  screen_on()
  unlock()
  launch('com.example.edittexttest/.MainActivity')

  fout = open(RESULT, 'w')
  wavs, _ = execute('adb shell find {} -name *.wav'.format(CORPUS))
  lines = wavs.splitlines()

  transcripts = {}
  if args.input is not None:
    with open(args.input) as fin:
      cur = dict((line.split(' ', maxsplit=1) for line in fin))
      transcripts.update(cur)
  print('Found %d inputs' % len(transcripts))

  i = 0
  n = len(lines)
  print('Found {} wav files'.format(n))
  for line in lines:
    try:
      wav = line.decode().strip()
      key = os.path.splitext(os.path.relpath(wav, CORPUS))[0]
      if key in transcripts and len(transcripts[key].strip()) > 0:
        continue
      text = voice_input(wav)
    except:
      print('Warning: failed to transcribe {}'.format(wav))
      text = ''
    try:
      line = u'{} {}\n'.format(key, text)
      fout.write(line)
      print(u'#{}/{} {}: [{}]'.format(i, n, key, text))
      i += 1
    except:
      print('Failed to write transcript for WAV {}'.format(wav))

  fout.close()
  execute('adb shell setprop {} None'.format(PROP))
  print('Done')
  d.press.home()
