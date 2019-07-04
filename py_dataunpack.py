#!python2

from __future__ import print_function

import json
import math
import os
import struct
import sys

def export_data(fp, p, j):
  raw = [0 for k in range(len(j["content"]))]
  val = [0 for k in range(len(j["content"]))]
  for k in range(len(j["content"])):
    ch = j["content"][k]
    if (not "derived" in ch.keys()) or (not ch["derived"]):
      s_fmt = ch["s_fmt"]
      ofs   = ch["offset"]
      raw[k] = struct.unpack_from(s_fmt, p, ofs)[0]
    
  for k in range(len(j["content"])):
    ch = j["content"][k]
    if "lambda" in ch.keys():
      if "lambda_ref" in ch.keys():
        param = [raw[k],]
        for idx in ch["lambda_ref"]:
          param.append(raw[idx])
      else:
        param = raw[k]
      val[k] = eval(ch["lambda"])(param)
    else:
      val[k] = raw[k]

  for k in range(len(j["content"])):
    ch = j["content"][k]
    if (not "hidden" in ch.keys()) or (not ch["hidden"]):
      p_fmt = ch["p_fmt"]
      str = p_fmt % val[k]
      fp.write(str + ", ")
  fp.write("\n")
  return
# end export_data()

def export_title(fp, j):
  for ch in j["content"]:
    if (not "hidden" in ch.keys()) or (not ch["hidden"]):
      fp.write(ch["title"] + ", ")
  fp.write("\n")
  return
# end export_title()

def find_header(fp, j):
  if j["header_size"]:
    frame_sz    = j["frame_size"]
    header_sz   = j["header_size"]
    header_str  = j["header"]
    counter_sz  = j["counter_size"]
    if counter_sz:
      counter_ofs = j["counter_offset"]
      if counter_ofs < header_sz:
        return False
      test_sz = frame_sz*2 + counter_ofs + counter_sz
    else:
      test_sz = frame_sz*2 + header_sz

    for retry in range(frame_sz):
      t = fp.read(test_sz)
      if len(t) < test_sz:
        break
      f = True
      f = f and (t[frame_sz*0 : (frame_sz*0+header_sz)] == header_str)
      f = f and (t[frame_sz*1 : (frame_sz*1+header_sz)] == header_str)
      f = f and (t[frame_sz*2 : (frame_sz*2+header_sz)] == header_str)
      if f and counter_sz:
        cnt = [0, 0, 0]
        cnt_mod = 256 ** counter_sz
        for k in range(3):
          for i in range(counter_sz):
            cnt[k] = cnt[k] * 256 + ord(t[frame_sz*k+counter_ofs+counter_sz-i-1])
        f = f and ((cnt[0]+1)%cnt_mod == cnt[1])
        f = f and ((cnt[1]+1)%cnt_mod == cnt[2])
      if f:
        fp.seek(-test_sz, 1)
        return True
      else:
        fp.seek(-test_sz+1, 1)
        print('H', end='')
  return False
# end find_header()

def check_frame(frame, j):
  if j["header_size"]:
    return frame[0:j["header_size"]] != j["header"]
  return 0
# end check_frame()

def decode_data(file_raw, j):
  frame_cnt = 0
  file_out = os.path.splitext(file_raw)[0] + ".csv"
  fpr = open(file_raw, 'rb')
  fpw = open(file_out, 'wb')
  frame_sz = j["frame_size"]
  header_sz = j["header_size"]
  if header_sz:
    header_hex = j["header_hex"]
    if header_sz * 2 > len(header_hex):
      return -1
    header_str = ""
    for k in range(header_sz):
      header_str = header_str + chr(int(header_hex[2*k:2*k+2], base=16))
    j["header"] = header_str
  if find_header(fpr, j):
    while 1:
      frame = fpr.read(frame_sz)
      if len(frame) != frame_sz:
        break
      if check_frame(frame, j):
        print('X', end='')
        fpr.seek(-frame_sz, 1)
        if not find_header(fpr, j):
          break
        else:
          continue
      if frame_cnt %  100 == 0:
        print('.', end='')
      if frame_cnt == 0:
        export_title(fpw, j)
      frame_cnt = frame_cnt + 1
      payload = frame[j["payload_offset"]:(j["payload_offset"]+j["payload_size"])]
      export_data(fpw, payload, j)
  fpr.close()
  fpw.close()
  return frame_cnt
# end decode_data()

def usage(script):
  s = os.path.split(script)[1]
  print("")
  print("  Tool to decode structured data from binary record file.")
  print("  Usage:")
  print("  %s DATA_FILE JSON_CONFIG_FILE" % s)
  return
# end usage()

def main(argv):
  retval = 0
  if len(argv)>=2 and os.path.isfile(argv[1]):
    if len(argv)>=3 and os.path.isfile(argv[2]):
      json_file = argv[2]
    elif os.path.isfile(os.path.splitext(argv[1])[0] + ".json"):
      json_file = os.path.splitext(argv[1])[0] + ".json"
    elif os.path.isfile(os.path.split(argv[1])[0] + "defconfig.json"):
      json_file = os.path.split(argv[1])[0] + "defconfig.json"
    else:
      print("cannot find json file (%s)" % json_file)
      retval = 2

    if retval == 0:
      try:
        fp = open(json_file)
        j = json.load(fp)
        fp.close()
      except Exception as e:
        print("load json file (%s) error" % json_file)
        print(e)
        retval = 3
      else:
        cnt = decode_data(argv[1], j)
        print("\nDecode finished. %d records exported." % cnt)
        retval = 0

  if retval:
    usage(argv[0])
  return retval
# end main()

if __name__ == '__main__':
  sys.exit(main(sys.argv))
# end if
