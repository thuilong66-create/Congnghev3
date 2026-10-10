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

# ============================================================================
#  REGIME-AWARE TX ENSEMBLE — port từ server.js (Node/Fastify)
#  20 tín hiệu + 63 cầu mẫu + bảng PATTERN8 + phát hiện chế độ (regime)
#  Dùng làm 1 tín hiệu 'ai' trọng số cao trong UltimateEngine, đồng thời
#  có hàm độc lập du_doan_tx_regime(lich_su).
# ============================================================================
PATTERN8_MAP = {
    'TXXTTXTX': ('T', 61.5, 13),
    'XXTTXTXX': ('T', 55.6, 18),
    'XTTXTXXT': ('T', 56.2, 16),
    'TTXTXXTT': ('T', 50.0, 16),
    'TXTXXTTT': ('X', 56.2, 16),
    'XTXXTTTX': ('T', 65.0, 20),
    'TXXTTTXX': ('T', 63.2, 19),
    'XXTTTXXT': ('X', 68.2, 22),
    'XTTTXXTX': ('T', 55.2, 29),
    'TTTXXTXX': ('X', 58.3, 24),
    'TTXXTXXX': ('T', 60.7, 28),
    'TXXTXXXX': ('X', 57.1, 21),
    'XXTXXXXX': ('T', 70.6, 17),
    'XTXXXXXT': ('X', 63.2, 19),
    'TXXXXXTX': ('X', 61.5, 26),
    'XXXXXTXX': ('X', 54.5, 22),
    'XXXXTXXX': ('T', 64.7, 17),
    'XXXTXXXT': ('T', 61.9, 21),
    'XXTXXXTX': ('X', 66.7, 24),
    'XTXXXTXX': ('T', 57.1, 21),
    'TXXXTXXX': ('T', 58.8, 17),
    'XXXTXXXX': ('T', 61.5, 13),
    'XXTXXXXT': ('X', 58.8, 17),
    'XTXXXXTT': ('T', 57.9, 19),
    'TXXXXTTX': ('X', 55.6, 18),
    'XXXXTTXX': ('T', 50.0, 20),
    'XXXTTXXX': ('X', 66.7, 18),
    'XXTTXXXT': ('T', 58.3, 12),
    'XTTXXXTX': ('T', 69.2, 13),
    'TTXXXTXT': ('T', 50.0, 16),
    'TXXXTXTX': ('T', 54.5, 22),
    'XXXTXTXT': ('T', 58.3, 24),
    'XXTXTXTT': ('T', 56.0, 25),
    'XTXTXTTT': ('T', 52.4, 21),
    'TXTXTTTT': ('T', 52.9, 17),
    'XTXTTTTT': ('T', 56.5, 23),
    'TXTTTTTT': ('X', 59.1, 22),
    'XTTTTTTX': ('T', 52.0, 25),
    'TTTTTTXT': ('X', 52.4, 21),
    'TTTTTXTX': ('T', 52.4, 21),
    'TTTTXTXT': ('T', 65.2, 23),
    'TTTXTXTT': ('X', 73.9, 23),
    'TTXTXTTX': ('T', 54.2, 24),
    'TXTXTTXT': ('T', 50.0, 24),
    'XTXTTXTX': ('T', 53.3, 15),
    'TXTTXTXT': ('X', 61.1, 18),
    'XTTXTXTT': ('X', 53.8, 13),
    'TXTTXTXX': ('T', 50.0, 12),
    'XTTXTXXX': ('X', 71.4, 14),
    'TTXTXXXT': ('X', 54.5, 11),
    'TXTXXXTT': ('X', 63.6, 22),
    'XTXXXTTX': ('X', 56.0, 25),
    'TXXXTTXX': ('T', 60.9, 23),
    'XXXTTXXT': ('X', 54.2, 24),
    'XXTTXXTX': ('T', 51.9, 27),
    'XTTXXTXX': ('X', 60.9, 23),
    'TXXTXXXT': ('X', 55.2, 29),
    'XXTXXXTT': ('T', 57.7, 26),
    'XTXXXTTT': ('T', 56.5, 23),
    'TXXXTTTT': ('T', 52.9, 17),
    'XXXTTTTT': ('T', 50.0, 22),
    'XXTTTTTT': ('X', 52.2, 23),
    'TTTTTTXX': ('X', 58.3, 24),
    'TTTTTXXX': ('X', 55.6, 27),
    'TTTTXXXT': ('X', 54.2, 24),
    'TTTXXXTX': ('X', 63.2, 19),
    'TXXXTXTT': ('X', 53.8, 13),
    'XXXTXTTX': ('X', 83.3, 12),
    'XXTXTTXX': ('T', 57.1, 21),
    'XTXTTXXT': ('X', 62.5, 24),
    'TXTTXXTT': ('T', 75.0, 16),
    'XTTXXTTT': ('T', 56.0, 25),
    'TTXXTTTX': ('X', 60.0, 20),
    'TXXTTTXT': ('T', 50.0, 22),
    'XXTTTXTX': ('X', 52.6, 19),
    'XTTTXTXX': ('X', 77.8, 18),
    'TTTXTXXX': ('X', 66.7, 21),
    'XTXTTXXX': ('X', 72.2, 18),
    'TXTTXXXT': ('X', 61.5, 13),
    'TTXXXTXX': ('X', 53.3, 15),
    'TXXXTXXT': ('X', 57.9, 19),
    'XXXTXXTX': ('X', 57.1, 21),
    'XXTXXTXT': ('X', 61.1, 18),
    'XTXXTXTX': ('T', 61.1, 18),
    'TXXTXTXT': ('X', 57.7, 26),
    'XTXTXTTX': ('T', 50.0, 22),
    'XTXTTXTT': ('T', 82.4, 17),
    'TXTTXTTT': ('T', 54.5, 22),
    'XTTXTTTX': ('T', 59.1, 22),
    'TTXTTTXT': ('T', 70.8, 24),
    'TXTTTXTT': ('T', 52.4, 21),
    'XTTTXTTX': ('T', 62.5, 16),
    'TTTXTTXT': ('X', 52.6, 19),
    'TTXTTXTX': ('T', 66.7, 15),
    'TTXTXXTX': ('T', 56.2, 16),
    'TXTXXTXT': ('T', 53.3, 15),
    'XTXXTXTT': ('X', 53.3, 15),
    'TXXTXTTT': ('T', 76.2, 21),
    'XXTXTTTT': ('T', 58.3, 24),
    'TXTTTTTX': ('X', 57.1, 21),
    'XTTTTTXX': ('X', 56.5, 23),
    'TTTTXXXX': ('X', 53.6, 28),
    'TTTXXXXX': ('X', 52.0, 25),
    'TTXXXXXX': ('T', 52.4, 21),
    'TXXXXXXT': ('T', 77.8, 18),
    'XXXXXXTT': ('X', 54.5, 22),
    'XXXXXTTX': ('T', 56.5, 23),
    'XTTXXTXT': ('X', 70.4, 27),
    'TTXXTXTT': ('T', 60.9, 23),
    'XTXTTTTX': ('T', 50.0, 18),
    'TXTTTTXT': ('X', 68.4, 19),
    'XTTTTXTX': ('T', 57.1, 21),
    'TTTTXTXX': ('T', 63.2, 19),
    'TTTXTXXT': ('X', 56.2, 16),
    'TXTXTTTX': ('T', 50.0, 16),
    'XTXTTTXX': ('T', 56.5, 23),
    'TXTTTXXT': ('X', 58.3, 24),
    'XTTTXXTT': ('T', 55.6, 18),
    'TTTXXTTT': ('T', 60.9, 23),
    'TTXXTTTT': ('T', 50.0, 28),
    'TXXTTTTX': ('X', 57.1, 28),
    'XXTTTTXT': ('T', 55.6, 18),
    'TXTXTTXX': ('T', 54.5, 22),
    'TXTTXXXX': ('T', 52.6, 19),
    'XTTXXXXT': ('X', 70.6, 17),
    'TTXXXXTX': ('X', 57.1, 21),
    'TXXXXTXT': ('T', 61.9, 21),
    'XXXXTXTX': ('T', 75.0, 16),
    'TXTTTTXX': ('X', 60.0, 20),
    'XTTTTXXT': ('X', 57.9, 19),
    'TTTTXXTX': ('X', 60.0, 20),
    'XXXTXXTT': ('T', 53.8, 26),
    'XXTXXTTT': ('T', 57.7, 26),
    'XXTTTXTT': ('T', 71.4, 21),
    'TTTXTTXX': ('X', 52.9, 17),
    'TTXTTXXX': ('T', 57.1, 14),
    'XTTXXXXX': ('T', 63.6, 22),
    'TTXXXXXT': ('X', 53.8, 26),
    'TXXXXXTT': ('X', 57.9, 19),
    'XXXXXTTT': ('T', 55.6, 18),
    'XXXXTTTT': ('T', 72.2, 18),
    'XXXTTTTX': ('X', 53.8, 13),
    'XTTXTXTX': ('X', 57.9, 19),
    'TTXTXTXT': ('X', 56.2, 16),
    'TXTXTXTX': ('X', 55.6, 18),
    'XTXTXTXT': ('T', 55.0, 20),
    'XTXTXTXX': ('X', 56.5, 23),
    'TXTXTXXT': ('X', 77.8, 18),
    'XTXTXXTX': ('X', 66.7, 18),
    'XXTXTXTX': ('X', 52.0, 25),
    'TXTXTXTT': ('X', 61.1, 18),
    'TXTTTXXX': ('X', 60.0, 20),
    'XTTTXXXX': ('X', 62.5, 16),
    'TTTXXXXT': ('T', 52.6, 19),
    'TTXXXXTT': ('X', 66.7, 15),
    'XXXTXTXX': ('X', 57.1, 14),
    'XXTXTXXX': ('T', 73.7, 19),
    'XTXTXXXT': ('T', 63.0, 27),
    'XXTTXXTT': ('T', 72.2, 18),
    'TXXTTTTT': ('T', 52.2, 23),
    'TTTTTXTT': ('X', 60.0, 20),
    'TTTTXTTT': ('T', 53.3, 15),
    'TTTXTTTT': ('X', 55.6, 18),
    'TTXTTTTX': ('X', 52.4, 21),
    'XTXXTTTT': ('X', 60.9, 23),
    'XTTTTXTT': ('T', 50.0, 16),
    'XTTTTXXX': ('X', 52.0, 25),
    'TXXXXTTT': ('T', 50.0, 16),
    'XXXXTTTX': ('T', 62.5, 16),
    'XXXTTTXX': ('T', 62.5, 16),
    'TXTXTXXX': ('T', 56.5, 23),
    'XXTTTTXX': ('X', 54.2, 24),
    'TTTXXXTT': ('X', 54.5, 22),
    'TTXXXTTX': ('T', 59.1, 22),
    'TXXXTTXT': ('T', 62.5, 24),
    'XXXTTXTT': ('T', 73.1, 26),
    'XXTTXTTX': ('X', 61.5, 13),
    'XTTXTTXX': ('T', 58.3, 12),
    'TTXTTXXT': ('X', 53.3, 15),
    'TTTXXTXT': ('T', 62.5, 24),
    'TTXXTXTX': ('T', 53.6, 28),
    'TXTXXXTX': ('T', 68.8, 16),
    'TTTTXXTT': ('T', 68.4, 19),
    'XTTTTTTT': ('T', 60.0, 20),
    'TTTTTTTT': ('T', 53.8, 26),
    'TTTTTTTX': ('X', 60.0, 20),
    'TTTTTXXT': ('T', 55.0, 20),
    'TTTXXTTX': ('T', 50.0, 14),
    'TTXXTTXX': ('T', 72.7, 11),
    'TXXTTXXT': ('X', 66.7, 21),
    'TTXXTXXT': ('X', 63.2, 19),
    'TXXTXXTX': ('X', 52.6, 19),
    'XXTXXTXX': ('X', 61.9, 21),
    'XTXXTXXX': ('T', 54.5, 22),
    'XTXXXXTX': ('T', 52.2, 23),
    'XXXXTXTT': ('T', 76.2, 21),
    'XXXTXTTT': ('X', 63.6, 22),
    'TXXTXXTT': ('T', 66.7, 18),
    'XXXXXTXT': ('T', 50.0, 16),
    'XTTXXXTT': ('X', 83.3, 12),
    'XXTTXXXX': ('X', 65.0, 20),
    'TXTTXTTX': ('X', 57.1, 7),
    'XTTXTTXT': ('X', 62.5, 8),
    'TTXTTXTT': ('T', 66.7, 12),
    'XTTXTTTT': ('T', 52.2, 23),
    'TTXTTTTT': ('X', 55.0, 20),
    'TTTTXTTX': ('X', 55.0, 20),
    'TTXTXXXX': ('T', 68.0, 25),
    'TXTXXXXT': ('X', 52.0, 25),
    'XXTTTTTX': ('T', 50.0, 22),
    'XTTTTTXT': ('T', 50.0, 20),
    'TTTXTXTX': ('T', 53.3, 15),
    'TXTXXTXX': ('T', 52.6, 19),
    'XTXXTXXT': ('T', 61.1, 18),
    'XTXTXXXX': ('T', 53.3, 15),
    'TXXXXTXX': ('T', 78.3, 23),
    'TTXTXTXX': ('X', 55.6, 18),
    'XTXTXXTT': ('T', 50.0, 16),
    'TXXXTTTX': ('X', 57.9, 19),
    'XXXTTTXT': ('T', 55.6, 18),
    'XXTTTXXX': ('T', 69.2, 13),
    'XTTTXXXT': ('T', 66.7, 18),
    'TTXXXTTT': ('X', 66.7, 12),
    'TXXTXTTX': ('X', 64.7, 17),
    'TXTTXXTX': ('T', 56.5, 23),
    'XXTXTTTX': ('X', 78.9, 19),
    'XTXXXXXX': ('T', 53.8, 13),
    'TXXXXXXX': ('T', 75.0, 16),
    'XXXXXXXT': ('T', 50.0, 16),
    'XXXXTTXT': ('T', 52.4, 21),
    'XXXTTXTX': ('X', 68.4, 19),
    'TXTXXXXX': ('X', 53.3, 15),
    'XXXXTXXT': ('T', 64.3, 28),
    'TXXTXTXX': ('T', 50.0, 20),
    'XXTXTXXT': ('T', 75.0, 16),
    'TXTXXTTX': ('X', 68.8, 16),
    'XTXXTTXX': ('T', 54.2, 24),
    'TXXTTXXX': ('X', 57.1, 14),
    'XXTTXTTT': ('X', 52.2, 23),
    'TTXTTTXX': ('T', 52.4, 21),
    'XXXXXXTX': ('T', 50.0, 12),
    'TTTXTTTX': ('X', 52.2, 23),
    'XTTTXTTT': ('X', 61.5, 26),
    'TXTTTXTX': ('X', 57.1, 14),
    'XTXXXTXT': ('X', 73.7, 19),
    'XTTXXTTX': ('T', 55.6, 9),
    'TTXXTTXT': ('X', 75.0, 12),
    'XXTTXTXT': ('X', 57.1, 14),
    'XXTXXTTX': ('X', 72.2, 18),
    'XXTXTTXT': ('T', 62.5, 8),
    'TTXTXTTT': ('T', 50.0, 12),
    'XTXTTTXT': ('X', 58.3, 12),
    'XTTTXTXT': ('T', 53.3, 15),
    'XTXXTTXT': ('T', 70.0, 10),
    'TXXTTXTT': ('X', 60.0, 10),
    'XXXXXXXX': ('X', 63.6, 11),
}

