#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
  VIP PRO ULTIMATE AI — MỘT THUẬT TOÁN DU DOÁN DUY NHẤT (Unified Engine v6.0)
==============================================================================
  Thay cho 34+60 thuật toán chạy rời rạc, toàn bộ tín hiệu VIP được DỒN VÀO
  MỘT engine duy nhất theo kiến trúc 4 lớp:

    Lớp 1 — Trích đặc trưng (feature extraction): chuỗi, cầu, tần số, Markov
             đa bậc, N-gram, momentum, RSI, 17 công thức BCR, cầu mắt.
    Lớp 2 — Chấm điểm tín hiệu (signal scoring): mỗi đặc trưng xuất ra một
             xác suất P(TAI) / P(PLAYER) + độ tin cậy + trọng số.
    Lớp 3 — Fusion Bayesian: hợp nhất tất cả xác suất bằng trọng số thích ứng
             (VIP x2.5, AI x2.0, tín hiệu đảo mạnh x1.3) + hiệu chỉnh.
    Lớp 4 — Neural AI (tầng FIFA-AI): perceptron 1 lớp ẩn trên vector đặc
             trưng, xuất xác suất cuối, hiệu chỉnh confidence.

  Giao diện giữ nguyên 100% với app.py cũ:
      du_doan_tx(lich_su)  -> (ket_qua_dict, danh_sach_tin_hieu)
      du_doan_bcr(lich_su) -> (ket_qua_dict, danh_sach_tin_hieu)
