#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 API CLIENT MODULE - VIP PRO WEB v6.0 ULTIMATE
50+ Tool Tài Xỉu + Baccarat — API mới nhất
(Mở rộng từ 21 tool gốc: thêm 789club, F8bet, New88, Jun88, Hi88, 388bet,
 King88, M88, V9bet, FB88, 12bet, Tiger88, Red88, Go88, VK789, FV88...)
"""
import time
import urllib3
import requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()

# ═══════════════════════════════════════════════
# API KEY dùng chung (kwinstore platform)
# ═══════════════════════════════════════════════
_KW_KEY = "6cd333eb6f42c778fb6ecbfd6fe8f14337f376d8b7fca424"

def _kw(slug, game):
    return f"https://kwinstore.com/{slug}/{game}/history/{_KW_KEY}"

# ═══════════════════════════════════════════════
# CẤU HÌNH 50+ TOOL TÀI XỈU
#   loai: TX (hũ/thường), MD5, SICBO
# ═══════════════════════════════════════════════
TOOLS_CONFIG = {
    # --- 21 TOOL GỐC ---
    '68gb_hu':   {'name': '68GB Hũ',    'full_name': '68GB - Tài Xỉu Hũ',   'nhom': '68GB',   'loai': 'TX',    'api_url': _kw('68gamebip','tx'),     'parser': 'kwinstore'},
    '68gb_md5':  {'name': '68GB MD5',   'full_name': '68GB - Tài Xỉu MD5',  'nhom': '68GB',   'loai': 'MD5',   'api_url': _kw('68gamebip','md5'),    'parser': 'kwinstore'},
    'b52_hu':    {'name': 'B52 Hũ',     'full_name': 'B52 - Tài Xỉu Hũ',    'nhom': 'B52',    'loai': 'TX',    'api_url': _kw('b52','hu'),           'parser': 'kwinstore'},
    'b52_md5':   {'name': 'B52 MD5',    'full_name': 'B52 - Tài Xỉu MD5',   'nhom': 'B52',    'loai': 'MD5',   'api_url': _kw('b52','md5'),          'parser': 'kwinstore'},
    'b52_sicbo': {'name': 'B52 Sicbo',  'full_name': 'B52 - Sicbo Tài Xỉu', 'nhom': 'B52',    'loai': 'SICBO', 'api_url': _kw('b52','sicbo'),        'parser': 'kwinstore_sicbo'},
    'hit_hu':    {'name': 'HitClub Hũ', 'full_name': 'HitClub - Tài Xỉu Hũ','nhom': 'HITCLUB','loai': 'TX',    'api_url': _kw('hitclub','tx'),       'parser': 'kwinstore'},
    'hit_md5':   {'name': 'HitClub MD5','full_name': 'HitClub - Tài Xỉu MD5','nhom':'HITCLUB','loai': 'MD5',   'api_url': _kw('hitclub','md5'),      'parser': 'kwinstore'},
    'hit_sicbo': {'name': 'HitClub Sicbo','full_name':'HitClub - Sicbo TX', 'nhom': 'HITCLUB','loai': 'SICBO', 'api_url': _kw('hitclub','sicbo'),    'parser': 'kwinstore_sicbo'},
    'max789_hu': {'name': 'Max789 Hũ',  'full_name': 'Max789 - Tài Xỉu Hũ', 'nhom': 'MAX789', 'loai': 'TX',    'api_url': _kw('max789','tx'),        'parser': 'kwinstore'},
    'max789_md5':{'name': 'Max789 MD5', 'full_name': 'Max789 - Tài Xỉu MD5','nhom': 'MAX789', 'loai': 'MD5',   'api_url': _kw('max789','md5'),       'parser': 'kwinstore'},
    'rikvip_hu': {'name': 'Rikvip Hũ',  'full_name': 'Rikvip - Tài Xỉu Hũ', 'nhom': 'RIKVIP', 'loai': 'TX',    'api_url': _kw('rikvip','tx'),        'parser': 'kwinstore'},
    'rikvip_md5':{'name': 'Rikvip MD5', 'full_name': 'Rikvip - Tài Xỉu MD5','nhom': 'RIKVIP', 'loai': 'MD5',   'api_url': _kw('rikvip','md5'),       'parser': 'kwinstore'},
    'rikvip_sicbo':{'name':'Rikvip Sicbo','full_name':'Rikvip - Sicbo TX',  'nhom': 'RIKVIP', 'loai': 'SICBO', 'api_url': _kw('rikvip','sicbo'),     'parser': 'kwinstore_sicbo'},
    'sumclub_hu':{'name': 'SumClub Hũ', 'full_name': 'SumClub - Tài Xỉu Hũ','nhom': 'SUMCLUB','loai': 'TX',    'api_url': _kw('sumclub','tx'),       'parser': 'kwinstore'},
    'sumclub_md5':{'name':'SumClub MD5','full_name':'SumClub - Tài Xỉu MD5','nhom': 'SUMCLUB','loai': 'MD5',   'api_url': _kw('sumclub','md5'),      'parser': 'kwinstore'},
    'sunwin_tx': {'name': 'Sunwin TX',  'full_name': 'Sunwin - Tài Xỉu Thường','nhom':'SUNWIN','loai': 'TX',   'api_url': _kw('sunwin','tx'),        'parser': 'kwinstore'},
    'sunwin_sicbo':{'name':'Sunwin Sicbo','full_name':'Sunwin - Sicbo TX',  'nhom': 'SUNWIN', 'loai': 'SICBO', 'api_url': _kw('sunwin','sicbo'),     'parser': 'kwinstore_sicbo'},
    'lc79_hu':   {'name': 'LC79 Hũ',    'full_name': 'LC79 - Tài Xỉu Hũ',   'nhom': 'LC79',   'loai': 'TX',    'api_url': _kw('lc79','tx'),          'parser': 'kwinstore'},
    'lc79_md5':  {'name': 'LC79 MD5',   'full_name': 'LC79 - Tài Xỉu MD5',  'nhom': 'LC79',   'loai': 'MD5',   'api_url': _kw('lc79','md5'),         'parser': 'kwinstore'},
    'betvip_hu': {'name': 'BETVIP Hũ',  'full_name': 'BETVIP - Tài Xỉu Hũ', 'nhom': 'BETVIP', 'loai': 'TX',    'api_url': 'https://wtx.macminim6.online/v1/tx/sessions',       'parser': 'tele68'},
    'betvip_md5':{'name': 'BETVIP MD5', 'full_name': 'BETVIP - Tài Xỉu MD5','nhom': 'BETVIP', 'loai': 'MD5',   'api_url': 'https://wtxmd52.macminim6.online/v1/txmd5/sessions','parser': 'tele68'},
    # --- TOOL MỚI THÊM (cùng nền tảng kwinstore) ---
    '789club_hu':  {'name': '789Club Hũ',  'full_name': '789Club - Tài Xỉu Hũ',  'nhom': '789CLUB', 'loai': 'TX',    'api_url': _kw('789club','tx'),    'parser': 'kwinstore'},
    '789club_md5': {'name': '789Club MD5', 'full_name': '789Club - Tài Xỉu MD5', 'nhom': '789CLUB', 'loai': 'MD5',   'api_url': _kw('789club','md5'),   'parser': 'kwinstore'},
    '789club_sicbo':{'name':'789Club Sicbo','full_name':'789Club - Sicbo TX',    'nhom': '789CLUB', 'loai': 'SICBO', 'api_url': _kw('789club','sicbo'), 'parser': 'kwinstore_sicbo'},
    'f8bet_hu':    {'name': 'F8bet Hũ',    'full_name': 'F8bet - Tài Xỉu Hũ',    'nhom': 'F8BET',   'loai': 'TX',    'api_url': _kw('f8bet','tx'),      'parser': 'kwinstore'},
    'f8bet_md5':   {'name': 'F8bet MD5',   'full_name': 'F8bet - Tài Xỉu MD5',   'nhom': 'F8BET',   'loai': 'MD5',   'api_url': _kw('f8bet','md5'),     'parser': 'kwinstore'},
    'f8bet_sicbo': {'name': 'F8bet Sicbo', 'full_name': 'F8bet - Sicbo Tài Xỉu', 'nhom': 'F8BET',   'loai': 'SICBO', 'api_url': _kw('f8bet','sicbo'),   'parser': 'kwinstore_sicbo'},
    'new88_hu':    {'name': 'New88 Hũ',    'full_name': 'New88 - Tài Xỉu Hũ',    'nhom': 'NEW88',   'loai': 'TX',    'api_url': _kw('new88','tx'),      'parser': 'kwinstore'},
    'new88_md5':   {'name': 'New88 MD5',   'full_name': 'New88 - Tài Xỉu MD5',   'nhom': 'NEW88',   'loai': 'MD5',   'api_url': _kw('new88','md5'),     'parser': 'kwinstore'},
    'jun88_hu':    {'name': 'Jun88 Hũ',    'full_name': 'Jun88 - Tài Xỉu Hũ',    'nhom': 'JUN88',   'loai': 'TX',    'api_url': _kw('jun88','tx'),      'parser': 'kwinstore'},
    'jun88_md5':   {'name': 'Jun88 MD5',   'full_name': 'Jun88 - Tài Xỉu MD5',   'nhom': 'JUN88',   'loai': 'MD5',   'api_url': _kw('jun88','md5'),     'parser': 'kwinstore'},
    'jun88_sicbo': {'name': 'Jun88 Sicbo', 'full_name': 'Jun88 - Sicbo Tài Xỉu', 'nhom': 'JUN88',   'loai': 'SICBO', 'api_url': _kw('jun88','sicbo'),   'parser': 'kwinstore_sicbo'},
    'hi88_hu':     {'name': 'Hi88 Hũ',     'full_name': 'Hi88 - Tài Xỉu Hũ',     'nhom': 'HI88',    'loai': 'TX',    'api_url': _kw('hi88','tx'),       'parser': 'kwinstore'},
    'hi88_md5':    {'name': 'Hi88 MD5',    'full_name': 'Hi88 - Tài Xỉu MD5',    'nhom': 'HI88',    'loai': 'MD5',   'api_url': _kw('hi88','md5'),      'parser': 'kwinstore'},
    '388bet_hu':   {'name': '388bet Hũ',   'full_name': '388bet - Tài Xỉu Hũ',   'nhom': '388BET',  'loai': 'TX',    'api_url': _kw('388bet','tx'),     'parser': 'kwinstore'},
    '388bet_md5':  {'name': '388bet MD5',  'full_name': '388bet - Tài Xỉu MD5',  'nhom': '388BET',  'loai': 'MD5',   'api_url': _kw('388bet','md5'),    'parser': 'kwinstore'},
    'king88_hu':   {'name': 'King88 Hũ',   'full_name': 'King88 - Tài Xỉu Hũ',   'nhom': 'KING88',  'loai': 'TX',    'api_url': _kw('king88','tx'),     'parser': 'kwinstore'},
    'king88_md5':  {'name': 'King88 MD5',  'full_name': 'King88 - Tài Xỉu MD5',  'nhom': 'KING88',  'loai': 'MD5',   'api_url': _kw('king88','md5'),    'parser': 'kwinstore'},
    'mx88_hu':     {'name': 'M88 Hũ',      'full_name': 'M88 (MX88) - Tài Xỉu Hũ','nhom': 'M88',    'loai': 'TX',    'api_url': _kw('mx88','tx'),       'parser': 'kwinstore'},
    'mx88_md5':    {'name': 'M88 MD5',     'full_name': 'M88 (MX88) - Tài Xỉu MD5','nhom':'M88',     'loai': 'MD5',   'api_url': _kw('mx88','md5'),      'parser': 'kwinstore'},
    'v9bet_hu':    {'name': 'V9bet Hũ',    'full_name': 'V9bet - Tài Xỉu Hũ',    'nhom': 'V9BET',   'loai': 'TX',    'api_url': _kw('v9bet','tx'),      'parser': 'kwinstore'},
    'v9bet_md5':   {'name': 'V9bet MD5',   'full_name': 'V9bet - Tài Xỉu MD5',   'nhom': 'V9BET',   'loai': 'MD5',   'api_url': _kw('v9bet','md5'),     'parser': 'kwinstore'},
    'fb88_hu':     {'name': 'FB88 Hũ',     'full_name': 'FB88 - Tài Xỉu Hũ',     'nhom': 'FB88',    'loai': 'TX',    'api_url': _kw('fb88','tx'),       'parser': 'kwinstore'},
    'fb88_md5':    {'name': 'FB88 MD5',    'full_name': 'FB88 - Tài Xỉu MD5',    'nhom': 'FB88',    'loai': 'MD5',   'api_url': _kw('fb88','md5'),      'parser': 'kwinstore'},
    '12bet_hu':    {'name': '12bet Hũ',    'full_name': '12bet - Tài Xỉu Hũ',    'nhom': '12BET',   'loai': 'TX',    'api_url': _kw('12bet','tx'),      'parser': 'kwinstore'},
    '12bet_md5':   {'name': '12bet MD5',   'full_name': '12bet - Tài Xỉu MD5',   'nhom': '12BET',   'loai': 'MD5',   'api_url': _kw('12bet','md5'),     'parser': 'kwinstore'},
    'tiger88_hu':  {'name': 'Tiger88 Hũ',  'full_name': 'Tiger88 - Tài Xỉu Hũ',  'nhom': 'TIGER88', 'loai': 'TX',    'api_url': _kw('tiger88','tx'),    'parser': 'kwinstore'},
    'tiger88_md5': {'name': 'Tiger88 MD5', 'full_name': 'Tiger88 - Tài Xỉu MD5', 'nhom': 'TIGER88', 'loai': 'MD5',   'api_url': _kw('tiger88','md5'),   'parser': 'kwinstore'},
    'red88_hu':    {'name': 'Red88 Hũ',    'full_name': 'Red88 - Tài Xỉu Hũ',    'nhom': 'RED88',   'loai': 'TX',    'api_url': _kw('red88','tx'),      'parser': 'kwinstore'},
    'red88_md5':   {'name': 'Red88 MD5',   'full_name': 'Red88 - Tài Xỉu MD5',   'nhom': 'RED88',   'loai': 'MD5',   'api_url': _kw('red88','md5'),     'parser': 'kwinstore'},
    'go88_hu':     {'name': 'Go88 Hũ',     'full_name': 'Go88 - Tài Xỉu Hũ',     'nhom': 'GO88',    'loai': 'TX',    'api_url': _kw('go88','tx'),       'parser': 'kwinstore'},
    'go88_md5':    {'name': 'Go88 MD5',    'full_name': 'Go88 - Tài Xỉu MD5',    'nhom': 'GO88',    'loai': 'MD5',   'api_url': _kw('go88','md5'),      'parser': 'kwinstore'},
    'vk789_hu':    {'name': 'VK789 Hũ',    'full_name': 'VK789 - Tài Xỉu Hũ',    'nhom': 'VK789',   'loai': 'TX',    'api_url': _kw('vk789','tx'),      'parser': 'kwinstore'},
    'vk789_md5':   {'name': 'VK789 MD5',   'full_name': 'VK789 - Tài Xỉu MD5',   'nhom': 'VK789',   'loai': 'MD5',   'api_url': _kw('vk789','md5'),     'parser': 'kwinstore'},
    'fv88_hu':     {'name': 'FV88 Hũ',     'full_name': 'FV88 - Tài Xỉu Hũ',     'nhom': 'FV88',    'loai': 'TX',    'api_url': _kw('fv88','tx'),       'parser': 'kwinstore'},
    'fv88_md5':    {'name': 'FV88 MD5',    'full_name': 'FV88 - Tài Xỉu MD5',    'nhom': 'FV88',    'loai': 'MD5',   'api_url': _kw('fv88','md5'),      'parser': 'kwinstore'},
}

# ═══════════════════════════════════════════════
# CHỈ GIỮ CÁC GAME CÓ API LINK (key mới)
# LC79, HITCLUB, MAX789 (TX + MD5) · SUNWIN (TX)
# ═══════════════════════════════════════════════
_KEEP = {'lc79_hu','lc79_md5','hit_hu','hit_md5','max789_hu','max789_md5','sunwin_tx'}
TOOLS_CONFIG = {k: v for k, v in TOOLS_CONFIG.items() if k in _KEEP}
# API Baccarat (60+ bàn)
BCR_API = "https://bcf-ayt4.onrender.com/sexy/all"

# Ảnh game — nhóm mới dùng lại ảnh có sẵn (an toàn, không 404)
GAME_IMAGES = {
    '68GB': 'https://i.ibb.co/S4TPspjJ/IMG-20260826-135222.jpg',
    'B52': 'https://i.ibb.co/BKtFRs37/IMG-20260826-135320.jpg',
    'HITCLUB': 'https://i.ibb.co/vxWppsF4/IMG-20260826-135300.jpg',
    'MAX789': 'https://i.ibb.co/Q7vN703F/IMG-20260826-135405.jpg',
    'RIKVIP': 'https://i.ibb.co/FLtmQzZJ/IMG-20260902-100653.jpg',
    'SUMCLUB': 'https://i.ibb.co/Q7vN703F/IMG-20260826-135405.jpg',
    'SUNWIN': 'https://i.ibb.co/S4TPspjJ/IMG-20260826-135222.jpg',
    'LC79': 'https://i.ibb.co/21g113nY/IMG-20260826-135238.jpg',
    'BETVIP': 'https://i.ibb.co/v68R7XYG/IMG-20260826-135348.jpg',
    'BACCARAT': 'https://i.ibb.co/WWMNJWCj/IMG-20260826-135430.jpg',
    # Nhóm mới — map lại ảnh có sẵn theo sắc thái
    '789CLUB': 'https://i.ibb.co/S4TPspjJ/IMG-20260826-135222.jpg',
    'F8BET':   'https://i.ibb.co/BKtFRs37/IMG-20260826-135320.jpg',
    'NEW88':   'https://i.ibb.co/vxWppsF4/IMG-20260826-135300.jpg',
    'JUN88':   'https://i.ibb.co/Q7vN703F/IMG-20260826-135405.jpg',
    'HI88':    'https://i.ibb.co/FLtmQzZJ/IMG-20260902-100653.jpg',
    '388BET':  'https://i.ibb.co/S4TPspjJ/IMG-20260826-135222.jpg',
    'KING88':  'https://i.ibb.co/BKtFRs37/IMG-20260826-135320.jpg',
    'M88':     'https://i.ibb.co/vxWppsF4/IMG-20260826-135300.jpg',
    'V9BET':   'https://i.ibb.co/Q7vN703F/IMG-20260826-135405.jpg',
    'FB88':    'https://i.ibb.co/FLtmQzZJ/IMG-20260902-100653.jpg',
    '12BET':   'https://i.ibb.co/21g113nY/IMG-20260826-135238.jpg',
    'TIGER88': 'https://i.ibb.co/v68R7XYG/IMG-20260826-135348.jpg',
    'RED88':   'https://i.ibb.co/S4TPspjJ/IMG-20260826-135222.jpg',
    'GO88':    'https://i.ibb.co/BKtFRs37/IMG-20260826-135320.jpg',
    'VK789':   'https://i.ibb.co/vxWppsF4/IMG-20260826-135300.jpg',
    'FV88':    'https://i.ibb.co/Q7vN703F/IMG-20260826-135405.jpg',
}

LOGO_URL = "https://i.postimg.cc/6Qgy45qM/IMG-20260821-091544.jpg"
QR_ZALOPAY = "https://i.postimg.cc/Y0KbjzYx/IMG-20260826-140021.jpg"

NHOM_TOOL = list(dict.fromkeys(cfg['nhom'] for cfg in TOOLS_CONFIG.values()))

# Cache
API_CACHE = {}
CACHE_TTL = 3

# ═══════════════════════════════════════════════
# PARSERS
# ═══════════════════════════════════════════════
def kq_to_char(r):
    if not r: return ''
    s = str(r).upper()
    if 'TAI' in s or s=='T' or 'TÀI' in s or 'BIG' in s or '大' in s: return 'T'
    if 'XIU' in s or s=='X' or 'XỈU' in s or 'SMALL' in s or '小' in s: return 'X'
    return ''

def find_list(obj):
    for k in ['data','Data','result','Result','list','List','items','Items',
              'history','History','sessions','Sessions','records','Records']:
        if k in obj:
            v=obj[k]
            if isinstance(v, list): return v
            if isinstance(v, dict):
                for k2 in ['list','List','items','Items','data','Data']:
                    if k2 in v and isinstance(v[k2], list): return v[k2]
    if 'data' in obj and isinstance(obj['data'], dict):
        return [obj['data']]
    for v in obj.values():
        if isinstance(v, list): return v
    return None

def parse_kwinstore(raw):
    arr = raw if isinstance(raw, list) else (find_list(raw) or [])
    out = []
    for p in arr:
        if not isinstance(p, dict): continue
        kq = ''
        for k in ['result','Result','kết quả','ket_qua','ketqua','kq','KQ','outcome','Outcome',
                  'type','Type','value','Value','big_small','tai_xiu','resultTruyenThong']:
            if k in p and p[k]:
                val = str(p[k])
                if val.lower() in ('đang chạy','đã có kết quả','pending','running','finished'): continue
                kq = val; break
        if not kq:
            d1=d2=d3=None
            for t1,t2,t3 in [('d1','d2','d3'),('xuc_xac_1','xuc_xac_2','xuc_xac_3'),
                            ('dice1','dice2','dice3'),('Dice1','Dice2','Dice3')]:
                if t1 in p and t2 in p and t3 in p:
                    d1,d2,d3=p.get(t1),p.get(t2),p.get(t3); break
            if d1 is None:
                for k in ['dices','Dices','dice','Dice','results','Results']:
                    if k in p and isinstance(p[k], list) and len(p[k])>=3:
                        d1,d2,d3=p[k][0],p[k][1],p[k][2]; break
            if d1 is not None:
                try:
                    tong=int(d1)+int(d2)+int(d3)
                    kq='TAI' if tong>10 else 'XIU'
                except: pass
        mp=''
        for k in ['session','Session','id','Id','ID','_id','round','Round','phiên','phien',
                  'code','Code','num','Num','number','Number','index','Index','gameNum']:
            if k in p and p[k]: mp=str(p[k]); break
        c=kq_to_char(kq)
        if c in ('T','X'):
            out.append({'ma_phien':mp,'ket_qua':c,'ket_qua_text':str(kq or '')})
    out.reverse()
    return out

def parse_kwinstore_sicbo(raw):
    arr = raw if isinstance(raw, list) else (find_list(raw) or [])
    out = []
    for p in arr:
        if not isinstance(p, dict): continue
        diem=None
        for k in ['score','Score','total','Total','sum','Sum','tong','Tong']:
            if k in p and p[k] is not None:
                try: diem=int(p[k]); break
                except: pass
        kq=''
        if diem is not None:
            if 4<=diem<=10: kq='XIU'
            elif 11<=diem<=17: kq='TAI'
            else: continue
        else:
            for k in ['result','Result','kq','KQ','outcome','Outcome','ket_qua','kết quả']:
                if k in p and p[k]: kq=p[k]; break
            if not kq:
                d1=d2=d3=None
                for t1,t2,t3 in [('d1','d2','d3'),('xuc_xac_1','xuc_xac_2','xuc_xac_3')]:
                    if t1 in p and t2 in p and t3 in p:
                        d1,d2,d3=p.get(t1),p.get(t2),p.get(t3); break
                if d1 is None:
                    for k in ['dices','Dices','faces','Faces','facesList','keyR']:
                        if k in p:
                            v=p[k]
                            if isinstance(v, list) and len(v)>=3:
                                d1,d2,d3=v[0],v[1],v[2]; break
                            if isinstance(v, str) and '-' in v:
                                try:
                                    parts=list(map(int,v.split('-')))
                                    if len(parts)>=3: d1,d2,d3=parts[0],parts[1],parts[2]; break
                                except: pass
                if d1 is not None:
                    try:
                        tong=int(d1)+int(d2)+int(d3)
                        if 4<=tong<=10: kq='XIU'
                        elif 11<=tong<=17: kq='TAI'
                        else: continue
                    except: pass
        mp=''
        for k in ['session','Session','id','Id','ID','round','Round','phiên','phien',
                  'gameNum','GameNum','code','Code']:
            if k in p and p[k]: mp=str(p[k]); break
        if mp.upper().startswith('S'): mp=mp[1:]
        c=kq_to_char(kq)
        if c in ('T','X'):
            ph={'ma_phien':mp,'ket_qua':c,'ket_qua_text':str(kq or '')}
            if diem is not None: ph['diem']=diem
            out.append(ph)
    out.reverse()
    return out

def parse_tele68(raw):
    arr = raw if isinstance(raw, list) else []
    if isinstance(raw, dict):
        if 'sessions' in raw and isinstance(raw['sessions'],list): arr=raw['sessions']
        elif 'data' in raw and isinstance(raw['data'],list): arr=raw['data']
        elif 'list' in raw and isinstance(raw['list'],list): arr=raw['list']
        else: arr=find_list(raw) or []
    out = []
    for p in arr:
        if not isinstance(p, dict): continue
        kq=''
        for k in ['result','big_small','tai_xiu','outcome','value','type','resultTruyenThong']:
            if k in p and p[k] is not None: kq=p[k]; break
        if not kq and 'total' in p and p['total'] is not None:
            try: kq='TAI' if int(p['total'])>10 else 'XIU'
            except: pass
        if not kq and 'dices' in p and isinstance(p['dices'], list) and len(p['dices'])>=3:
            try:
                tong=int(p['dices'][0])+int(p['dices'][1])+int(p['dices'][2])
                kq='TAI' if tong>10 else 'XIU'
            except: pass
        mp=''
        for k in ['id','session','session_id','round','code','number','num','_id']:
            if k in p and p[k] is not None: mp=str(p[k]); break
        c=kq_to_char(kq)
        if c in ('T','X'):
            out.append({'ma_phien':mp,'ket_qua':c,'ket_qua_text':str(kq or '')})
    out.reverse()
    return out

PARSERS = {'kwinstore': parse_kwinstore, 'kwinstore_sicbo': parse_kwinstore_sicbo, 'tele68': parse_tele68}

# ═══════════════════════════════════════════════
# API CALLS
# ═══════════════════════════════════════════════
def call_api(url, timeout=20):
    try:
        h={'Accept':'application/json','Cache-Control':'no-cache',
           'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
           'Origin':'https://kwinstore.com','Referer':'https://kwinstore.com/'}
        r=requests.get(url, timeout=timeout, headers=h, verify=False)
        if r.status_code==200: return r.json()
        return None
    except:
        return None

def get_tool_data(tid):
    if tid not in TOOLS_CONFIG: return None
    cfg=TOOLS_CONFIG[tid]
    now=time.time()
    if tid in API_CACHE and now-API_CACHE[tid]['time']<CACHE_TTL:
        return API_CACHE[tid]['data']
    raw=call_api(cfg['api_url'])
    pf=PARSERS.get(cfg['parser'], parse_kwinstore)
    ph=pf(raw) if raw else []
    ls=[p['ket_qua'] for p in ph]
    pc=ph[-1]['ma_phien'] if ph else ''
    res={'tool_id':tid,'name':cfg['name'],'full_name':cfg['full_name'],
         'nhom':cfg['nhom'],'loai':cfg['loai'],'lich_su':ls,
         'cac_phien':ph,'phien':pc,'so_phien':len(ph)}
    API_CACHE[tid]={'time':now,'data':res}
    return res

def get_bcr_data():
    now=time.time()
    cache_key='_bcr_all'
    if cache_key in API_CACHE and now-API_CACHE[cache_key]['time']<CACHE_TTL:
        return API_CACHE[cache_key]['data']
    try:
        raw=call_api(BCR_API, timeout=15)
        if not raw: return None
        tables=[]
        for item in raw:
            ban=item.get('ban','')
            cau=item.get('cau','')
            kq=item.get('ket_qua','')
            phien=item.get('phien',0)
            gio=item.get('time','')
            history=list(kq.upper())
            if not cau:
                pb=[c for c in history if c in ('P','B')]
                if len(pb)>=5:
                    dao=sum(1 for i in range(1,len(pb)) if pb[i]!=pb[i-1])
                    if dao/(len(pb)-1)>=0.7: cau='Cầu đảo'
                    else: cau='Cầu bình thường'
                else: cau='Chưa rõ'
            tables.append({'ban':ban,'cau':cau,'history':history,'phien':phien,'gio':gio,'so_phien':len(history)})
        def sort_key(b):
            ban=b['ban']
            try:
                if ban.startswith('C'): return (100,int(ban[1:]))
                return (0,int(ban))
            except: return (50,0)
        tables.sort(key=sort_key)
        API_CACHE[cache_key]={'time':now,'data':tables}
        return tables
    except:
        return None

def tools_by_group():
    g={}
    for tid,cfg in TOOLS_CONFIG.items():
        n=cfg['nhom']
        if n not in g: g[n]=[]
        g[n].append({'id':tid,'name':cfg['name'],'full_name':cfg['full_name'],'loai':cfg['loai']})
    return g