PATTERNS_63 = [
    {'name':'BET_9+','type':'streak','spec':[9,99],'action':'opp','conf':94},
    {'name':'BET_7-8','type':'streak','spec':[7,8],'action':'opp','conf':91},
    {'name':'BET_5-6','type':'streak','spec':[5,6],'action':'opp','conf':88},
    {'name':'CHUKY_7-7','type':'groups','spec':[7,7],'action':'opp','conf':92},
    {'name':'CHUKY_6-6','type':'groups','spec':[6,6],'action':'opp','conf':91},
    {'name':'CHUKY_5-5','type':'groups','spec':[5,5],'action':'opp','conf':90},
    {'name':'CHUKY_4-4','type':'groups','spec':[4,4],'action':'opp','conf':89},
    {'name':'CHUKY_3-3','type':'groups','spec':[3,3],'action':'opp','conf':89},
    {'name':'CHUKY_2-2','type':'groups','spec':[2,2,2,2],'action':'opp','conf':88},
    {'name':'CHUKY_1-1','type':'groups','spec':[1,1,1,1,1,1],'action':'opp','conf':90},
    {'name':'NHIPHUC_3-2-2-3','type':'groups','spec':[3,2,2,3],'action':'opp','conf':89},
    {'name':'NHIPHUC_1-1-2-2-3','type':'groups','spec':[1,1,2,2,3],'action':'opp','conf':86},
    {'name':'NHIPHUC_2-1-2-1-2','type':'groups','spec':[2,1,2,1,2],'action':'opp','conf':88},
    {'name':'NHIPHUC_1-2-1-2-1','type':'groups','spec':[1,2,1,2,1],'action':'opp','conf':88},
    {'name':'NHIPHUC_3-1-2-2','type':'groups','spec':[3,1,2,2],'action':'opp','conf':84},
    {'name':'NHIPHUC_2-2-1-3','type':'groups','spec':[2,2,1,3],'action':'opp','conf':85},
    {'name':'NHIPHUC_3-2-3-2','type':'groups','spec':[3,2,3,2],'action':'opp','conf':88},
    {'name':'NHIPHUC_1-2-1-3','type':'groups','spec':[1,2,1,3],'action':'opp','conf':84},
    {'name':'NHIPHUC_3-1-1-3','type':'groups','spec':[3,1,1,3],'action':'opp','conf':90},
    {'name':'NHIPHUC_3-2-3','type':'groups','spec':[3,2,3],'action':'opp','conf':86},
    {'name':'NHIPHUC_2-3-2','type':'groups','spec':[2,3,2],'action':'opp','conf':84},
    {'name':'NHIPHUC_3-1-3','type':'groups','spec':[3,1,3],'action':'opp','conf':91},
    {'name':'NHIPHUC_1-3-1','type':'groups','spec':[1,3,1],'action':'opp','conf':90},
    {'name':'NHIPHUC_1-2-3','type':'groups','spec':[1,2,3],'action':'opp','conf':84},
    {'name':'NHIPHUC_2-1-2','type':'groups','spec':[2,1,2],'action':'opp','conf':86},
    {'name':'NHIPHUC_1-2-1','type':'groups','spec':[1,2,1],'action':'opp','conf':85},
    {'name':'NHIPHUC_2-1-1-2','type':'groups','spec':[2,1,1,2],'action':'opp','conf':87},
    {'name':'NHIPHUC_1-2-1-2','type':'groups','spec':[1,2,1,2],'action':'opp','conf':87},
    {'name':'NHIPHUC_1-1-1-2','type':'groups','spec':[1,1,1,2],'action':'opp','conf':87},
    {'name':'NHIPHUC_2-2-1-1','type':'groups','spec':[2,2,1,1],'action':'opp','conf':88},
    {'name':'NHIPHUC_1-1-2-2','type':'groups','spec':[1,1,2,2],'action':'opp','conf':88},
    {'name':'NHIPHUC_1-2-2-1','type':'groups','spec':[1,2,2,1],'action':'opp','conf':86},
    {'name':'NHIPHUC_1-1-2','type':'groups','spec':[1,1,2],'action':'opp','conf':84},
    {'name':'NHIPHUC_1-2-1-1','type':'groups','spec':[1,2,1,1],'action':'opp','conf':83},
    {'name':'NHIPHUC_1-6','type':'groups','spec':[1,6],'action':'opp','conf':90},
    {'name':'NHIPHUC_6-1','type':'groups','spec':[6,1],'action':'opp','conf':90},
    {'name':'NHIPHUC_1-5','type':'groups','spec':[1,5],'action':'opp','conf':89},
    {'name':'NHIPHUC_5-1','type':'groups','spec':[5,1],'action':'opp','conf':89},
    {'name':'NHIPHUC_1-4','type':'groups','spec':[1,4],'action':'opp','conf':85},
    {'name':'NHIPHUC_4-1','type':'groups','spec':[4,1],'action':'opp','conf':85},
    {'name':'NHIPHUC_1-3','type':'groups','spec':[1,3],'action':'opp','conf':83},
    {'name':'NHIPHUC_3-1','type':'groups','spec':[3,1],'action':'opp','conf':83},
    {'name':'GUONG_11','type':'palin','spec':11,'action':'opp','conf':88},
    {'name':'GUONG_9','type':'palin','spec':9,'action':'opp','conf':86},
    {'name':'PALIN_7','type':'palin','spec':7,'action':'opp','conf':84},
    {'name':'PALIN_5','type':'palin','spec':5,'action':'opp','conf':82},
    {'name':'BET_3-4','type':'streak','spec':[3,4],'action':'cont','conf':82},
]