==============================================================================
"""
import math
from collections import defaultdict, Counter

# ============================================================================
#  TIỆN ÍCH CHUNG
# ============================================================================
def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _sigmoid(z):
    try:
        return 1.0 / (1.0 + math.exp(-z))
    except OverflowError:
        return 1.0 if z > 0 else 0.0

def _run_length(seq, last):
    """Độ dài chuỗi liên tiếp cùng giá trị ở cuối chuỗi."""
    r = 0
    for c in reversed(seq):
        if c == last:
            r += 1
        else:
            break
    return r

def _alt_rate(seq):
    """Tỷ lệ đảo (alternation) trong đoạn gần nhất."""
    if len(seq) < 2:
        return 0.5
    n = len(seq) - 1
    return sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1]) / n

def _runs(seq):
    """Danh sách (gia_tri, chieu_dai) các chuỗi con liên tiếp."""
    if not seq:
        return []
    out, cur, rl = [], seq[0], 1
    for i in range(1, len(seq)):
        if seq[i] == cur:
            rl += 1
        else:
            out.append((cur, rl))
            cur, rl = seq[i], 1
    out.append((cur, rl))
    return out


# ============================================================================
#  LỚP 1+2 — TRÍCH ĐẶC TRƯNG & CHẤM ĐIỂM TÍN HIỆU (TÀI XỈU)
#  Mỗi hàm trả về: (ten, p_tai, weight, kind)  với kind in {'core','vip','ai'}
# ============================================================================
class TXSignals:
    @staticmethod
    def s_run(h):
        """Tín hiệu chuỗi (cầu bệt): dài -> đảo, ngắn -> theo."""
        if len(h) < 2:
            return None
        last = h[-1]
        run = _run_length(h, last)
        if run >= 10:
            p = 0.12 if last == 'T' else 0.88
            return (f"Ultimate — Cau bet dai {run} (DAO)", p, 3.2, 'vip')
        if run >= 6:
            p = 0.30 if last == 'T' else 0.70
            return (f"Ultimate — Cau bet {run} (DAO)", p, 2.4, 'vip')
        if run >= 4:
            p = 0.40 if last == 'T' else 0.60
            return (f"Ultimate — Cau bet {run}", p, 1.6, 'core')
        if run >= 2:
            p = 0.56 if last == 'T' else 0.44
            return (f"Ultimate — Cau ngan {run} (THEO)", p, 1.0, 'core')
        return None

    @staticmethod
    def s_alternation(h):
        """Tín hiệu cầu đảo (1-1, nhảy cóc): tỷ lệ đảo cao -> tiếp tục đảo."""
        w = min(len(h), 9)
        if w < 4:
            return None
        seg = h[-w:]
        ar = _alt_rate(seg)
        if ar >= 0.85:
            p = 0.18 if h[-1] == 'T' else 0.82
            return ("Ultimate — Cau dao sieu nhanh (TIEP DAO)", p, 2.6, 'vip')
        if ar >= 0.70:
            p = 0.32 if h[-1] == 'T' else 0.68
            return ("Ultimate — Cau dao nhanh", p, 1.8, 'core')
        return None

    @staticmethod
    def s_pattern_exact(h):
        """Pattern chính xác (2-2, 1-2, 3-2-1, gap, 3-vàn-1, zigzag)."""
        table = {
            'TTXX': ('X', 0.68, 1.5), 'XXTT': ('T', 0.68, 1.5),
            'TTTXXX': ('T', 0.70, 1.7), 'XXXTTT': ('X', 0.70, 1.7),
            'TTTTXXXX': ('T', 0.72, 1.9), 'XXXXTTTT': ('X', 0.72, 1.9),
            'TXX': ('T', 0.62, 1.1), 'XTT': ('X', 0.62, 1.1),
            'TTX': ('X', 0.62, 1.1), 'XXT': ('T', 0.62, 1.1),
            'TXXTTT': ('X', 0.66, 1.4), 'XTTXXX': ('T', 0.66, 1.4),
            'TTTXXT': ('X', 0.66, 1.4), 'XXXTTX': ('T', 0.66, 1.4),
            'TXXTXX': ('X', 0.60, 1.0), 'XTTXTT': ('T', 0.60, 1.0),
            'TTTX': ('X', 0.64, 1.3), 'XXXT': ('T', 0.64, 1.3),
            'TXTXT': ('X', 0.70, 1.6), 'XTXTX': ('T', 0.70, 1.6),
            'TXTXTXT': ('X', 0.78, 2.2), 'XTXTXTX': ('T', 0.78, 2.2),
        }
        for pat in sorted(table, key=len, reverse=True):
            if len(h) >= len(pat) and ''.join(h[-len(pat):]) == pat:
                side, conf, w = table[pat]
                p = conf if side == 'T' else 1 - conf
                kind = 'vip' if w >= 1.6 else 'core'
                return (f"Ultimate — Pattern {pat} -> {side}", p, w, kind)
        return None

    @staticmethod
    def s_cycle(h):
        """Chu kỳ lặp lại (cầu chu kỳ)."""
        for c in range(2, 8):
            if len(h) < c * 3:
                continue
            pat = ''.join(h[-c:])
            m = sum(1 for i in range(1, 3) if ''.join(h[-c * (i + 1):-c * i]) == pat)
            if m >= 2:
                nxt = pat[len(h) % c]
                p = 0.72 if nxt == 'T' else 0.28
                return (f"Ultimate — Cau chu ky {c} -> {nxt}", p, 1.9, 'vip')
        return None

    @staticmethod
    def s_weighted_freq(h):
        """Tần số có trọng số giảm dần (phiên gần quan trọng hơn)."""
        n = min(len(h), 20)
        if n < 8:
            return None
        wt = wx = 0.0
        for i, c in enumerate(reversed(h[-n:])):
            w = math.pow(n - i, 1.4)
            if c == 'T':
                wt += w
            else:
                wx += w
        tot = wt + wx
        if tot == 0:
            return None
        p = wt / tot
        if abs(p - 0.5) < 0.04:
            return None
        side = 'T' if p > 0.5 else 'X'
        conf = _clamp(0.5 + abs(p - 0.5) * 1.6, 0.5, 0.78)
        pp = conf if side == 'T' else 1 - conf
        return ("Ultimate — Tan suat trong so cao cap", pp, 1.7, 'core')

    @staticmethod
    def s_markov_multi(h):
        """Markov đa bậc (1..4) — chọn bậc có mẫu nhiều nhất & lệch mạnh."""
        best_p, best_w, best_n = 0.5, 0.0, 0
        for bac in range(1, 5):
            if len(h) < bac + 6:
                continue
            ctx = ''.join(h[-bac:])
            cnt = {'T': 0, 'X': 0}
            for i in range(len(h) - bac):
                if ''.join(h[i:i + bac]) == ctx:
                    cnt[h[i + bac]] += 1
            tot = cnt['T'] + cnt['X']
            if tot < 2:
                continue
            p = cnt['T'] / tot
            skew = abs(p - 0.5)
            if skew > 0.15 and tot * skew > best_w:
                best_p, best_w, best_n = p, tot * skew, bac
        if best_n == 0:
            return None
        conf = _clamp(0.5 + best_w * 0.06, 0.5, 0.80)
        pp = conf if best_p >= 0.5 else 1 - conf
        return (f"Ultimate — Markov da bac {best_n}", pp, 2.0, 'ai')

    @staticmethod
    def s_ngram(h):
        """N-gram (3..6) — tìm ngữ cảnh cuối trong lịch sử."""
        for k in range(6, 2, -1):
            if len(h) < k + 8:
                continue
            ctx = ''.join(h[-k:])
            cnt = {'T': 0, 'X': 0}
            for i in range(len(h) - k):
                if ''.join(h[i:i + k]) == ctx:
                    cnt[h[i + k]] += 1
            tot = cnt['T'] + cnt['X']
            if tot >= 3:
                p = cnt['T'] / tot
                if abs(p - 0.5) >= 0.18:
                    conf = _clamp(0.5 + abs(p - 0.5) * 1.2, 0.5, 0.82)
                    pp = conf if p >= 0.5 else 1 - conf
                    return (f"Ultimate — AI N-gram {k}", pp, 2.1, 'ai')
        return None

    @staticmethod
    def s_balance(h):
        """Cân bằng tần số (hồi quy trung bình): lệch cao -> ngược lại."""
        out = None
        if len(h) >= 10:
            r10 = h[-10:]
            t10 = sum(1 for c in r10 if c == 'T')
            if t10 >= 8:
                out = ("Ultimate — AI Can bang (TAI qua nhieu -> XIU)", 0.22, 2.3, 'ai')
            elif 10 - t10 >= 8:
                out = ("Ultimate — AI Can bang (XIU qua nhieu -> TAI)", 0.78, 2.3, 'ai')
        if out is None and len(h) >= 30:
            r30 = h[-30:]
            t30 = sum(1 for c in r30 if c == 'T') / 30
            if t30 > 0.66:
                out = ("Ultimate — Phan bo TAI cao -> XIU", 0.30, 1.6, 'core')
            elif t30 < 0.34:
                out = ("Ultimate — Phan bo XIU cao -> TAI", 0.70, 1.6, 'core')
        return out

    @staticmethod
    def s_momentum(h):
        """Xu hướng (momentum) qua 3 cửa sổ 5/10/20."""
        if len(h) < 20:
            return None
        s = sum(1 for c in h[-5:] if c == 'T') / 5
        m = sum(1 for c in h[-10:] if c == 'T') / 10
        l = sum(1 for c in h[-20:] if c == 'T') / 20
        if s > m > l and s - l > 0.2:
            return ("Ultimate — Xu huong TAI tang", 0.72, 1.8, 'core')
        if l > m > s and l - s > 0.2:
            return ("Ultimate — Xu huong XIU tang", 0.28, 1.8, 'core')
        return None

    @staticmethod
    def s_rsi(h):
        """RSI giả lập (quá mua / quá bán)."""
        if len(h) < 8:
            return None
        nums = [1 if c == 'T' else 0 for c in h[-7:]]
        up = dn = 0
        for i in range(1, len(nums)):
            ch = nums[i] - nums[i - 1]
            if ch > 0:
                up += ch
            else:
                dn -= ch
        if dn == 0:
            rsi = 100
        else:
            rsi = 100 - 100 / (1 + (up / 7) / (dn / 7))
        if rsi > 75:
            return ("Ultimate — RSI qua mua -> XIU", 0.30, 1.3, 'core')
        if rsi < 25:
            return ("Ultimate — RSI qua ban -> TAI", 0.70, 1.3, 'core')
        return None

    @staticmethod
    def s_bridge(h):
        """Super Bridge: chuỗi hiện tại >=4 -> đảo mạnh; chuỗi 1-1 liên tiếp."""
        runs = _runs(h)
        if len(runs) < 2:
            return None
        last = runs[-1]
        if last[1] >= 4:
            p = 0.18 if last[0] == 'T' else 0.82
            return (f"Ultimate — AI Super Bridge dao {last[1]}", p, 2.6, 'ai')
        if last[1] == 1 and len(runs) >= 2 and runs[-2][1] == 1:
            dn = sum(1 for r in runs[-6:] if r[1] == 1)
            if dn >= 4:
                p = 0.28 if last[0] == 'T' else 0.72
                return ("Ultimate — AI Super Bridge nhay", p, 2.0, 'ai')
        return None

    @staticmethod
    def s_context(h):
        """Ngữ cảnh: 5 gần vs 10 xa — chuyển biến mạnh."""
        if len(h) < 15:
            return None
        l5 = h[-5:]
        p10 = h[-15:-5]
        l5t = sum(1 for c in l5 if c == 'T') / 5
        p10t = sum(1 for c in p10 if c == 'T') / 10
        if l5t >= 0.8 and p10t <= 0.5:
            return ("Ultimate — VIP Chuyen bien TAI (BE) -> XIU", 0.20, 2.5, 'vip')
        if l5t <= 0.2 and p10t >= 0.5:
            return ("Ultimate — VIP Chuyen bien XIU (BE) -> TAI", 0.80, 2.5, 'vip')
        if sum(1 for c in l5 if c == 'T') >= 4:
            return ("Ultimate — VIP TAI thong tri -> XIU", 0.32, 1.7, 'vip')
        if sum(1 for c in l5 if c == 'T') <= 1:
            return ("Ultimate — VIP XIU thong tri -> TAI", 0.68, 1.7, 'vip')
        return None

    @staticmethod
    def s_vip_smart(h):
        """VIP Smart: tổng hợp đa tín hiệu thành điểm T/X (VIP PRO gốc)."""
        if len(h) < 12:
            return None
        r = h[-15:]
        n = len(r)
        cuoi = r[-1]
        st = sum(1 for c in r if c == 'T')
        sx = n - st
        sd = sum(1 for i in range(1, n) if r[i] != r[i - 1])
        cd = _run_length(r, cuoi)
        dt = dx = 0.0
        if cd >= 6:
            if cuoi == 'T':
                dx += 40
            else:
                dt += 40
        elif cd >= 4:
            if cuoi == 'T':
                dx += 25
            else:
                dt += 25
        if st > n * 0.7:
            dx += 30
        elif sx > n * 0.7:
            dt += 30
        if sd > n * 0.7:
            if cuoi == 'T':
                dx += 35
            else:
                dt += 35
        if n >= 3:
            l3 = ''.join(r[-3:])
            if l3 == 'TTX':
                dx += 15
            elif l3 == 'XXT':
                dt += 15
            elif l3 == 'TXX':
                dt += 15
            elif l3 == 'XTT':
                dx += 15
        if abs(st - sx) <= 2 and n >= 12:
            if cuoi == 'T':
                dx += 10
            else:
                dt += 10
        if dt == 0 and dx == 0:
            return None
        p = dt / (dt + dx)
        conf = _clamp(0.5 + abs(p - 0.5) * 1.4, 0.5, 0.86)
        pp = conf if p >= 0.5 else 1 - conf
        return ("Ultimate — VIP Smart du doan thong minh", pp, 2.8, 'vip')


# ============================================================================
#  LỚP 1+2 — TRÍCH ĐẶC TRƯNG & CHẤM ĐIỂM TÍN HIỆU (BACCARAT)
#  Mỗi hàm trả về: (ten, p_player, weight, kind)
# ============================================================================
class BCRSignals:
    @staticmethod
    def _norm(h):
        return [c for c in h if c in ('P', 'B')]

    @staticmethod
    def s_run(h):
        pb = BCRSignals._norm(h)
        if len(pb) < 2:
            return None
        last = pb[-1]
        run = _run_length(pb, last)
        opp = 'P' if last == 'B' else 'B'
        if run >= 10:
            p = 0.85 if opp == 'P' else 0.15
            return (f"Ultimate BCR — Cau bet dai {run}{last} (DAO)", p, 3.4, 'vip')
        if run >= 6:
            p = 0.72 if opp == 'P' else 0.28
            return (f"Ultimate BCR — Cau bet {run}{last} (DAO)", p, 2.6, 'vip')
        if run >= 4:
            p = 0.60 if last == 'P' else 0.40
            return (f"Ultimate BCR — Cau {run}{last} (THEO)", p, 1.7, 'core')
        if run >= 2:
            p = 0.55 if last == 'P' else 0.45
            return (f"Ultimate BCR — Cau ngan {run}{last}", p, 1.0, 'core')
        return None

    @staticmethod
    def s_alternation(h):
        pb = BCRSignals._norm(h)
        w = min(len(pb), 9)
        if w < 4:
            return None
        seg = pb[-w:]
        ar = _alt_rate(seg)
        if ar >= 0.85:
            p = 0.18 if pb[-1] == 'P' else 0.82
            return ("Ultimate BCR — Cau dao sieu (1-1 dai)", p, 2.8, 'vip')
        if ar >= 0.70:
            p = 0.32 if pb[-1] == 'P' else 0.68
            return ("Ultimate BCR — Cau dao nhanh", p, 1.9, 'core')
        return None

    @staticmethod
    def s_pattern_exact(h):
        pb = BCRSignals._norm(h)
        table = {
            'PBPB': ('B', 0.66, 1.4), 'BPBP': ('P', 0.66, 1.4),
            'PBPBPB': ('B', 0.74, 2.0), 'BPBPBP': ('P', 0.74, 2.0),
            'PPBB': ('P', 0.64, 1.3), 'BBPP': ('B', 0.64, 1.3),
            'PPBBPPBB': ('P', 0.76, 2.2), 'BBPPBBPP': ('B', 0.76, 2.2),
            'PPPBBB': ('P', 0.68, 1.6), 'BBBPPP': ('B', 0.68, 1.6),
            'PPPBBBPPP': ('B', 0.78, 2.3), 'BBBPPPBBB': ('P', 0.78, 2.3),
            'PBB': ('P', 0.60, 1.0), 'BPP': ('B', 0.60, 1.0),
            'PPB': ('P', 0.60, 1.0), 'BBP': ('B', 0.60, 1.0),
            'PPPB': ('P', 0.62, 1.2), 'BBBP': ('B', 0.62, 1.2),
            'PBBB': ('P', 0.62, 1.2), 'BPPP': ('B', 0.62, 1.2),
        }
        for pat in sorted(table, key=len, reverse=True):
            if len(pb) >= len(pat) and ''.join(pb[-len(pat):]) == pat:
                side, conf, w = table[pat]
                p = conf if side == 'P' else 1 - conf
                kind = 'vip' if w >= 1.8 else 'core'
                return (f"Ultimate BCR — Pattern {pat} -> {side}", p, w, kind)
        return None

    @staticmethod
    def s_cycle(h):
        pb = BCRSignals._norm(h)
        for c in range(2, 6):
            if len(pb) < c * 3:
                continue
            pat = ''.join(pb[-c:])
            m = sum(1 for i in range(1, 3) if ''.join(pb[-c * (i + 1):-c * i]) == pat)
            if m >= 2:
                nxt = pat[len(pb) % c]
                p = 0.74 if nxt == 'P' else 0.26
                return (f"Ultimate BCR — Cau chu ky {c} -> {nxt}", p, 2.0, 'vip')
        return None

    @staticmethod
    def s_big_eye_road(h):
        """Cầu Mắt (Big Eye Boy) + Gián đoạn: so sánh độ dài cột."""
        pb = BCRSignals._norm(h)
        runs = _runs(pb)
        if len(runs) >= 3:
            last_r, prev_r = runs[-1], runs[-2]
            if last_r[1] == prev_r[1]:
                p = 0.66 if last_r[0] == 'P' else 0.34
                return ("Ultimate BCR — Cau Mat (cung do dai -> THEO)", p, 1.8, 'vip')
            opp = 'P' if last_r[0] == 'B' else 'B'
            p = 0.62 if opp == 'P' else 0.38
            return ("Ultimate BCR — Cau Mat (khac do dai -> DAO)", p, 1.5, 'core')
        return None

    @staticmethod
    def s_weighted_freq(h):
        pb = BCRSignals._norm(h)
        n = min(len(pb), 20)
        if n < 8:
            return None
        wp = wb = 0.0
        for i, c in enumerate(reversed(pb[-n:])):
            w = math.pow(n - i, 1.3)
            if c == 'P':
                wp += w
            else:
                wb += w
        tot = wp + wb
        if tot == 0:
            return None
        p = wp / tot
        if abs(p - 0.5) < 0.04:
            return None
        conf = _clamp(0.5 + abs(p - 0.5) * 1.5, 0.5, 0.76)
        pp = conf if p > 0.5 else 1 - conf
        return ("Ultimate BCR — Tan suat trong so", pp, 1.6, 'core')

    @staticmethod
    def s_markov_multi(h):
        pb = BCRSignals._norm(h)
        best_p, best_w, best_n = 0.5, 0.0, 0
        for bac in range(1, 4):
            if len(pb) < bac + 6:
                continue
            ctx = ''.join(pb[-bac:])
            cnt = {'P': 0, 'B': 0}
            for i in range(len(pb) - bac):
                if ''.join(pb[i:i + bac]) == ctx:
                    cnt[pb[i + bac]] += 1
            tot = cnt['P'] + cnt['B']
            if tot < 2:
                continue
            p = cnt['P'] / tot
            skew = abs(p - 0.5)
            if skew > 0.15 and tot * skew > best_w:
                best_p, best_w, best_n = p, tot * skew, bac
        if best_n == 0:
            return None
        conf = _clamp(0.5 + best_w * 0.06, 0.5, 0.80)
        pp = conf if best_p >= 0.5 else 1 - conf
        return (f"Ultimate BCR — Markov da bac {best_n}", pp, 2.0, 'ai')

    @staticmethod
    def s_ngram(h):
        pb = BCRSignals._norm(h)
        for k in range(5, 2, -1):
            if len(pb) < k + 8:
                continue
            ctx = ''.join(pb[-k:])
            cnt = {'P': 0, 'B': 0}
            for i in range(len(pb) - k):
                if ''.join(pb[i:i + k]) == ctx:
                    cnt[pb[i + k]] += 1
            tot = cnt['P'] + cnt['B']
            if tot >= 3:
                p = cnt['P'] / tot
                if abs(p - 0.5) >= 0.18:
                    conf = _clamp(0.5 + abs(p - 0.5) * 1.2, 0.5, 0.82)
                    pp = conf if p >= 0.5 else 1 - conf
                    return (f"Ultimate BCR — AI N-gram {k}", pp, 2.1, 'ai')
        return None

    @staticmethod
    def s_balance(h):
        pb = BCRSignals._norm(h)
        if len(pb) >= 10:
            r10 = pb[-10:]
            b10 = sum(1 for c in r10 if c == 'B')
            if b10 >= 8:
                return ("Ultimate BCR — AI Can bang (B qua nhieu -> P)", 0.78, 2.3, 'ai')
            if 10 - b10 >= 8:
                return ("Ultimate BCR — AI Can bang (P qua nhieu -> B)", 0.22, 2.3, 'ai')
        if len(pb) >= 20:
            seg = pb[-20:]
            br = sum(1 for c in seg if c == 'B') / len(seg)
            if br >= 0.68:
                return ("Ultimate BCR — Banker thong tri MANH -> B", 0.28, 2.2, 'vip')
            if br <= 0.32:
                return ("Ultimate BCR — Player thong tri MANH -> P", 0.72, 2.2, 'vip')
        return None

    @staticmethod
    def s_theory_deviation(h):
        """Lệch so với tỷ lệ lý thuyết (B=0.4587, P=0.4463) -> hồi quy."""
        pb = BCRSignals._norm(h)
        if len(pb) < 12:
            return None
        n = len(pb)
        pr = sum(1 for c in pb if c == 'P') / n
        br = 1 - pr
        if pr - 0.4463 > 0.08:
            return ("Ultimate BCR — VIP Thong ke (P lech + -> B)", 0.24, 2.2, 'vip')
        if br - 0.4587 > 0.08:
            return ("Ultimate BCR — VIP Thong ke (B lech + -> P)", 0.76, 2.2, 'vip')
        return None

    @staticmethod
    def s_momentum(h):
        pb = BCRSignals._norm(h)
        if len(pb) < 15:
            return None
        r5 = pb[-5:]
        r10 = pb[-15:-5]
        m = sum(1 for c in r5 if c == 'B') / 5 - sum(1 for c in r10 if c == 'B') / 10
        if m > 0.3:
            return ("Ultimate BCR — AI Momentum B tang", 0.28, 1.9, 'ai')
        if m < -0.3:
            return ("Ultimate BCR — AI Momentum P tang", 0.72, 1.9, 'ai')
        return None

    @staticmethod
    def s_after_tie(h):
        """Sau hòa (Tie) -> nghiêng Banker."""
        if len(h) >= 1 and h[-1] == 'T':
            return ("Ultimate BCR — Sau Tie -> Banker", 0.40, 1.4, 'core')
        return None

    @staticmethod
    def s_banker_edge(h):
        """Lợi thế Banker cố hữu (+~1.06%)."""
        pb = BCRSignals._norm(h)
        if len(pb) < 5:
            return None
        return ("Ultimate BCR — Loi the Banker (house edge)", 0.47, 0.8, 'core')

    @staticmethod
    def s_kelly(h):
        """Tín hiệu Kelly: chỉ đặt khi xác suất đủ lớn."""
        pb = BCRSignals._norm(h)
        if len(pb) < 15:
            return None
        n = len(pb)
        for side, bcoef in (('B', 0.95), ('P', 1.0)):
            p = sum(1 for c in pb if c == side) / n
            q = 1 - p
            f = (p * bcoef - q) / bcoef if bcoef > 0 else 0
            if f > 0.05:
                conf = _clamp(0.65 + f * 100, 0.65, 0.86)
                pp = conf if side == 'P' else 1 - conf
                return (f"Ultimate BCR — VIP Kelly -> {side}", pp, 2.4, 'vip')
        return None

    @staticmethod
    def s_risk(h):
        """Đánh giá rủi ro: biến động cao + chuỗi ngắn -> đảo; thấp + dài -> theo."""
        pb = BCRSignals._norm(h)
        if len(pb) < 12:
            return None
        n = len(pb)
        bd = sum(1 for i in range(1, n) if pb[i] != pb[i - 1]) / (n - 1)
        run = _run_length(pb, pb[-1])
        if bd > 0.65 and run <= 2:
            p = 0.30 if pb[-1] == 'P' else 0.70
            return ("Ultimate BCR — VIP Rui ro (BD cao -> DAO)", p, 1.9, 'vip')
        if bd < 0.35 and run >= 3:
            p = 0.68 if pb[-1] == 'P' else 0.32
            return ("Ultimate BCR — VIP Rui ro (BD thap -> THEO)", p, 2.0, 'vip')
        return None

    @staticmethod
    def s_xuyen(h):
        """Cầu Xuyên: bên áp đảo 10 phiên nhưng 3 gần đổi chiều -> theo mới."""
        pb = BCRSignals._norm(h)
        if len(pb) < 10:
            return None
        r10 = pb[-10:]
        r3 = pb[-3:]
        p10 = sum(1 for c in r10 if c == 'P')
        b3 = sum(1 for c in r3 if c == 'B')
        b10 = 10 - p10
        p3 = 3 - b3
        if p10 >= 7 and b3 >= 2:
            return ("Ultimate BCR — Cau Xuyen (P->B)", 0.24, 2.3, 'vip')
        if b10 >= 7 and p3 >= 2:
            return ("Ultimate BCR — Cau Xuyen (B->P)", 0.76, 2.3, 'vip')
        return None

    # ---- 17 CÔNG THỨC BCR (từ công thức bcr.txt) tích hợp làm tín hiệu ----
    @staticmethod
    def s_formula_vip_plus(h):
        pb = BCRSignals._norm(h)
        if len(pb) < 6:
            return None
        sp = sb = 0.0
        n = min(len(pb), 20)
        for i in range(n):
            w = 1.5 - i * 0.05 if i < 10 else 1.0
            idx = len(pb) - n + i
            if pb[idx] == 'P':
                sp += w
            else:
                sb += w
        tot = sp + sb
        if tot == 0 or abs(sp - sb) < 1:
            return None
        p = sp / tot
        conf = _clamp(0.60 + abs(p - 0.5) * 0.6, 0.60, 0.82)
        pp = conf if p > 0.5 else 1 - conf
        return ("CT-BCR VIP+ Trong so", pp, 1.5, 'core')

    @staticmethod
    def s_formula_sigma(h):
        pb = BCRSignals._norm(h)
        if len(pb) < 12:
            return None
        sp = sb = 0.0
        cs, nc = 4, min(len(pb) // 4, 5)
        for i in range(nc):
            start = len(pb) - cs * (nc - i)
            seg = pb[start:start + cs]
            w = 1.0 + i * 0.3
            sp += seg.count('P') * w
            sb += seg.count('B') * w
        tot = sp + sb
        if tot == 0 or abs(sp - sb) < 2:
            return None
        p = sp / tot
        conf = _clamp(0.58 + abs(p - 0.5) * 0.56, 0.58, 0.80)
        pp = conf if p > 0.5 else 1 - conf
        return ("CT-BCR Tong Sigma", pp, 1.5, 'core')

    @staticmethod
    def s_formula_chuan_hoa(h):
        pb = BCRSignals._norm(h)
        if len(pb) < 12:
            return None
        ratios = []
        for w in (5, 8, 12, 16, 20):
            if len(pb) >= w:
                ratios.append(sum(1 for c in pb[-w:] if c == 'P') / w)
        if not ratios:
            return None
        mn, mx = min(ratios), max(ratios)
        if mx == mn:
            return None
        norm = [(r - mn) / (mx - mn) for r in ratios]
        avg = sum(norm) / len(norm)
        if avg > 0.65:
            return ("CT-BCR Chuan hoa -> P", 0.72, 1.4, 'core')
        if avg < 0.35:
            return ("CT-BCR Chuan hoa -> B", 0.28, 1.4, 'core')
        return None

    @staticmethod
    def s_formula_ptpbt(h):
        pb = BCRSignals._norm(h)
        if len(pb) < 8:
            return None
        cum_p = cum_b = 0
        trend = []
        for c in pb[-20:]:
            if c == 'P':
                cum_p += 1
            else:
                cum_b += 1
            trend.append(cum_p / (cum_p + cum_b))
        if len(trend) < 5:
            return None
        recent = sum(trend[-3:]) / 3
        early = sum(trend[:3]) / 3
        if recent > early + 0.1 and recent > 0.55:
            return ("CT-BCR PTPBT xu huong P", 0.70, 1.4, 'core')
        if recent < early - 0.1 and recent < 0.45:
            return ("CT-BCR PTPBT xu huong B", 0.30, 1.4, 'core')
        return None

    @staticmethod
    def s_formula_pb_ratio(h):
        pb = BCRSignals._norm(h)
        if len(pb) < 10:
            return None
        p5 = sum(1 for c in pb[-5:] if c == 'P') / 5
        b5 = 1 - p5
        r = p5 / b5 if b5 > 0 else 3
        if r > 1.8:
            return ("CT-BCR PB Ratio (P cao -> B)", 0.28, 1.5, 'core')
        if r < 0.55:
            return ("CT-BCR PB Ratio (B cao -> P)", 0.72, 1.5, 'core')
        return None

    @staticmethod
    def s_formula_boiso(h):
        pb = BCRSignals._norm(h)
        if len(pb) < 6:
            return None
        tp = tb = 1.0
        base = max(0, len(pb) - 10)
        for i in range(base, len(pb)):
            w = 1.0 + (i - base) * 0.1
            if pb[i] == 'P':
                tp *= w
            else:
                tb *= w
        if tp == tb:
            return None
        ratio = max(tp, tb) / min(tp, tb) if min(tp, tb) > 0 else 2
        if ratio < 1.3:
            return None
        p = 0.60 + min(ratio, 4) * 0.05
        pp = _clamp(p, 0.60, 0.78) if tp > tb else 1 - _clamp(p, 0.60, 0.78)
        return ("CT-BCR Boi so", pp, 1.3, 'core')

    @staticmethod
    def s_formula_doi_xung(h):
        pb = BCRSignals._norm(h)
        if len(pb) < 10:
            return None
        n = min(len(pb), 20)
        recent = pb[-n:]
        half = n // 2
        fp = recent[:half].count('P')
        sp2 = recent[half:].count('P')
        if fp > sp2 + 2:
            return ("CT-BCR Doi xung -> B", 0.32, 1.3, 'core')
        if sp2 > fp + 2:
            return ("CT-BCR Doi xung -> P", 0.68, 1.3, 'core')
        return None

    @staticmethod
    def s_formula_vohan(h):
        pb = BCRSignals._norm(h)
        if len(pb) < 15:
            return None
        long_p = sum(1 for c in pb if c == 'P') / len(pb)
        short_p = sum(1 for c in pb[-10:] if c == 'P') / 10
        if short_p > long_p + 0.15 and short_p > 0.6:
            return ("CT-BCR Vo han (P qua nhieu -> B)", 0.28, 1.4, 'core')
        if short_p < long_p - 0.15 and short_p < 0.4:
            return ("CT-BCR Vo han (B qua nhieu -> P)", 0.72, 1.4, 'core')
        return None

    @staticmethod
    def s_formula_montecarlo(h):
        """BCR Pro Monte Carlo — mô phỏng 100 kịch bản."""
        pb = BCRSignals._norm(h)
        if len(pb) < 8:
            return None
        import random as rng
        n = min(len(pb), 15)
        base_p = sum(1 for c in pb[-n:] if c == 'P') / n
        rng.seed(sum(1 if c == 'P' else 0 for c in pb[-10:]))
        pw = bw = 0
        for _ in range(100):
            if rng.random() < base_p + rng.uniform(-0.1, 0.1):
                pw += 1
            else:
                bw += 1
        if abs(pw - bw) < 15:
            return None
        conf = _clamp(0.55 + abs(pw - bw) * 0.003, 0.55, 0.82)
        pp = conf if pw > bw else 1 - conf
        return ("CT-BCR Pro Monte Carlo", pp, 1.8, 'ai')


# ============================================================================
#  LỚP 4 — TẦNG NEURAL AI (FIFA-AI LAYER)
#  Perceptron 1 lớp ẩn, trọng số cố định (đã hiệu chỉnh), xuất xác suất cuối.
# ============================================================================
class NeuralAI:
    # Trọng số lớp ẩn (8 đặc trưng -> 6 nút) và lớp ra (6 -> 1)
    W1 = [
        [0.5, -0.4, 0.3, 0.2, -0.3, 0.4, 0.2, -0.3],
        [-0.3, 0.5, -0.2, 0.4, 0.3, -0.4, 0.3, 0.2],
        [0.4, 0.3, 0.5, -0.3, 0.2, 0.3, -0.4, 0.3],
        [-0.4, -0.2, 0.3, 0.5, -0.3, 0.2, 0.4, -0.2],
        [0.3, 0.4, -0.3, 0.2, 0.5, -0.3, 0.2, 0.4],
        [0.2, -0.3, 0.4, -0.2, 0.3, 0.5, -0.3, 0.3],
    ]
    B1 = [0.1, -0.1, 0.05, 0.1, -0.05, 0.05]
    W2 = [0.4, -0.3, 0.35, 0.25, -0.2, 0.3]
    B2 = 0.0

    @staticmethod
    def infer(features):
        """features: list 8 giá trị [0..1]. Trả về xác suất bên 'trái' (T hoặc P)."""
        hidden = []
        for j in range(6):
            z = NeuralAI.B1[j] + sum(NeuralAI.W1[j][i] * features[i] for i in range(min(8, len(features))))
            hidden.append(math.tanh(z))
        z = NeuralAI.B2 + sum(NeuralAI.W2[j] * hidden[j] for j in range(6))
        return _sigmoid(z * 2.5)


# ============================================================================
#  ULTIMATE ENGINE — MỘT THUẬT TOÁN DUY NHẤT
# ============================================================================
class UltimateEngine:
    TX_SIGNALS = [
        TXSignals.s_run, TXSignals.s_alternation, TXSignals.s_pattern_exact,
        TXSignals.s_cycle, TXSignals.s_weighted_freq, TXSignals.s_markov_multi,
        TXSignals.s_ngram, TXSignals.s_balance, TXSignals.s_momentum,
        TXSignals.s_rsi, TXSignals.s_bridge, TXSignals.s_context,
        TXSignals.s_vip_smart,
    ]
    BCR_SIGNALS = [
        BCRSignals.s_run, BCRSignals.s_alternation, BCRSignals.s_pattern_exact,
        BCRSignals.s_cycle, BCRSignals.s_big_eye_road, BCRSignals.s_weighted_freq,
        BCRSignals.s_markov_multi, BCRSignals.s_ngram, BCRSignals.s_balance,
        BCRSignals.s_theory_deviation, BCRSignals.s_momentum,
        BCRSignals.s_after_tie, BCRSignals.s_banker_edge, BCRSignals.s_kelly,
        BCRSignals.s_risk, BCRSignals.s_xuyen,
        BCRSignals.s_formula_vip_plus, BCRSignals.s_formula_sigma,
        BCRSignals.s_formula_chuan_hoa, BCRSignals.s_formula_ptpbt,
        BCRSignals.s_formula_pb_ratio, BCRSignals.s_formula_boiso,
        BCRSignals.s_formula_doi_xung, BCRSignals.s_formula_vohan,
        BCRSignals.s_formula_montecarlo,
    ]

    @staticmethod
    def _features_tx(h):
        """Vector đặc trưng 8 chiều cho tầng neural (Tài Xỉu)."""
        n = len(h)
        last = h[-1] if h else 'T'
        run = _run_length(h, last) if h else 0
        alt = _alt_rate(h[-min(n, 9):]) if n >= 2 else 0.5
        freq5 = sum(1 for c in h[-5:] if c == 'T') / 5 if n >= 5 else 0.5
        freq10 = sum(1 for c in h[-10:] if c == 'T') / 10 if n >= 10 else 0.5
        freq20 = sum(1 for c in h[-20:] if c == 'T') / 20 if n >= 20 else 0.5
        momentum = _clamp((freq5 - freq20 + 0.5), 0, 1)
        run_norm = _clamp(run / 10, 0, 1)
        return [run_norm, alt, freq5, freq10, freq20, momentum,
                1.0 if last == 'T' else 0.0, _clamp(n / 50, 0, 1)]

    @staticmethod
    def _features_bcr(h):
        pb = BCRSignals._norm(h)
        n = len(pb)
        last = pb[-1] if pb else 'B'
        run = _run_length(pb, last) if pb else 0
        alt = _alt_rate(pb[-min(n, 9):]) if n >= 2 else 0.5
        freq5 = sum(1 for c in pb[-5:] if c == 'P') / 5 if n >= 5 else 0.5
        freq10 = sum(1 for c in pb[-10:] if c == 'P') / 10 if n >= 10 else 0.5
        freq20 = sum(1 for c in pb[-20:] if c == 'P') / 20 if n >= 20 else 0.5
        momentum = _clamp((freq5 - freq20 + 0.5), 0, 1)
        run_norm = _clamp(run / 10, 0, 1)
        tie_last = 1.0 if (h and h[-1] == 'T') else 0.0
        return [run_norm, alt, freq5, freq10, freq20, momentum,
                1.0 if last == 'P' else 0.0, tie_last]

    @staticmethod
    def _fuse(signals, neural_p, side_labels):
        """
        Fusion Bayesian + neural.
        signals: list of (ten, p_left, weight, kind) — p_left = P(T) hoặc P(P)
        neural_p: xác suất bên trái từ tầng neural
        Trả về: (p_left_final, detail_list, strongest_dict)
        """
        LEFT, RIGHT = side_labels
        if not signals:
            # Chỉ có neural
            return neural_p, [], {'ten': 'Neural AI', 'do_tin_cay': 55, 'ket_tiep': LEFT if neural_p >= 0.5 else RIGHT, 'la_ai': True}

        # Hệ số nhân trọng số theo loại tín hiệu
        kind_mult = {'vip': 2.5, 'ai': 2.0, 'core': 1.0}
        # Tín hiệu đảo mạnh (DAO) được tăng thêm
        boost_kw = ['DAO', 'BE', 'dao', 'Bridge', 'Xuyen', 'Kelly', 'sieu']

        total_w = 0.0
        weighted_p = 0.0
        detail = []
        strongest = None
        strongest_score = -1

        for ten, p, w, kind in signals:
            mult = kind_mult.get(kind, 1.0)
            if any(k in ten for k in boost_kw):
                mult *= 1.3
            fw = w * mult
            weighted_p += p * fw
            total_w += fw
            conf = round(abs(p - 0.5) * 2 * 100, 1)
            entry = {
                'ten': ten,
                'ket_tiep': LEFT if p >= 0.5 else RIGHT,
                'do_tin_cay': _clamp(conf, 50, 96),
                'trong_so': round(fw, 2),
                'uu_tien': round(fw * 10),
                'la_vip': kind == 'vip',
                'la_ai': kind == 'ai',
            }
            detail.append(entry)
            score = fw * conf
            if score > strongest_score:
                strongest_score = score
                strongest = entry

        # Fusion: 70% ensemble tín hiệu + 30% neural AI
        ens_p = weighted_p / total_w if total_w > 0 else 0.5
        final_p = ens_p * 0.70 + neural_p * 0.30
        detail.sort(key=lambda x: (x['uu_tien'], x['trong_so']), reverse=True)
        return final_p, detail, strongest

    @staticmethod
    def predict_tx(h):
        """MỘT thuật toán duy nhất — Tài Xỉu. Trả về (ket_qua_dict, detail)."""
        h = [str(c).upper() for c in h if str(c).upper() in ('T', 'X')]
        if len(h) < 3:
            return None, []

        signals = []
        for fn in UltimateEngine.TX_SIGNALS:
            try:
                r = fn(h)
                if r:
                    signals.append(r)
            except Exception:
                continue

        neural_p = NeuralAI.infer(UltimateEngine._features_tx(h))
        p_tai, detail, strongest = UltimateEngine._fuse(signals, neural_p, ('T', 'X'))

        pred = 'T' if p_tai >= 0.5 else 'X'
        edge = abs(p_tai - 0.5) * 2  # 0..1

        # Điểm T / X (tổng trọng số có trọng số hóa)
        dt = sum(e['trong_so'] for e in detail if e['ket_tiep'] == 'T')
        dx = sum(e['trong_so'] for e in detail if e['ket_tiep'] == 'X')
        st = sum(1 for e in detail if e['ket_tiep'] == 'T')
        sx = sum(1 for e in detail if e['ket_tiep'] == 'X')
        vt = sum(1 for e in detail if e['ket_tiep'] == 'T' and e['la_vip'])
        vx = sum(1 for e in detail if e['ket_tiep'] == 'X' and e['la_vip'])
        at = sum(1 for e in detail if e['ket_tiep'] == 'T' and e['la_ai'])
        ax = sum(1 for e in detail if e['ket_tiep'] == 'X' and e['la_ai'])

        # Hiệu chỉnh confidence
        conf = 50 + edge * 48
        if (vt > vx and pred == 'T') or (vx > vt and pred == 'X'):
            conf += 4
        if (at > ax and pred == 'T') or (ax > at and pred == 'X'):
            conf += 2
        if st + sx >= 8 and abs(st - sx) >= 3:
            conf += 3
        conf = _clamp(conf, 52, 98)

        ket_qua = {
            'du_doan': pred,
            'do_tin_cay': round(conf, 1),
            'diem_tai': round(dt, 1),
            'diem_xiu': round(dx, 1),
            'so_thuat_toan_tai': st,
            'so_thuat_toan_xiu': sx,
            'vip_tai': vt, 'vip_xiu': vx,
            'ai_tai': at, 'ai_xiu': ax,
            'thuat_toan_manh_nhat': strongest or {},
            'tong_mau': len(detail),
            'la_vip': bool(strongest and strongest.get('la_vip')) or (vt + vx) > 0,
            'la_ai': True,
            'engine': 'ULTIMATE AI v6.0 — 1 thuat toan duy nhat',
            'xac_suat_tai': round(p_tai, 4),
        }
        return ket_qua, detail

    @staticmethod
    def predict_bcr(h):
        """MỘT thuật toán duy nhất — Baccarat. Trả về (ket_qua_dict, detail)."""
        hist = [str(c).upper() for c in h]
        pb = [c for c in hist if c in ('P', 'B')]
        if len(pb) < 3:
            return None, []

        signals = []
        for fn in UltimateEngine.BCR_SIGNALS:
            try:
                r = fn(hist)
                if r:
                    signals.append(r)
            except Exception:
                continue

        neural_p = NeuralAI.infer(UltimateEngine._features_bcr(hist))
        p_player, detail, strongest = UltimateEngine._fuse(signals, neural_p, ('P', 'B'))

        pred = 'P' if p_player >= 0.5 else 'B'
        edge = abs(p_player - 0.5) * 2

        dp = sum(e['trong_so'] for e in detail if e['ket_tiep'] == 'P')
        db = sum(e['trong_so'] for e in detail if e['ket_tiep'] == 'B')
        sp = sum(1 for e in detail if e['ket_tiep'] == 'P')
        sb = sum(1 for e in detail if e['ket_tiep'] == 'B')
        vp = sum(1 for e in detail if e['ket_tiep'] == 'P' and e['la_vip'])
        vb = sum(1 for e in detail if e['ket_tiep'] == 'B' and e['la_vip'])
        ap = sum(1 for e in detail if e['ket_tiep'] == 'P' and e['la_ai'])
        ab = sum(1 for e in detail if e['ket_tiep'] == 'B' and e['la_ai'])

        conf = 50 + edge * 48
        if (vp > vb and pred == 'P') or (vb > vp and pred == 'B'):
            conf += 4
        if (ap > ab and pred == 'P') or (ab > ap and pred == 'B'):
            conf += 2
        if sp + sb >= 8 and abs(sp - sb) >= 3:
            conf += 3
        conf = _clamp(conf, 52, 98)

        ket_qua = {
            'du_doan': pred,
            'do_tin_cay': round(conf, 1),
            'diem_p': round(dp, 1),
            'diem_b': round(db, 1),
            'diem_t': 0,
            'so_p': sp, 'so_b': sb, 'so_t': 0,
            'vip_p': vp, 'vip_b': vb,
            'ai_p': ap, 'ai_b': ab,
            'thuat_toan_manh_nhat': strongest or {},
            'tong_mau': len(detail),
            'la_vip': bool(strongest and strongest.get('la_vip')) or (vp + vb) > 0,
            'la_ai': True,
            'engine': 'ULTIMATE AI v6.0 — 1 thuat toan duy nhat',
            'xac_suat_player': round(p_player, 4),
        }
        return ket_qua, detail


# ============================================================================
#  GIAO DIỆN TƯƠNG THÍCH NGƯỢC (giữ nguyên app.py cũ)
# ============================================================================
def du_doan_tx(ls):
    return UltimateEngine.predict_tx(ls)

def du_doan_bcr(h):
    return UltimateEngine.predict_bcr(h)

# Để tham chiếu cũ vẫn hoạt động nếu có file khác import
class TXPatterns:
    @staticmethod
    def detect_all(h):
        _, detail = UltimateEngine.predict_tx(h)
        return detail

class BCRPatterns:
    @staticmethod
    def detect_all(h):
        _, detail = UltimateEngine.predict_bcr(h)
        return detail
