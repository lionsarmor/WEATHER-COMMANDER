#!/usr/bin/env python3
"""Integrated native app regression checks using compiled 65C02 instructions."""
import json
import unittest
from pathlib import Path
from runtime_harness import Harness, ROOT, centered_bar

class RuntimeTests(unittest.TestCase):
 def test_every_view_and_centered_navigation(self):
  h=Harness()
  self.assertEqual(h.m[0x9805],0);self.assertTrue(h.m[0x980c])
  for page in range(12):
   h.m[0x9800]=page;h.run(0,'p8b_main:p8s_redraw')
   self.assertEqual(h.m[0],0)
   if page==10:continue
   for i,label in enumerate(['HOME','NATIONAL','REGIONAL','LOCAL','RADAR','FORECAST','CITIES','SETTINGS','ABOUT']):
    self.assertEqual(h.text(4+(12-len(label))//2,11+i*3,len(label)),label.encode())
    centered_bar(h,4,10+i*3,12,3)
  for step in range(5):
   h.m[0x9800]=10;h.m[0x981a]=step;h.run(0,'p8b_main:p8s_redraw')
   for rect in [(4,9,59,3),(64,9,12,3),(8,48,64,3),(8,54,20,3),(42,54,30,3)]:centered_bar(h,*rect)
 def test_country_switch_is_offline_and_transactional(self):
  h=Harness();h.m[0x981f]=1;h.run(0,'p8b_main:p8s_select_country')
  self.assertEqual((h.m[0x981e],h.m[0x9804],h.m[0x9805],h.m[0x9800]),(1,0,0,1))
  self.assertEqual(bytes(h.m[0x63e8:0x63f8]).rstrip(b'\0'),b'MANILA HOME')
  self.assertTrue(h.m[0x9821]);self.assertFalse(h.m[0x980e])
  h.m[0x981f]=0;h.run(0,'p8b_main:p8s_select_country')
  self.assertEqual(h.m[0x981e],0);self.assertTrue(h.m[0x9821])
  h.m[0x9804]=2;h.m[0x981f]=1
  h.hooks[(12,0xa006)]=lambda:(h.m.__setitem__(0x6a87,0),h.m.__setitem__(0x69c5,3))
  before=bytes(h.m[0x6000:0x6400]);h.run(0,'p8b_main:p8s_select_country')
  self.assertEqual(h.m[0x981e],0);self.assertEqual(h.m[0x9820],2)
  self.assertEqual(bytes(h.m[0x6000:0x6400]),before)
 def test_weather_commit_rejects_corrupt_or_partial_country(self):
  h=Harness();h.m[0x9804]=2
  good=bytearray(h.files['WCDMUS.BIN']);good[10:15]=bytes([126,9,10,14,30]);good[8:10]=((sum(good[6:8])+sum(good[10:]))&65535).to_bytes(2,'little')
  def response(raw):
   h.m[0x6400:0x6400+len(raw)]=raw;h.m[0x6a87]=1;h.m[0x6a84:0x6a86]=len(raw).to_bytes(2,'little')
  h.hooks[(12,0xa006)]=lambda:response(good)
  h.run(13,0xa003);self.assertEqual(h.m[0x9805],3)
  before=bytes(h.m[0x6000:0x6400])
  for offset in (15,33,34,42,44,50,51,54,55,354,355,633,634,872):
   bad=bytearray(good);bad[offset]=255;bad[8:10]=((sum(bad[6:8])+sum(bad[10:]))&65535).to_bytes(2,'little')
   h.hooks[(12,0xa006)]=lambda raw=bad:response(raw)
   h.run(13,0xa003);self.assertEqual(bytes(h.m[0x6000:0x6400]),before);self.assertEqual(h.m[0x9805],2)
  h.hooks[(12,0xa006)]=lambda:response(good[:-1]);h.run(13,0xa003)
  self.assertEqual(bytes(h.m[0x6000:0x6400]),before)
 def test_radar_cache_survives_http_scratch_and_age(self):
  h=Harness();h.run(15,0xa003);self.assertTrue(h.m[0x9821])
  header=bytes(h.m[0x7000:0x7010]);tilemap=bytes(h.m[0x89f0:0x9320])
  h.m[0x7000:0x9320]=[0xa5]*8992;h.m[0x9821]=0
  h.run(15,0xa00f)
  self.assertEqual(bytes(h.m[0x7000:0x7010]),header)
  self.assertEqual(bytes(h.m[0x89f0:0x9320]),tilemap)
  self.assertTrue(h.m[0x9821]);self.assertFalse(h.m[0x980e])
  h.clock=[126,12,31,23,59,0,0,4];h.run(15,0xa006);self.assertTrue(h.m[0x9821])
  h.m[0x9804]=2;h.run(15,0xa00f);self.assertFalse(h.m[0x9821]);self.assertFalse(h.m[0x980e])
 def test_preferences_roundtrip_checksum_and_legacy_migration(self):
  h=Harness();h.m[0x9802]=1;h.m[0x9803]=120;h.m[0x981e]=1;h.m[0x9804]=2
  h.m[0x9890:0x989c]=b'43.07305\0'.ljust(12,b'\0');h.m[0x989c:0x98a8]=b'-89.40123\0'.ljust(12,b'\0');h.m[0x98a8:0x98b8]=b'MADISON\0'.ljust(16,b'\0');h.m[0x98e0]=1
  locations=bytes(h.m[0x9890:0x98e2]);h.run(16,0xa006)
  self.assertTrue(h.m[0x980d]);saved=h.files['WCSETUP.BIN'];self.assertEqual(len(saved),100)
  h.m[0x9890:0x98e2]=[0]*82;h.m[0x981e]=0;h.run(16,0xa003)
  self.assertEqual(bytes(h.m[0x9890:0x98e2]),locations);self.assertEqual(h.m[0x981e],1)
  for offset in (2,4,6,8,16,98,99):
   bad=bytearray(saved);bad[offset]^=255;h.files['WCSETUP.BIN']=bad;h.m[0x9802]=0;h.run(16,0xa003);self.assertEqual(h.m[0x9802],0)
  bad=bytearray(saved);bad[16:28]=b'91.0\0'.ljust(12,b'\0');bad[98:100]=sum(bad[:98]).to_bytes(2,'little');h.files['WCSETUP.BIN']=bad;h.run(16,0xa003);self.assertEqual(h.m[0x9802],0)
  legacy=bytearray(144);legacy[:8]=bytes([87,83,2,1,60,1,1,3]);h.files['WCSETUP.BIN']=legacy;h.run(16,0xa003)
  self.assertEqual((h.m[0x9802],h.m[0x9804],h.m[0x9801]),(1,0,3))
  h.write_ok=False;h.run(16,0xa006);self.assertFalse(h.m[0x980d])
 def test_scheduler_and_controls_across_clock_wrap(self):
  h=Harness()
  for key,page in [(133,9),(137,6),(134,5),(138,4),(135,7),(72,0)]:h.key(key);self.assertEqual(h.m[0x9800],page)
  h.m[0x9801]=0;h.key(157);self.assertEqual(h.m[0x9801],9);h.key(29);self.assertEqual(h.m[0x9801],0)
  h.m[0x9800]=7;h.key(85);self.assertEqual(h.m[0x9802],1)
  h.word(0,'p8b_main:p8v_last_refresh',65000);cycles=h.m[0x9806]
  h.ticks=(65000+3599)&65535;h.run(0,'p8b_main:p8s_service_timers');self.assertEqual(h.m[0x9806],cycles)
  h.ticks=(65000+3600)&65535;h.run(0,'p8b_main:p8s_service_timers');self.assertEqual(h.m[0x9806],(cycles+1)&255)
 def test_failed_join_clears_secret_and_does_not_advance(self):
  h=Harness();h.set(12,'p8b_network_driver:p8v_modem_present',1);h.m[0x69c5]=3;h.m[0x69c0]=3
  h.m[0x6950:0x6955]=b'Home\0';h.m[0x6980:0x6987]=b'secret\0'
  h.hook(12,'p8b_network_driver:p8s_send_command',lambda:h.ay(0));h.run(12,0xa003)
  self.assertEqual(h.m[0x69c5],2);self.assertFalse(any(h.m[0x6980:0x69c0]))
 def test_failed_weather_setup_keeps_error_and_skips_radar_download(self):
  h=Harness();h.m[0x9800]=10;h.m[0x981a]=3;h.m[0x69c0]=6
  notice=b'HTTPS FAILED / CHECK TLS OR INTERNET\0'
  def failed_weather():
   h.m[0x9805]=2;h.m[0x69d0:0x69d0+len(notice)]=notice
  h.hooks[(13,0xa003)]=failed_weather
  h.hooks[(15,0xa003)]=lambda:self.fail('Weather failure must not start another radar download')
  h.run(0,'p8b_main:p8s_finish_wifi_action')
  self.assertEqual(h.m[0x981a],3)
  self.assertEqual(bytes(h.m[0x69d0:0x69d0+len(notice)]),notice)

if __name__=='__main__':unittest.main()