REGIME_BOOST = {
    'streaky':  {'markov':0.9,'streak':1.5,'betbreak':1.4,'pattern':1.0,'pattern63':1.3,'momentum':1.1,'alt':0.7},
    'choppy':   {'markov':1.1,'streak':0.7,'betbreak':1.0,'pattern':1.4,'pattern63':1.4,'momentum':0.8,'alt':1.5},
    'trending': {'markov':1.2,'streak':1.1,'betbreak':0.9,'pattern':0.9,'pattern63':1.0,'momentum':1.5,'alt':0.8},
    'balanced': {'markov':1.2,'streak':1.0,'betbreak':1.0,'pattern':1.1,'pattern63':1.2,'momentum':1.0,'alt':1.0},
}


def _re_wilson(correct, total, z=1.96):
    if total == 0:
        return 0.0
    p = correct / total
    d = 1 + z * z / total
    c = (p + z * z / (2 * total)) / d
    sp = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return max(0.0, c - sp)


def _re_blocks(seq):
    b, c = [], 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            c += 1
        else:
            b.append(c); c = 1
    b.append(c)
    return b


def _re_detect_regime(seq, A, B):
    if len(seq) < 30:
        return 'balanced'
    recent = seq[-50:]
    maxS = cur = 1
    for i in range(1, len(recent)):
        if recent[i] == recent[i - 1]:
            cur += 1
        else:
            maxS = max(maxS, cur); cur = 1
    maxS = max(maxS, cur)
    a_ratio = sum(1 for x in recent if x == A) / len(recent)
    bias = abs(a_ratio - 0.5)
    alt = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])
    alt_rate = alt / (len(recent) - 1)
    if maxS >= 6: return 'streaky'
    if alt_rate > 0.62: return 'choppy'
    if bias > 0.12: return 'trending'
    return 'balanced'


