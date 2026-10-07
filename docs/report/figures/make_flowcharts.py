"""วาด flowchart / sequence / state diagram ของรายงาน เป็นภาพ PNG พื้นหลังขาว (ใช้ matplotlib + ฟอนต์ Noto Sans Thai)

รัน:  .venv-ml/bin/python docs/report/figures/make_flowcharts.py
ผลลัพธ์: docs/report/figures/flow_*.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon

OUT = Path(__file__).resolve().parent
FONT_DIR = Path("/usr/share/fonts/truetype/noto")
for f in ("NotoSansThai-Regular.ttf", "NotoSansThai-Bold.ttf"):
    if (FONT_DIR / f).exists():
        fm.fontManager.addfont(str(FONT_DIR / f))
plt.rcParams["font.family"] = ["Noto Sans Thai", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

LAYER_FILL = "#f2f2f2"


class Chart:
    """พิกัด = นิ้ว, แกน y ชี้ลง"""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.fig = plt.figure(figsize=(w, h), dpi=200, facecolor="white")
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(h, 0)
        self.ax.axis("off")
        self.n = {}

    # ---------- nodes
    def node(self, name, cx, cy, w, h, text, shape="rect", fs=10, bold=False, fill="white", lw=1.2):
        self.n[name] = (cx, cy, w, h, shape)
        x0, y0 = cx - w / 2, cy - h / 2
        if shape == "diamond":
            self.ax.add_patch(Polygon([(cx, y0), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)], closed=True,
                                      fc=fill, ec="black", lw=lw, zorder=2))
        elif shape == "term":
            self.ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle=f"round,pad=0,rounding_size={h / 2}", fc=fill,
                                             ec="black", lw=lw, zorder=2))
        elif shape == "round":
            self.ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=0.12", fc=fill,
                                             ec="black", lw=lw, zorder=2))
        elif shape == "io":
            sk = h * 0.3
            self.ax.add_patch(Polygon([(x0 + sk, y0), (x0 + w, y0), (x0 + w - sk, y0 + h), (x0, y0 + h)], closed=True,
                                      fc=fill, ec="black", lw=lw, zorder=2))
        else:
            self.ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="square,pad=0", fc=fill, ec="black", lw=lw,
                                             zorder=2))
        self.ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal",
                     zorder=3, linespacing=1.25)

    def layer(self, x0, y0, w, h, title, fs=10.5):
        self.ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=0.1", fc=LAYER_FILL,
                                         ec="black", lw=1.4, zorder=0))
        self.ax.text(x0 + 0.15, y0 + 0.12, title, ha="left", va="top", fontsize=fs, fontweight="bold", zorder=1)

    def a(self, name, side, off=0.0):
        cx, cy, w, h, _ = self.n[name]
        return {"t": (cx + off, cy - h / 2), "b": (cx + off, cy + h / 2), "l": (cx - w / 2, cy + off),
                "r": (cx + w / 2, cy + off)}[side]

    # ---------- edges
    def line(self, pts, label=None, lpos=None, dashed=False, arrow=True, fs=8.5, lw=1.1, ha="center", va="bottom",
             lbox=True):
        pts = [self.a(*p) if isinstance(p, tuple) and isinstance(p[0], str) else p for p in pts]
        xs, ys = zip(*pts)
        ls = (0, (4, 3)) if dashed else "-"
        if len(pts) > 2:
            self.ax.plot(xs[:-1], ys[:-1], color="black", lw=lw, ls=ls, zorder=1, solid_capstyle="butt")
        self.ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>" if arrow else "-", mutation_scale=11,
                                          lw=lw, color="black", ls=ls, zorder=1, shrinkA=0, shrinkB=0))
        if label:
            if lpos is None:
                lpos = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
            self.ax.text(lpos[0], lpos[1], label, ha=ha, va=va, fontsize=fs, zorder=4,
                         bbox=dict(fc="white", ec="none", pad=1.2) if lbox else None)

    def arc(self, p0, p1, rad, label=None, lpos=None, fs=8.5, dashed=False):
        p0 = self.a(*p0) if isinstance(p0[0], str) else p0
        p1 = self.a(*p1) if isinstance(p1[0], str) else p1
        self.ax.add_patch(FancyArrowPatch(p0, p1, connectionstyle=f"arc3,rad={rad}", arrowstyle="-|>",
                                          mutation_scale=11, lw=1.1, color="black", zorder=1, shrinkA=0, shrinkB=0,
                                          ls=(0, (4, 3)) if dashed else "-"))
        if label:
            self.ax.text(lpos[0], lpos[1], label, ha="center", va="center", fontsize=fs, zorder=4,
                         bbox=dict(fc="white", ec="none", pad=1.2))

    def text(self, x, y, s, **kw):
        self.ax.text(x, y, s, zorder=4, **kw)

    def save(self, name):
        self.fig.savefig(OUT / name, dpi=200, facecolor="white")
        plt.close(self.fig)
        print("wrote", name)


# =====================================================================================================
def arch():
    c = Chart(10.5, 8.0)
    c.layer(0.3, 0.3, 9.9, 1.75, "ชั้นผู้ใช้ — Frontend (SvelteKit SPA บนมือถือ/คอมพิวเตอร์)")
    c.node("ui", 5.25, 1.45, 7.6, 0.8, "ถ่ายภาพ/เลือกไฟล์  →  แตะจุดอ้างอิง 4 จุด (Q, P, M, Z)  →  ดูผลซ้อนบนภาพ", "round")
    c.layer(0.3, 2.95, 9.9, 2.7, "ชั้นบริการ — Backend (FastAPI)")
    c.node("img", 1.45, 4.45, 1.9, 0.95, "ที่เก็บ\nไฟล์ภาพ", "round")
    c.node("api", 4.0, 4.45, 2.3, 0.95, "API + Session\nตรวจไฟล์/สิทธิ์", "round")
    c.node("q", 6.55, 4.45, 2.0, 0.95, "คิวงาน\n(memory / MongoDB)", "round")
    c.node("w", 9.0, 4.45, 1.9, 0.95, "Worker แยกโปรเซส\nlease + heartbeat", "round", fs=9)
    c.layer(0.3, 6.15, 9.9, 1.55, "ชั้นประมวลผลภาพ — แพ็กเกจ ai/")
    c.node("lay", 2.2, 7.1, 2.1, 0.62, "Layout JSON", "round")
    c.node("bun", 4.9, 7.1, 2.6, 0.62, "Model bundle\n(bundle.json + weights)", "round", fs=9)
    c.node("ins", 9.0, 7.1, 2.3, 0.62, "Inspector", "round", bold=True)
    c.line([("ui", "b", -1.25), ("api", "t")], "REST /api/v1 (poll สถานะ)", lpos=(4.15, 2.55), ha="left")
    c.line([("api", "l"), ("img", "r")])
    c.line([("api", "r"), ("q", "l")])
    c.line([("q", "r"), ("w", "l")])
    c.line([("w", "b"), ("ins", "t")])
    c.line([("ins", "l"), ("bun", "r")])
    c.line([("bun", "l"), ("lay", "r")], dashed=True)
    c.save("flow_architecture.png")


def pipeline():
    c = Chart(12.8, 3.6)
    c.node("in", 1.2, 1.0, 1.9, 1.0, "ภาพถ่าย\n+ จุดอ้างอิง 4 จุด", "io", fs=9.5)
    names = [("r", "1 Rectify\nHomography"), ("d", "2 Detect\nกรอบปุ่ม"), ("rd", "3 Read\nอ่านตัวอักษร"),
             ("m", "4 Match\nปุ่ม ↔ ช่อง"), ("dc", "5 Decide\nถูก/ผิด/ไม่แน่ใจ")]
    xs = [3.45, 5.5, 7.55, 9.6, 11.65]
    c.line([("in", "r"), (xs[0] - 0.8, 1.0)])
    for (k, t), x in zip(names, xs):
        c.node(k, x, 1.0, 1.55, 0.95, t, "rect", fs=9.5, bold=False)
    for a, b in zip(names[:-1], names[1:]):
        c.line([(a[0], "r"), (b[0], "l")])
    c.node("lay", 10.6, 2.8, 2.6, 0.7, "Layout (26 ช่อง)", "round")
    c.line([("lay", "t", -0.55), ("m", "b")])
    c.line([("lay", "t", 0.9), ("dc", "b", -0.2)])
    c.save("flow_pipeline.png")


def sequence():
    parts = ["ผู้ใช้", "Frontend", "Backend API", "คิวงาน/ฐานข้อมูล", "Worker", "Inspector"]
    xs = [1.0, 3.0, 5.3, 7.6, 9.8, 11.7]
    H = 9.6
    c = Chart(12.8, H)
    for p, x in zip(parts, xs):
        c.node("p" + p, x, 0.5, 1.7, 0.55, p, "rect", fs=9.5, bold=True)
        c.line([(x, 0.78), (x, H - 0.3)], dashed=True, arrow=False, lw=0.8)
    X = dict(zip(parts, xs))
    msgs = [
        ("ผู้ใช้", "Frontend", "ถ่ายภาพ/เลือกไฟล์", False),
        ("Frontend", "Backend API", "POST /uploads (ภาพ)", False),
        ("Backend API", "Frontend", "201 image_id", True),
        ("ผู้ใช้", "Frontend", "แตะ Q, P, M, Z", False),
        ("Frontend", "Backend API", "POST /inspections", False),
        ("Backend API", "คิวงาน/ฐานข้อมูล", "สร้างงาน queued", False),
        ("Backend API", "Frontend", "202 inspection_id", True),
        ("Worker", "คิวงาน/ฐานข้อมูล", "claim งาน (atomic) + lease", False),
        ("Worker", "Inspector", "inspect(ภาพ, 4 จุด)", False),
        ("Inspector", "Worker", "ผลรายช่อง", True),
        ("Worker", "คิวงาน/ฐานข้อมูล", "finish (ตรวจ contract)", False),
        ("Frontend", "Backend API", "GET /inspections/{id}  (วน poll)", False),
        ("Backend API", "Frontend", "status + stage / ผลลัพธ์", True),
        ("Frontend", "ผู้ใช้", "แสดงผลซ้อนบนภาพ", True),
    ]
    y = 1.45
    ys = {}
    for i, (a, b, t, dash) in enumerate(msgs):
        ys[i] = y
        x0, x1 = X[a], X[b]
        d = 0.0
        c.line([(x0, y), (x1, y)], dashed=dash)
        c.text((x0 + x1) / 2, y - 0.07, t, ha="center", va="bottom", fontsize=8.8)
        y += 0.6
    # กรอบ loop poll (ข้อความที่ 11–12)
    ya, yb = ys[11] - 0.42, ys[12] + 0.22
    c.ax.add_patch(FancyBboxPatch((2.0, ya), 4.9, yb - ya, boxstyle="square,pad=0", fc="none", ec="black", lw=0.9,
                                  ls=(0, (2, 2)), zorder=0))
    c.text(2.06, ya + 0.04, "loop", ha="left", va="top", fontsize=8.5, fontweight="bold")
    c.save("flow_sequence.png")


def stages():
    c = Chart(14.0, 5.2)
    c.node("q1", 1.3, 1.5, 2.1, 0.85, "Q1 นำเข้า + Audit\n+ แบ่งชุด", fs=9.5)
    c.node("q2", 4.2, 2.6, 2.1, 0.85, "Q2 ภาพ rectified\n+ ชุดประเมิน S1–S4", fs=9.5)
    c.node("q3", 7.2, 1.0, 1.9, 0.75, "Q3 ทดลอง OCR", fs=9.5)
    c.node("q4", 7.2, 2.6, 1.9, 0.75, "Q4 ฝึก YOLO11n", fs=9.5)
    c.node("q5", 7.2, 4.2, 1.9, 0.75, "Q5 ฝึก Faster R-CNN", fs=9.5)
    c.node("q3b", 10.2, 1.0, 1.9, 0.75, "Q3b ฝึกตัวจำแนก\nA–Z + OTHER", fs=9.5)
    c.node("q6", 10.2, 2.6, 2.3, 0.95, "Q6 ประเมิน + จูน\nthreshold + สร้าง bundle", fs=9.5)
    c.node("q7", 12.9, 2.6, 1.7, 0.95, "Q7 ทดสอบ Test\n(ล็อก — รันครั้งเดียว)", "rect", fs=8.8, bold=True)
    c.line([("q1", "r"), (4.2, 1.5), ("q2", "t")])
    c.line([("q2", "t", 0.4), (4.6, 1.0), ("q3", "l")])
    c.line([("q2", "r"), ("q4", "l")])
    c.line([("q2", "b", 0.4), (4.6, 4.2), ("q5", "l")])
    c.line([("q1", "t"), (1.3, 0.25), (10.2, 0.25), ("q3b", "t")], "ใช้ข้อมูล Q1", lpos=(5.5, 0.25))
    c.line([("q3", "r"), ("q3b", "l")])
    c.line([("q3b", "b"), ("q6", "t")])
    c.line([("q4", "r"), ("q6", "l")])
    c.line([("q5", "r"), (10.2, 4.2), ("q6", "b")])
    c.line([("q6", "r"), ("q7", "l")])
    c.save("flow_stages.png")


def reader():
    c = Chart(7.6, 8.2)
    c.node("a", 3.1, 0.7, 4.0, 0.8, "ทดลอง PP-OCRv5\nสำเร็จรูป (Q3)", fs=10)
    c.node("b", 3.1, 2.55, 4.0, 1.6, "ผ่านเกณฑ์?\nreject ≤ 10%", "diamond", fs=10)
    c.node("c", 3.1, 4.65, 4.3, 0.95, "ออกแบบตัวจำแนกเฉพาะทาง\nResNet18 · 27 คลาส (Q3b)", fs=10)
    c.node("d", 3.1, 6.05, 4.3, 0.75, "เพิ่มอักษรไทยสังเคราะห์ตอนฝึก", fs=10)
    c.node("e", 3.1, 7.4, 4.3, 0.75, "ใช้เป็นตัวอ่านหลักใน Q6", "term", fs=10)
    c.node("ok", 6.6, 2.55, 1.3, 0.7, "ใช้ OCR", "term", fs=9)
    c.line([("a", "b"), ("b", "t")])
    c.line([("a", "b"), ("b", "t")])
    c.line([("b", "b"), ("c", "t")], "ไม่ผ่านทุกแบบ", lpos=(3.2, 3.85), ha="left")
    c.line([("b", "r"), ("ok", "l")], "ผ่าน", lpos=(5.75, 2.45))
    c.line([("c", "b"), ("d", "t")])
    c.line([("d", "b"), ("e", "t")])
    c.save("flow_reader.png")


def decide():
    c = Chart(10.2, 12.0)
    c.node("s", 3.8, 0.55, 2.0, 0.6, "ช่อง j", "term")
    ds = [("d1", 2.15, "มีกรอบถูกจับคู่?"), ("d2", 4.2, "จับคู่กำกวม?"),
          ("d3", 6.25, "อ่านเป็นตัวอักษร\nA–Z ได้?"), ("d4", 8.3, "score ≥\nocr_score_min?")]
    for k, y, t in ds:
        c.node(k, 3.8, y, 3.2, 1.35, t, "diamond", fs=9.5)
    c.line([("s", "b"), ("d1", "t")])
    for (k1, _, _), (k2, _, _) in zip(ds[:-1], ds[1:]):
        c.line([(k1, "b"), (k2, "t")])
    # label ที่เส้นลงล่างของแต่ละ decision
    c.text(3.95, 3.18, "ใช่", fontsize=8.5, ha="left")
    c.text(3.95, 5.23, "ไม่", fontsize=8.5, ha="left")
    c.text(3.95, 7.28, "ใช่", fontsize=8.5, ha="left")
    c.text(3.95, 9.33, "ใช่", fontsize=8.5, ha="left")
    c.node("u1", 8.4, 2.15, 3.2, 0.8, "uncertain\ndetection_unavailable", fs=9)
    c.node("u2", 8.4, 4.2, 3.2, 0.8, "uncertain\nmapping_ambiguous", fs=9)
    c.node("u3", 8.4, 6.25, 3.2, 0.8, "uncertain\nocr_invalid_label", fs=9)
    c.node("u4", 8.4, 8.3, 3.2, 1.05, "uncertain\nocr_low_confidence\n(เก็บ candidate_label เป็นคำใบ้)", fs=9)
    c.line([("d1", "r"), ("u1", "l")], "ไม่", lpos=(5.9, 2.1))
    c.line([("d2", "r"), ("u2", "l")], "ใช่", lpos=(5.9, 4.15))
    c.line([("d3", "r"), ("u3", "l")], "ไม่", lpos=(5.9, 6.2))
    c.line([("d4", "r"), ("u4", "l")], "ไม่", lpos=(5.9, 8.25))
    c.node("d5", 3.8, 10.2, 3.2, 1.3, "ตรงกับ\nexpected_label?", "diamond", fs=9.5)
    c.line([("d4", "b"), ("d5", "t")])
    c.node("ok", 1.5, 11.5, 2.2, 0.62, "correct", "term", bold=True)
    c.node("bad", 6.3, 11.5, 3.6, 0.62, "incorrect + observed_label", "term", bold=True, fs=9.5)
    c.line([("d5", "l"), (1.5, 10.2), ("ok", "t")], "ตรง", lpos=(2.1, 10.15))
    c.line([("d5", "r"), (6.3, 10.2), ("bad", "t")], "ไม่ตรง", lpos=(5.5, 10.15))
    c.save("flow_decide.png")


def evidence():
    c = Chart(11.6, 4.8)
    c.layer(0.3, 0.3, 6.0, 4.1, "หลักฐาน (Evidence) — ช้า · แคชได้")
    c.node("det", 1.7, 1.6, 2.0, 0.8, "Detector\n(กรอบ + score)", "round", fs=9)
    c.node("rd", 1.7, 3.2, 2.0, 0.8, "Reader\n(ตัวอักษร + score)", "round", fs=9)
    c.node("ev", 4.9, 2.4, 2.2, 1.3, "Evidence\nกรอบ · score ·\nตัวอักษร · score", "rect", fs=9)
    c.line([("det", "r"), (3.3, 1.6), (3.3, 2.05), ("ev", "l", -0.35)])
    c.line([("rd", "r"), (3.3, 3.2), (3.3, 2.75), ("ev", "l", 0.35)])
    c.layer(7.3, 0.3, 4.0, 4.1, "การตัดสิน — เร็ว · ฟังก์ชันบริสุทธิ์")
    c.node("dec", 9.3, 2.4, 2.4, 0.95, "decide(evidence,\nlayout, params)", "rect", fs=9.5, bold=True)
    c.line([("ev", "r"), ("dec", "l")], "คำนวณ", lpos=(6.8, 2.2), fs=8)
    c.node("thr", 9.3, 3.55, 3.3, 0.55, "threshold หลายร้อยชุด (Params)", "round", fs=9)
    c.line([("thr", "t"), ("dec", "b")])
    c.save("flow_evidence.png")


def inspector():
    c = Chart(10.5, 14.4)
    X = 4.2
    c.node("s", X, 0.45, 2.0, 0.55, "inspect()", "term", bold=True)
    c.node("d1", X, 1.75, 3.5, 1.3, "ภาพถูกต้อง?\nHxWx3 uint8", "diamond", fs=9.5)
    c.node("e1", 8.6, 1.75, 3.2, 0.7, "ValueError", "term", fs=9)
    c.node("d2", X, 3.55, 3.6, 1.45, "4 จุดถูกต้อง?\nนูน/ในภาพ/พื้นที่/ลำดับ", "diamond", fs=9)
    c.node("e2", 8.6, 3.55, 3.2, 0.8, "InvalidReferencePoints\n→ INVALID_CORNERS", "term", fs=8.8)
    c.node("r", X, 5.2, 4.2, 0.8, "Rectify: H = S·H(px→u)\nwarpPerspective → canvas", fs=9.5)
    c.node("q", X, 6.4, 4.2, 0.7, "ตรวจคุณภาพภาพ (blur/exposure) → ธง", fs=9.5)
    c.node("d3", X, 7.9, 3.0, 1.2, "detector?", "diamond", fs=9.5)
    c.node("g", 1.5, 9.35, 2.6, 0.7, "กรอบคงที่จาก layout", fs=9)
    c.node("h", 7.6, 9.35, 2.6, 0.7, "predict บน canvas", fs=9)
    c.node("m", X, 10.45, 4.2, 0.65, "match: จับคู่ด้วยตำแหน่ง", fs=9.5)
    c.node("rd", X, 11.45, 4.6, 0.7, "อ่านตัวอักษรเฉพาะกรอบที่จับคู่ (≤ 26 ครอป)", fs=9.2)
    c.node("dc", X, 12.45, 4.2, 0.65, "decide + suggest", fs=9.5)
    c.node("po", X, 13.4, 5.2, 0.7, "แปลง polygon กลับภาพต้นฉบับ\nใส่ warnings + timings_ms", fs=9.2)
    c.node("end", 8.6, 13.4, 1.9, 0.6, "result JSON", "term", bold=True, fs=9)
    c.line([("s", "b"), ("d1", "t")])
    c.line([("d1", "r"), ("e1", "l")], "ไม่", lpos=(6.45, 1.7))
    c.line([("d1", "b"), ("d2", "t")], "ใช่", lpos=(4.3, 2.5), ha="left")
    c.line([("d2", "r"), ("e2", "l")], "ไม่", lpos=(6.45, 3.5))
    c.line([("d2", "b"), ("r", "t")], "ใช่", lpos=(4.3, 4.45), ha="left")
    c.line([("r", "b"), ("q", "t")])
    c.line([("q", "b"), ("d3", "t")])
    c.line([("d3", "l"), (1.5, 7.9), ("g", "t")], "baseline", lpos=(2.4, 7.82))
    c.line([("d3", "r"), (7.6, 7.9), ("h", "t")], "yolo / frcnn", lpos=(6.7, 7.82))
    c.line([("g", "b"), (1.5, 10.45), ("m", "l")])
    c.line([("h", "b"), (7.6, 10.45), ("m", "r")])
    c.line([("m", "b"), ("rd", "t")])
    c.line([("rd", "b"), ("dc", "t")])
    c.line([("dc", "b"), ("po", "t")])
    c.line([("po", "r"), ("end", "l")])
    c.save("flow_inspector.png")


def worker():
    c = Chart(11.6, 14.6)
    X = 4.0
    c.node("s", X, 0.45, 2.2, 0.55, "เริ่ม worker", "term", bold=True)
    c.node("a", X, 1.5, 4.6, 0.75, "โหลด Inspector ครั้งเดียว\nลงทะเบียน bundle", fs=9.5)
    c.node("b", X, 2.65, 4.2, 0.7, "กู้ lease ที่หมดอายุ (requeue / failed)", fs=9.5)
    c.node("c", X, 3.7, 4.2, 0.65, "รัน retention ตามช่วงเวลา", fs=9.5)
    c.node("d", X, 4.75, 4.6, 0.7, "claim งาน queued เก่าสุด\n(atomic + lease)", fs=9.5)
    c.node("e", X, 6.1, 2.6, 1.15, "มีงาน?", "diamond", fs=9.5)
    c.node("f", X, 7.55, 5.0, 0.85, "ส่ง heartbeat ต่อ lease\nขณะ inspect() ทำงานใน thread", fs=9.5)
    c.node("g", X, 9.15, 4.2, 1.5, "ผลผ่านตรวจ contract?\ncorrect+incorrect+\nuncertain = 26", "diamond", fs=8.8)
    c.node("h", 8.9, 9.15, 3.2, 0.7, "failed\nPROCESSING_FAILED", fs=9)
    c.node("k", X, 11.05, 4.6, 0.7, "finish: completed / rejected / failed", fs=9.5)
    c.node("l", X, 12.55, 3.4, 1.25, "ยังเป็นเจ้าของ\nlease?", "diamond", fs=9.5)
    c.node("m", 1.35, 13.95, 2.2, 0.65, "บันทึกผล", "term", fs=9.5)
    c.node("n", 6.9, 13.95, 2.2, 0.65, "ทิ้งผล", "term", fs=9.5)
    c.line([("s", "b"), ("a", "t")])
    c.line([("a", "b"), ("b", "t")])
    c.line([("b", "b"), ("c", "t")])
    c.line([("c", "b"), ("d", "t")])
    c.line([("d", "b"), ("e", "t")])
    c.line([("e", "b"), ("f", "t")], "มี", lpos=(4.1, 6.95), ha="left")
    c.line([("e", "r"), (7.0, 6.1), (7.0, 2.65), ("b", "r")], "ไม่มี", lpos=(5.5, 6.05), ha="left")
    c.line([("f", "b"), ("g", "t")])
    c.line([("g", "r"), ("h", "l")], "ไม่", lpos=(6.55, 9.1))
    c.line([("g", "b"), ("k", "t")], "ใช่", lpos=(4.1, 10.2), ha="left")
    c.line([("h", "b"), (8.9, 11.05), ("k", "r")])
    c.line([("k", "b"), ("l", "t")])
    c.line([("l", "l"), (1.35, 12.55), ("m", "t")], "ใช่", lpos=(2.3, 12.5))
    c.line([("l", "r"), (6.9, 12.55), ("n", "t")], "ไม่", lpos=(5.7, 12.5))
    # วนกลับ
    c.line([("m", "l"), (0.4, 13.95), (0.4, 2.65), ("b", "l")], dashed=True)
    c.line([("n", "r"), (11.0, 13.95), (11.0, 2.65), (10.0, 2.65)], dashed=True, arrow=False)
    c.line([(10.0, 2.65), (7.0, 2.65)], dashed=True, arrow=False)
    c.text(0.5, 8.3, "วนรอบถัดไป", rotation=90, fontsize=8.5, ha="left", va="center")
    c.save("flow_worker.png")


def fsm():
    c = Chart(16.6, 10.9)
    W, Hh = 2.2, 0.75
    y0 = 2.8
    c.node("idle", 1.6, y0, W, Hh, "idle", "round", bold=True)
    c.node("prev", 6.0, y0, W, Hh, "preview", "round", bold=True)
    c.node("up", 9.4, y0, W, Hh, "uploading", "round", bold=True)
    c.node("cal", 12.8, y0, W, Hh, "calibrating", "round", bold=True)
    c.node("cam", 1.6, 5.4, 2.6, Hh, "camera_permission", "round", fs=9.3)
    c.node("que", 12.8, 4.6, W, Hh, "queued", "round", bold=True)
    c.node("proc", 12.8, 6.3, W, Hh, "processing", "round", bold=True)
    c.node("comp", 7.0, 9.0, W, Hh, "completed", "round", bold=True)
    c.node("rej", 10.6, 9.0, W, Hh, "rejected", "round", bold=True)
    c.node("fail", 14.2, 9.0, W, Hh, "failed", "round", bold=True)
    # จุดเริ่มต้น
    c.ax.plot(0.9, 1.75, "o", color="black", ms=7, zorder=2)
    c.line([(0.9, 1.78), ("idle", "t", -0.7)])
    # แถวหลัก
    c.line([("idle", "r"), ("prev", "l")], "IMAGE_SELECTED", lpos=(3.8, y0 - 0.08))
    c.line([("prev", "r"), ("up", "l")], "UPLOAD", lpos=(7.7, y0 - 0.08))
    c.line([("up", "r"), ("cal", "l")], "UPLOADED", lpos=(11.1, y0 - 0.08))
    c.arc(("up", "b", -0.4), ("prev", "b", 0.4), rad=-0.5, label="UPLOAD_FAILED", lpos=(7.7, 3.95))
    c.arc(("prev", "t", -0.4), ("idle", "t", 0.4), rad=0.55, label="RETAKE", lpos=(3.8, 1.55))
    c.line([("cal", "t", 0.4), (13.2, 0.5), (2.3, 0.5), ("idle", "t", 0.7)], "RETAKE", lpos=(8.0, 0.5))
    # กล้อง
    c.line([("idle", "b", -0.45), ("cam", "t", -0.45)], "OPEN_CAMERA", lpos=(1.0, 4.1), ha="right")
    c.line([("cam", "t", 0.45), ("idle", "b", 0.45)], "CLOSE_CAMERA", lpos=(2.1, 4.1), ha="left", dashed=True)
    c.line([("cam", "r"), (6.0, 5.4), ("prev", "b")], "IMAGE_SELECTED", lpos=(4.3, 5.32))
    # แถวประมวลผล
    c.line([("cal", "b"), ("que", "t")], "SUBMITTED", lpos=(12.95, 3.9), ha="left")
    c.line([("que", "b"), ("proc", "t")], "STARTED", lpos=(12.95, 5.55), ha="left")
    c.line([("proc", "b"), (12.8, 7.6)], arrow=False)
    c.line([(7.0, 7.6), (14.2, 7.6)], arrow=False)
    c.line([(7.0, 7.6), ("comp", "t")], "COMPLETED", lpos=(7.15, 8.2), ha="left")
    c.line([(10.6, 7.6), ("rej", "t")], "REJECTED", lpos=(10.75, 8.2), ha="left")
    c.line([(14.2, 7.6), ("fail", "t")], "FAILED", lpos=(14.35, 8.2), ha="left")
    # กลับ
    c.line([("comp", "l"), (0.2, 9.0), (0.2, y0), ("idle", "l")], "RETAKE", lpos=(0.3, 7.0), ha="left")
    c.line([("rej", "b"), (10.6, 10.05), (15.9, 10.05), (15.9, y0), ("cal", "r")], "RECALIBRATE (ใช้ภาพเดิม แตะจุดใหม่)", lpos=(12.6, 10.05))
    c.line([("fail", "b"), (14.2, 10.05)], arrow=False)
    c.save("flow_state_machine.png")


def matching_example():
    c = Chart(12.6, 5.6)
    xs = [4.0, 5.5, 7.0, 8.5, 10.0]
    slots = ["A", "S", "D", "F", "G"]
    seen = ["S", "A", "D", "F", "G"]
    c.text(0.3, 1.2, "ช่อง (ตำแหน่งที่ควรเป็น)\nexpected_label", fontsize=10, va="center", ha="left", fontweight="bold")
    c.text(0.3, 3.1, "ปุ่มที่ตรวจพบ\nตัวอักษรที่อ่านได้", fontsize=10, va="center", ha="left", fontweight="bold")
    c.text(0.3, 4.6, "ผลตัดสิน", fontsize=10, va="center", ha="left", fontweight="bold")
    for i, (x, a, b) in enumerate(zip(xs, slots, seen)):
        c.node(f"s{i}", x, 1.2, 1.1, 0.75, a, "rect", fs=15, bold=True)
        c.node(f"d{i}", x, 3.1, 1.1, 0.75, b, "rect", fs=15, bold=True, fill="#f2f2f2")
        c.line([(x, 2.72), (x, 1.58)], dashed=False)
        ok = a == b
        c.text(x, 4.6, "correct" if ok else "incorrect", fontsize=10, ha="center", va="center",
               fontweight="normal" if ok else "bold")
        if not ok:
            c.ax.add_patch(FancyBboxPatch((x - 0.62, 4.28), 1.24, 0.64, boxstyle="round,pad=0,rounding_size=0.08", fc="none", ec="black", lw=1.4, zorder=2))
    c.text(2.9, 2.15, "จับคู่ด้วยตำแหน่ง\n(ใกล้ที่สุด · Hungarian)", fontsize=8.8, ha="right", va="center")
    c.text(10.0, 0.25, "", fontsize=1)
    c.node("sug", 11.7, 4.6, 1.8, 0.95, "คำแนะนำ: swap_pair\nสลับช่อง A ↔ S", "round", fs=9.5, bold=True)
    c.save("flow_matching_example.png")


if __name__ == "__main__":
    arch()
    pipeline()
    sequence()
    stages()
    reader()
    decide()
    evidence()
    inspector()
    worker()
    fsm()
    matching_example()