def _re_streak_len(seq):
    if not seq: return 0
    last = seq[-1]; r = 0
    for c in reversed(seq):
        if c == last: r += 1
        else: break
    return r


class TXRegimeEngine:
    """Port trung thực của predict() trong server.js."""

    @staticmethod
    def _markov_n(seq, n, minC, A, B):
        if len(seq) < n + 8:
            return None
        key = tuple(seq[-n:])
        a = b = 0
        for i in range(n, len(seq)):
            if tuple(seq[i - n:i]) == key:
                if seq[i] == A: a += 1
                else: b += 1
        t = a + b
        if t < minC:
            return None
        pa = (a + 1) / (t + 2)
        if pa > 0.6:
            return {'vote': A, 'w': 1 + _re_wilson(a, t) * 0.5}
        if pa < 0.4:
            return {'vote': B, 'w': 1 + _re_wilson(b, t) * 0.5}
        return None

    @staticmethod
    def _recent_markov(seq, A, B):
        if len(seq) < 50: return None
        return TXRegimeEngine._markov_n(seq[-150:], 2, 5, A, B)

    @staticmethod
    def _weighted_markov(seq, A, B):
        if len(seq) < 60: return None
        key = tuple(seq[-2:])
        wa = wb = 0.0
        tau = 80.0
        for i in range(2, len(seq)):
            if tuple(seq[i - 2:i]) == key:
                w = math.exp(-(len(seq) - i) / tau)
                if seq[i] == A: wa += w
                else: wb += w
        t = wa + wb
        if t < 3: return None
        pa = (wa + 0.3) / (t + 0.6)
        if pa > 0.6: return {'vote': A, 'w': 1.2}
        if pa < 0.4: return {'vote': B, 'w': 1.2}
        return None

    @staticmethod
    def _bayesian(seq, A, B):
        if len(seq) < 40: return None
        key = tuple(seq[-3:])
        prior = 0.5 + (sum(1 for x in seq[-30:] if x == A) / 30.0 - 0.5) * 0.5
        a = b = 0
        for i in range(3, len(seq)):
            if tuple(seq[i - 3:i]) == key:
                if seq[i] == A: a += 1
                else: b += 1
        t = a + b
        if t < 5: return None
        pa = (a + 4 * prior) / (t + 4)
        if pa > 0.6: return {'vote': A, 'w': 1.1}
        if pa < 0.4: return {'vote': B, 'w': 1.1}
        return None

    @staticmethod
    def _streak(seq, A, B):
        if len(seq) < 30: return None
        last = seq[-1]
        s = _re_streak_len(seq)
        if s < 3: return None
        cont = brk = 0
        for i in range(len(seq) - 1):
            ss = 1
            j = i - 1
            while j >= 0 and seq[j] == seq[i]:
                ss += 1; j -= 1
            if ss == s:
                if seq[i + 1] == seq[i]: cont += 1
                else: brk += 1
        t = cont + brk
        if t < 6: return None
        pc = (cont + 1.5) / (t + 3)
        if pc > 0.58: return {'vote': last, 'w': 1.3}
        if pc < 0.42: return {'vote': B if last == A else A, 'w': 1.3}
        return None

    @staticmethod
    def _bet_breaker(seq, A, B):
        if len(seq) < 50: return None
        last = seq[-1]
        s = _re_streak_len(seq)
        if s < 4 or s > 9: return None
        cont = brk = 0
        for i in range(len(seq) - 1):
            ss = 1
            j = i - 1
            while j >= 0 and seq[j] == seq[i]:
                ss += 1; j -= 1
            if ss == s:
                if seq[i + 1] == seq[i]: cont += 1
                else: brk += 1
        t = cont + brk
        if t < 5: return None
        pb = (brk + 1.5) / (t + 3)
        if pb > 0.6: return {'vote': B if last == A else A, 'w': 1.4}
        if pb < 0.4: return {'vote': last, 'w': 1.2}
        return None

    @staticmethod
    def _streak_dist(seq, A, B):
        if len(seq) < 60: return None
        last = seq[-1]
        cur = _re_streak_len(seq)
        if cur < 2: return None
        ends = {}
        c = 1
        for i in range(1, len(seq)):
            if seq[i] == seq[i - 1]:
                c += 1
            else:
                ends[c] = ends.get(c, 0) + 1; c = 1
        ends[c] = ends.get(c, 0) + 1
        maxH = max(ends.keys()) if ends else 0
        opp = B if last == A else A
        if cur >= maxH + 1:
            return {'vote': opp, 'w': 1.5}
        stop = ends.get(cur, 0)
        cont_long = sum(v for k, v in ends.items() if k > cur)
        if stop + cont_long < 6: return None
        ps = (stop + 1.5) / (stop + cont_long + 3)
        if ps > 0.62: return {'vote': opp, 'w': 1.3}
        if ps < 0.38: return {'vote': last, 'w': 1.1}
        return None

    @staticmethod
    def _pattern(seq, A, B):
        if len(seq) < 6: return None
        b = _re_blocks(seq)
        last_block = b[-1]
        lv = seq[-1]
        opp = B if lv == A else A
        if last_block >= 5: return {'vote': opp, 'w': 1.4}
        if last_block >= 3 and len(b) >= 2: return {'vote': opp, 'w': 1.1}
        if len(b) >= 3:
            l3 = b[-3:]
            if l3[0] == l3[2] and l3[0] >= 2: return {'vote': opp, 'w': 1.2}
            if l3[0] < l3[1] and l3[1] > l3[2]: return {'vote': opp, 'w': 1.1}
            if (l3[0] == 1 and l3[1] == 2 and l3[2] == 1) or (l3[0] == 2 and l3[1] == 1 and l3[2] == 2):
                return {'vote': opp, 'w': 1.3}
        fib = [1, 1, 2, 3, 5]
        if len(b) >= 3 and b[-3:] == fib[:3]:
            return {'vote': opp, 'w': 1.3}
        return None

    @staticmethod
    def _alternating(seq, A, B):
        if len(seq) < 6: return None
        l6 = seq[-6:]
        if all(l6[i] != l6[i - 1] for i in range(1, 6)):
            return {'vote': l6[-1], 'w': 1.3}
        return None

    @staticmethod
    def _double_block(seq, A, B):
        if len(seq) < 8: return None
        b = _re_blocks(seq)
        if len(b) >= 2 and b[-1] == b[-2] and 2 <= b[-1] <= 4:
            return {'vote': B if seq[-1] == A else A, 'w': 1.2}
        return None

    @staticmethod
    def _long_pattern(seq, A, B):
        if len(seq) < 10: return None
        tail = seq[-8:]
        if tail == tail[::-1]:
            return {'vote': B if seq[-1] == A else A, 'w': 1.2}
        return None

    @staticmethod
    def _momentum(seq, w, A, B):
        if len(seq) < w + 5: return None
        a = sum(1 for x in seq[-w:] if x == A)
        pa = a / w
        if pa > 0.65: return {'vote': A, 'w': 1.1}
        if pa < 0.35: return {'vote': B, 'w': 1.1}
        return None

    @staticmethod
    def _dual_timeframe(seq, A, B):
        m5 = TXRegimeEngine._momentum(seq, 5, A, B)
        m20 = TXRegimeEngine._momentum(seq, 20, A, B)
        if m5 and m20 and m5['vote'] == m20['vote']:
            return {'vote': m5['vote'], 'w': 1.4}
        return None

    @staticmethod
    def _pattern63(seq, A, B):
        if len(seq) < 3: return None
        rle = _re_blocks(seq)
        last = seq[-1]
        cont = last
        opp = B if last == A else A
        streak = rle[-1]
        last8 = seq[-8:]
        if len(last8) >= 8 and all(last8[i] != last8[i - 1] for i in range(1, 8)):
            return {'vote': cont, 'w': 1.8, 'name': 'ANTI_TRAP_8DAO'}
        for p in PATTERNS_63:
            matched = False
            if p['type'] == 'streak':
                if p['spec'][0] <= streak <= p['spec'][1]:
                    matched = True
            elif p['type'] == 'groups':
                spec = p['spec']
                tail = rle[-len(spec):]
                if len(tail) == len(spec) and tail == spec:
                    matched = True
            elif p['type'] == 'palin':
                L = p['spec']
                if len(seq) >= L:
                    s = seq[-L:]
                    if s == s[::-1]:
                        matched = True
            if matched:
                vote = cont if p['action'] == 'cont' else opp
                return {'vote': vote, 'w': 1 + (p['conf'] - 80) / 18.0, 'name': p['name']}
        if len(seq) >= 12:
            lastN = seq[-20:]
            aN = sum(1 for x in lastN if x == A)
            bN = len(lastN) - aN
            if abs(aN - bN) >= 6:
                return {'vote': A if aN < bN else B, 'w': 1.3, 'name': 'HOI_QUY_20'}
        return None

    @staticmethod
    def _pattern8(seq, A, B):
        if len(seq) < 8: return None
        key = ''.join('T' if x == A else 'X' for x in seq[-8:])
        m = PATTERN8_MAP.get(key)
        if not m or m[1] < 55:
            return None
        pred_side, rate, _n = m
        vote = A if pred_side == 'T' else B
        return {'vote': vote, 'w': 1 + (rate - 50) / 25.0, 'name': 'PATTERN8(%.1f%%)' % rate}

    @staticmethod
    def _markov_fallback(seq, A, B):
        if len(seq) < 4: return None
        w = min(20, len(seq))
        recent = seq[-w:]
        aa = ab = ba = bb = 0
        for i in range(len(recent) - 1):
            x, y = recent[i], recent[i + 1]
            if x == A and y == A: aa += 1
            elif x == A and y == B: ab += 1
            elif x == B and y == A: ba += 1
            else: bb += 1
        last = recent[-1]
        if last == A:
            t = aa + ab or 1
            p_cont = aa / t
        else:
            t = ba + bb or 1
            p_cont = bb / t
        if p_cont > 0.58:
            return {'vote': last, 'w': 1.0, 'name': 'MARKOV_FB'}
        if p_cont < 0.42:
            return {'vote': B if last == A else A, 'w': 1.0, 'name': 'MARKOV_FB'}
        return None

    @staticmethod
    def predict(seq, A='T', B='X'):
        seq = [x for x in seq if x in (A, B)]
        regime = _re_detect_regime(seq, A, B)
        boost = REGIME_BOOST[regime]
        E = TXRegimeEngine
        raw = [
            (E._markov_n(seq, 2, 8, A, B), 'markov'),
            (E._markov_n(seq, 3, 6, A, B), 'markov'),
            (E._markov_n(seq, 4, 4, A, B), 'markov'),
            (E._recent_markov(seq, A, B), 'markov'),
            (E._weighted_markov(seq, A, B), 'markov'),
            (E._bayesian(seq, A, B), 'markov'),
            (E._streak(seq, A, B), 'streak'),
            (E._bet_breaker(seq, A, B), 'betbreak'),
            (E._streak_dist(seq, A, B), 'streak'),
            (E._pattern(seq, A, B), 'pattern'),
            (E._alternating(seq, A, B), 'alt'),
            (E._double_block(seq, A, B), 'pattern'),
            (E._long_pattern(seq, A, B), 'pattern'),
            (E._momentum(seq, 5, A, B), 'momentum'),
            (E._momentum(seq, 10, A, B), 'momentum'),
            (E._momentum(seq, 20, A, B), 'momentum'),
            (E._dual_timeframe(seq, A, B), 'momentum'),
            (E._pattern63(seq, A, B), 'pattern63'),
            (E._pattern8(seq, A, B), 'pattern'),
            (E._markov_fallback(seq, A, B), 'markov'),
        ]
        wA = wB = 0.0
        used = 0
        hit = ''
        for s, g in raw:
            if not s:
                continue
            bw = s['w'] * boost.get(g, 1.0)
            if s['vote'] == A:
                wA += bw
            else:
                wB += bw
            used += 1
            if s.get('name') and not hit:
                hit = s['name']
        if used == 0:
            return {'prediction': 'CHO', 'confidence': 50, 'signals': 0,
                    'regime': regime, 'pattern_hit': '', 'wA': 0.0, 'wB': 0.0}
        total = wA + wB
        pred = A if wA >= wB else B
        wWin = max(wA, wB)
        conf = min(97, round(50 + (wWin / total - 0.5) * 100 +
                             _re_wilson(int(round(wWin)), int(round(total))) * 15))
        return {'prediction': pred, 'confidence': conf, 'signals': used,
                'regime': regime, 'pattern_hit': hit, 'wA': wA, 'wB': wB}

    @staticmethod
    def as_signal(h):
        """Đóng gói thành tín hiệu (ten, p_tai, weight, kind) cho UltimateEngine."""
        h = [str(c).upper() for c in h if str(c).upper() in ('T', 'X')]
        if len(h) < 8:
            return None
        try:
            r = TXRegimeEngine.predict(h, 'T', 'X')
        except Exception:
            return None
        if r['signals'] == 0 or r['prediction'] == 'CHO':
            return None
        total = r['wA'] + r['wB']
        if total <= 0:
            return None
        p_tai = _clamp(r['wA'] / total, 0.05, 0.95)
        weight = 2.0 + min(r['signals'], 14) * 0.12
        name = "REGIME AI [%s] %d/20 tin hieu" % (r['regime'], r['signals'])
        if r.get('pattern_hit'):
            name += " + " + r['pattern_hit']
        return (name, p_tai, weight, 'ai')


# --- Đưa vào engine chung (giữ nguyên giao diện) ---
UltimateEngine.TX_SIGNALS.append(TXRegimeEngine.as_signal)


def du_doan_tx_regime(ls):
    """Gọi độc lập engine regime-aware. Trả về (ket_qua_dict, [signal])."""
    ls = [str(c).upper() for c in ls if str(c).upper() in ('T', 'X')]
    if len(ls) < 8:
        return None, []
    r = TXRegimeEngine.predict(ls, 'T', 'X')
    if r['signals'] == 0 or r['prediction'] == 'CHO':
        return None, []
    sig = [{
        'ten': 'REGIME AI [%s] %d/20' % (r['regime'], r['signals']),
        'ket_tiep': r['prediction'],
        'do_tin_cay': r['confidence'],
        'trong_so': round(2.0 + min(r['signals'], 14) * 0.12, 2),
        'la_ai': True, 'la_vip': False,
        'pattern_hit': r.get('pattern_hit', ''),
    }]
    ket_qua = {
        'du_doan': r['prediction'],
        'do_tin_cay': r['confidence'],
        'xac_suat_tai': round(r['wA'] / (r['wA'] + r['wB']), 4) if (r['wA'] + r['wB']) > 0 else 0.5,
        'so_thuat_toan_tai': 1 if r['prediction'] == 'T' else 0,
        'so_thuat_toan_xiu': 1 if r['prediction'] == 'X' else 0,
        'tong_mau': r['signals'],
        'regime': r['regime'],
        'pattern_hit': r.get('pattern_hit', ''),
        'la_ai': True,
        'engine': 'REGIME-AWARE ENSEMBLE — 20 tin hieu + 63 cau + PATTERN8',
    }
    return ket_qua, sig

# ============================================================================
#  BỔ SUNG THÊM — từ các file thuật toán (batch thứ 2)
#  1. MD5Analyzer: phân tích mã MD5 (port khovukhiobf.html / md5quantum)
#  2. BCR state-flip signal (port main.py bcr_predict)
#  3. TX cycle-correlation (port thuattoan.js analyzeCycles)
#  4. TX B52 pattern-first (port thuattoan (1).js ThuatToanB52)
# ============================================================================
import re as _re
from collections import Counter as _Counter


# ----------------------------------------------------------------------------
#  1. MD5 ANALYZER — nhập mã MD5 32 ký tự hex → dự đoán Tài/Xỉu
# ----------------------------------------------------------------------------
class MD5Analyzer:
    """Phân tích chuỗi hash MD5 (32 hex) theo đa chỉ số.
    Port cấu trúc analyzeDeepMD5_V4 + pythonStandardAlgorithm (khovukhiobf.html)."""

    HIGH = set('89abcdef')
    LOW = set('01234567')

    @staticmethod
    def _bytes(md5):
        return [int(md5[i:i + 2], 16) for i in range(0, 32, 2)]

    @staticmethod
    def _bitstring(md5):
        return ''.join(bin(int(c, 16))[2:].zfill(4) for c in md5)

    @staticmethod
    def _entropy(symbols):
        n = len(symbols)
        if n == 0:
            return 0.0
        c = _Counter(symbols)
        h = 0.0
        for v in c.values():
            p = v / n
            h -= p * math.log2(p)
        return h

    @staticmethod
    def _entropy_v4(md5):
        return MD5Analyzer._entropy(list(md5))

    @staticmethod
    def _hex_pair_entropy(md5):
        pairs = [md5[i:i + 2] for i in range(0, 32, 2)]
        return MD5Analyzer._entropy(pairs)

    @staticmethod
    def _xor_fold(bits):
        # gập 128 bit thành 64 bằng XOR 2 nửa, đếm bit 1 → chuẩn hóa về 0
        half = len(bits) // 2
        ones = sum(1 for i in range(half) if bits[i] != bits[i + half])
        return (ones / half - 0.5) * 2  # -1..1

    @staticmethod
    def _markov_momentum(md5):
        # xu hướng chuyển tiếp hex cao→thấp
        ups = downs = 0
        for i in range(1, len(md5)):
            a, b = int(md5[i - 1], 16), int(md5[i], 16)
            if b > a: ups += 1
            elif b < a: downs += 1
        t = ups + downs or 1
        return (ups - downs) / t  # -1..1

    @staticmethod
    def _run_length(bits):
        # chuỗi bit lặp dài nhất → chuẩn hóa
        maxr = cur = 1
        for i in range(1, len(bits)):
            if bits[i] == bits[i - 1]:
                cur += 1; maxr = max(maxr, cur)
            else:
                cur = 1
        return (maxr - 4) / 8  # xấp xỉ -0.5..1

    @staticmethod
    def _vilong_bit_entropy(bits):
        # entropy của các cặp bit liền kề
        pairs = [bits[i:i + 2] for i in range(0, len(bits) - 1, 2)]
        return MD5Analyzer._entropy(pairs) / 2.0  # 0..1

    @staticmethod
    def _python_standard(md5):
        """pythonStandardAlgorithm: 4 cụm 8 hex, cao→Tài thấp→Xỉu."""
        score_tai = score_xiu = 0.0
        for i in range(0, 32, 8):
            cluster = md5[i:i + 8]
            hi = sum(1 for c in cluster if c in MD5Analyzer.HIGH)
            lo = sum(1 for c in cluster if c in MD5Analyzer.LOW)
            if hi > lo: score_tai += 1
            elif lo > hi: score_xiu += 1
            else: score_tai += 0.5; score_xiu += 0.5
        total = score_tai + score_xiu or 1
        py_tai_pct = score_tai / total * 100
        normalized = (score_tai - score_xiu) / total  # -1..1
        return {'pyTaiPct': round(py_tai_pct, 1), 'normalizedScore': normalized}

    @staticmethod
    def analyze(md5_hex):
        md5 = md5_hex.strip().lower()
        if not _re.fullmatch(r'[0-9a-f]{32}', md5):
            return {'error': 'MD5 phai la 32 ky tu hex (0-9,a-f)'}

        # 4 cụm 8 hex có trọng số [1.2, 1.0, 1.0, 1.1]
        weights = [1.2, 1.0, 1.0, 1.1]
        score_old = 0.0
        for i in range(4):
            cluster = md5[i * 8:i * 8 + 8]
            hi = sum(1 for c in cluster if c in MD5Analyzer.HIGH)
            lo = 8 - hi
            if hi > lo: score_old += weights[i]
            elif lo > hi: score_old -= weights[i]

        bits = MD5Analyzer._bitstring(md5)
        entropy_score = (MD5Analyzer._entropy_v4(md5) + MD5Analyzer._hex_pair_entropy(md5) - 7) * 2
        deep_score = (MD5Analyzer._xor_fold(bits) * 1.5 +
                      MD5Analyzer._markov_momentum(md5) * 2.0 +
                      MD5Analyzer._run_length(bits) * 1.0)
        vilong = MD5Analyzer._vilong_bit_entropy(bits)
        py = MD5Analyzer._python_standard(md5)

        final_score = (score_old * 0.2 + entropy_score * 0.1 +
                       deep_score * 0.35 + vilong * 0.15 +
                       py['normalizedScore'] * 0.2)

        tai_pct = max(5.0, min(95.0, 50 + final_score * 12))
        xiu_pct = 100 - tai_pct
        pred = 'T' if tai_pct >= xiu_pct else 'X'
        conf = round(max(tai_pct, xiu_pct), 1)

        byts = MD5Analyzer._bytes(md5)
        xor_all = 0
        for b in byts: xor_all ^= b
        bit_ones = bin(xor_all).count('1') + sum(bin(b).count('1') for b in byts)

        return {
            'du_doan': pred,
            'do_tin_cay': conf,
            'tai_pct': round(tai_pct, 1),
            'xiu_pct': round(xiu_pct, 1),
            'md5': md5,
            'metrics': {
                'score_old': round(score_old, 2),
                'entropy': round(entropy_score, 2),
                'deep': round(deep_score, 2),
                'vilong': round(vilong, 3),
                'py_tai_pct': py['pyTaiPct'],
                'xor': xor_all,
                'bit_ones': bit_ones,
                'hex_sum': sum(byts),
            },
            'engine': 'MD5 DEEP ANALYZER V4 — multi-metric hash scoring',
        }


def du_doan_md5(md5_hex):
    """Gọi tiện ích: nhập mã MD5 → ket_qua dict."""
    return MD5Analyzer.analyze(md5_hex)


# ----------------------------------------------------------------------------
#  2. BCR STATE-FLIP — port main.py bcr_predict (streak+tỉ lệ+nhịp+backtrack)
# ----------------------------------------------------------------------------
def bcr_state_signal(h):
    pb = [c for c in h if c in ('P', 'B')]
    if len(pb) < 6:
        return None
    results = ['P' if c == 'P' else 'B' for c in pb]
    score = {'B': 0.0, 'P': 0.0}
    last = results[-1]
    streak = 1
    for i in range(len(results) - 2, -1, -1):
        if results[i] == last: streak += 1
        else: break
    if streak >= 3:
        score[last] += 4
    cnt = _Counter(results)
    if cnt['B'] > cnt['P']: score['B'] += 2
    else: score['P'] += 2
    if results[-1] != results[-2]:
        score[results[-1]] += 2
    # backtrack pattern 4
    if len(results) >= 6:
        pattern = results[-4:]
        for i in range(len(results) - 5):
            if results[i:i + 4] == pattern:
                score[results[i + 4]] += 3
                break
    # cầu loạn 3-3 → bỏ qua
    last6 = results[-6:]
    if last6.count('P') == 3 and last6.count('B') == 3:
        return None
    total = score['B'] + score['P']
    if total <= 0:
        return None
    p_player = score['P'] / total
    edge = abs(p_player - 0.5) * 2
    weight = 1.4 + edge * 1.2
    pred = 'P' if p_player >= 0.5 else 'B'
    return ("BCR STATE-FLIP [streak %d] -> %s" % (streak, pred),
            _clamp(p_player, 0.05, 0.95), weight, 'ai')


# ----------------------------------------------------------------------------
#  3. TX CYCLE-CORRELATION — port thuattoan.js analyzeCycles
# ----------------------------------------------------------------------------
def tx_cycle_corr(h):
    h = [c for c in h if c in ('T', 'X')]
    if len(h) < 6:
        return None
    best_cycle = 0
    best_corr = 0.0
    max_cycle = min(10, len(h) // 2)
    for cycle in range(2, max_cycle + 1):
        matches = sum(1 for i in range(len(h) - cycle) if h[i] == h[i + cycle])
        corr = matches / (len(h) - cycle)
        if corr > best_corr:
            best_corr, best_cycle = corr, cycle
    if best_cycle > 0 and best_corr > 0.6:
        predicted = h[len(h) - best_cycle]
        p_tai = 0.8 if predicted == 'T' else 0.2
        return ("TX CYCLE-CORR cycle=%d (%.0f%%) -> %s" % (best_cycle, best_corr * 100, predicted),
                p_tai, 1.6, 'ai')
    return None


# ----------------------------------------------------------------------------
#  4. TX B52 PATTERN-FIRST — port thuattoan (1).js ThuatToanB52.duDoan
# ----------------------------------------------------------------------------
def tx_b52_pattern(h):
    h = [c for c in h if c in ('T', 'X')]
    if len(h) < 5:
        return None
    # ưu tiên pattern 3 khớp lịch sử
    last3 = ''.join(h[-3:])
    seq_predict = None
    for i in range(len(h) - 3):
        if ''.join(h[i:i + 3]) == last3 and i + 3 < len(h):
            seq_predict = h[i + 3]
            break
    if seq_predict:
        p_tai = 0.68 if seq_predict == 'T' else 0.32
        return ("TX B52 pattern %s -> %s" % (last3, seq_predict), p_tai, 1.3, 'core')
    # markov bậc 2
    if len(h) >= 3:
        trans = {}
        for i in range(len(h) - 2):
            key = h[i] + h[i + 1]
            trans.setdefault(key, {'T': 0, 'X': 0})
            trans[key][h[i + 2]] += 1
        last2 = h[-2] + h[-1]
        if last2 in trans:
            t, x = trans[last2]['T'], trans[last2]['X']
            if t != x:
                pred = 'T' if t > x else 'X'
                p_tai = 0.62 if pred == 'T' else 0.38
                return ("TX B52 markov2 -> %s" % pred, p_tai, 1.1, 'core')
    return None


# --- Đưa vào engine chung ---
UltimateEngine.BCR_SIGNALS.append(bcr_state_signal)
UltimateEngine.TX_SIGNALS.append(tx_cycle_corr)
UltimateEngine.TX_SIGNALS.append(tx_b52_pattern)
