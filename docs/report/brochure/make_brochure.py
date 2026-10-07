"""แผ่นพับ KeyCheck (A4 แนวนอน พับสาม หน้า-หลัง) — ล้อเนื้อหาจากรายงานใน docs/report

รัน:  .venv-ml/bin/python docs/report/brochure/make_brochure.py
ผลลัพธ์: docs/report/brochure/keycheck_brochure.pdf (2 หน้า) + brochure_outside.png / brochure_inside.png
การพิมพ์: พิมพ์หน้า 1 (ด้านนอก) แล้วพิมพ์หน้า 2 (ด้านใน) ด้านหลังของแผ่นเดียวกัน (พลิกตามขอบสั้น) แล้วพับสาม
ข้อความใน [ ] คือช่องที่ต้องกรอกเอง
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = Path(__file__).resolve().parent
FIG = HERE.parent / "figures"
FONT_DIR = Path("/usr/share/fonts/truetype/noto")
for f in ("NotoSansThai-Regular.ttf", "NotoSansThai-Bold.ttf"):
    fm.fontManager.addfont(str(FONT_DIR / f))
plt.rcParams["font.family"] = ["Noto Sans Thai", "DejaVu Sans"]
plt.rcParams["pdf.fonttype"] = 42

W, H = 11.69, 8.27          # A4 แนวนอน (นิ้ว)
PW = W / 3                  # ความกว้างหนึ่งช่อง
M = 0.30                    # ขอบในของช่อง
K = 1.22                    # ตัวคูณขนาดตัวอักษร/กล่อง
ACC = "#0f4c5c"
GRAY = "#555555"
LIGHT = "#eef3f4"


class Panel:
    def __init__(self, fig, idx, fill=None):
        self.fig = fig
        self.ax = fig.add_axes([idx * PW / W, 0, PW / W, 1])
        self.ax.set_xlim(0, PW)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")
        if fill:
            self.ax.add_patch(Rectangle((0, 0), PW, H, fc=fill, ec="none", zorder=0))
        self.w = PW - 2 * M
        self.r = fig.canvas.get_renderer()

    # ---------- วัดความกว้าง/ตัดบรรทัด
    def _tw(self, s, fs, bold=False):
        t = self.ax.text(0, 0, s, fontsize=fs, fontweight="bold" if bold else "normal")
        bb = t.get_window_extent(self.r)
        t.remove()
        return bb.width / self.fig.dpi

    def wrap(self, text, fs, width, bold=False):
        lines = []
        for para in text.split("\n"):
            cur = ""
            for tok in para.split(" "):
                trial = (cur + " " + tok).strip()
                if self._tw(trial, fs, bold) <= width:
                    cur = trial
                    continue
                if cur:
                    lines.append(cur)
                cur = ""
                while self._tw(tok, fs, bold) > width:      # คำยาวเกิน: ตัดตามตัวอักษร
                    k = len(tok)
                    while k > 1 and self._tw(tok[:k], fs, bold) > width:
                        k -= 1
                    lines.append(tok[:k])
                    tok = tok[k:]
                cur = tok
            lines.append(cur)
        return lines

    # ---------- องค์ประกอบ
    def heading(self, y, text, fs=13, rule=True):
        fs *= K
        self.ax.text(M, y, text, fontsize=fs, fontweight="bold", color=ACC, va="top", zorder=3)
        y += fs / 72 * 1.5
        if rule:
            self.ax.plot([M, M + self.w], [y, y], color=ACC, lw=1.2, zorder=3)
            y += 0.1
        return y

    def para(self, y, text, fs=9, bullet=False, bold=False, color="black", gap=0.07, indent=0.0, lh=1.5):
        fs *= K
        x = M + indent + (0.16 if bullet else 0)
        width = self.w - indent - (0.16 if bullet else 0)
        for i, ln in enumerate(self.wrap(text, fs, width, bold)):
            if bullet and i == 0:
                self.ax.text(M + indent + 0.02, y, "•", fontsize=fs, va="top", color=ACC, zorder=3)
            self.ax.text(x, y, ln, fontsize=fs, va="top", fontweight="bold" if bold else "normal", color=color, zorder=3)
            y += fs / 72 * lh
        return y + gap

    def image(self, path, y, width=None, max_h=None, crop_top=0.0):
        im = mpimg.imread(path)
        im = im[int(im.shape[0] * crop_top):]
        h0, w0 = im.shape[:2]
        w = width or self.w
        h = w * h0 / w0
        if max_h and h > max_h:
            h, w = max_h, max_h * w0 / h0
        x0 = M + (self.w - w) / 2
        self.ax.imshow(im, extent=(x0, x0 + w, y + h, y), aspect="auto", zorder=2)
        self.ax.add_patch(Rectangle((x0, y), w, h, fc="none", ec="#999999", lw=0.6, zorder=3))
        return y + h + 0.06

    def card(self, y, big, small, h=0.95):
        h *= K
        self.ax.add_patch(FancyBboxPatch((M, y), self.w, h, boxstyle="round,pad=0,rounding_size=0.08", fc=LIGHT, ec="none", zorder=1))
        self.ax.text(M + 0.14, y + 0.12, big, fontsize=15 * K, fontweight="bold", color=ACC, va="top", zorder=3)
        yy = y + 0.12 + 15 * K / 72 * 1.4
        for ln in self.wrap(small, 8.2 * K, self.w - 0.28):
            self.ax.text(M + 0.14, yy, ln, fontsize=8.2 * K, va="top", color=GRAY, zorder=3)
            yy += 8.2 * K / 72 * 1.4
        return y + h + 0.12

    def step(self, y, n, title, desc, h=0.52):
        h *= K
        self.ax.add_patch(FancyBboxPatch((M, y), self.w, h, boxstyle="round,pad=0,rounding_size=0.06", fc="white", ec=ACC, lw=1.0, zorder=2))
        self.ax.add_patch(Rectangle((M, y), 0.4, h, fc=ACC, ec="none", zorder=2))
        self.ax.text(M + 0.2, y + h / 2, str(n), color="white", fontsize=12 * K, fontweight="bold", ha="center", va="center", zorder=3)
        self.ax.text(M + 0.52, y + 0.08, title, fontsize=9.3 * K, fontweight="bold", va="top", zorder=3)
        self.ax.text(M + 0.52, y + 0.08 + 9.3 * K / 72 * 1.45, desc, fontsize=8 * K, color=GRAY, va="top", zorder=3)
        return y + h

    def arrow(self, y, h=0.16):
        x = M + 0.2
        self.ax.annotate("", xy=(x, y + h), xytext=(x, y), arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1.0), zorder=2)
        return y + h


def folds(fig):
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    for k in (1, 2):
        for y0, y1 in ((0, 0.12), (H - 0.12, H)):
            ax.plot([k * PW, k * PW], [y0, y1], color="#999999", lw=0.5)
    return ax


def new_page():
    fig = plt.figure(figsize=(W, H), dpi=200, facecolor="white")
    fig.canvas.draw()
    return fig


# =========================================================================================================
def outside():
    fig = new_page()
    # ----- ช่อง 1: ปีกพับใน (ข้อจำกัดและงานต่อ)
    p = Panel(fig, 0)
    y = 0.45
    y = p.heading(y, "ข้อจำกัดที่ควรรู้")
    for t in ("ผลทั้งหมดมาจากข้อมูลตัวแทน (ภาพคีย์บอร์ด QWERTZ จาก Kaggle) บนชุด Validation เท่านั้น",
              "ยังไม่ได้รันชุด Test และยังไม่ได้ทดสอบกับภาพถ่ายคีย์บอร์ด QWERTY จริง",
              "อักษรไทยบนปุ่มเป็นแบบสังเคราะห์ ยังพิสูจน์กับปุ่มไทยจริงไม่ได้",
              "ผู้ใช้ต้องแตะจุดอ้างอิง 4 จุดเอง",
              "รองรับเฉพาะ QWERTY แถวเยื้อง ตัวอักษร A–Z และคีย์บอร์ดแบบ Ortholinear ที่แตะจุดถูกยังไม่ถูกปฏิเสธ"):
        y = p.para(y, t, fs=9, bullet=True)
    y += 0.12
    y = p.heading(y, "ก้าวต่อไป")
    for t in ("เก็บภาพคีย์บอร์ด QWERTY จริง 8–12 รุ่น (รวมแบบไทย-อังกฤษ)",
              "รันชุด Test ครั้งเดียว และรายงานผลแยกยี่ห้อที่เคยเห็น/ไม่เคยเห็น",
              "ตรวจหามุมคีย์บอร์ดอัตโนมัติ ลดการแตะ 4 จุด",
              "ทดสอบกับผู้ใช้จริงและ layout อื่น"):
        y = p.para(y, t, fs=9, bullet=True)
    print("outside panel1 end y", round(y, 2)); assert y < H - 0.4

    # ----- ช่อง 2: ปกหลัง
    p = Panel(fig, 1, fill=LIGHT)
    y = 0.6
    y = p.heading(y, "เทคโนโลยีที่ใช้", rule=True)
    for t in ("AI: Python · OpenCV · PyTorch · YOLO11n · ResNet18 · SciPy (Hungarian)",
              "Backend: FastAPI · MongoDB · Worker แยกโปรเซส",
              "Frontend: SvelteKit · TypeScript · Tailwind"):
        y = p.para(y, t, fs=9, bullet=True)
    y += 0.12
    y = p.heading(y, "รายงานฉบับเต็ม")
    y = p.para(y, "รายละเอียดการออกแบบ การพัฒนา ผลการทดลอง และโค้ด อยู่ในโฟลเดอร์ docs/report ของโปรเจกต์", fs=9)
    y += 0.25
    y = p.heading(y, "ผู้จัดทำ")
    for t in ("[ชื่อ-สกุล] [รหัสนักศึกษา]", "[ชื่อ-สกุล] [รหัสนักศึกษา]", "อาจารย์ที่ปรึกษา: [ชื่ออาจารย์]",
              "รายวิชา [รหัสวิชา] [ชื่อรายวิชา]", "[คณะ / มหาวิทยาลัย]", "ติดต่อ: [อีเมล]"):
        y = p.para(y, t, fs=9, gap=0.03)
    print("outside panel2 end y", round(y, 2)); assert y < H - 0.4

    # ----- ช่อง 3: ปกหน้า
    p = Panel(fig, 2)
    p.ax.add_patch(Rectangle((0, 0), PW, 1.55, fc=ACC, ec="none", zorder=0))
    p.ax.text(M, 0.4, "MINI PROJECT", fontsize=9, color="#bcd6dc", fontweight="bold", va="top", zorder=3)
    p.ax.text(M, 0.68, "KeyCheck", fontsize=34, color="white", fontweight="bold", va="top", zorder=3)
    y = 1.78
    y = p.para(y, "ระบบตรวจคีย์แคปผิดตำแหน่ง\nจากภาพถ่ายใบเดียว ด้วย AI", fs=13, bold=True, color=ACC, lh=1.5)
    y += 0.05
    y = p.image(FIG / "s3_swap_example_1.png", y, width=p.w, crop_top=0.06)
    y = p.para(y, "ภาพบน: ต้นฉบับ  ภาพล่าง: หลังสลับปุ่ม 2 ตัว (ภาพจำลองจากชุดข้อมูล)", fs=7.5, color=GRAY, gap=0.15)
    y = p.para(y, "ถ่ายภาพ → แตะ 4 จุด → รู้ทันทีว่าปุ่มไหนถูก ผิด หรือไม่แน่ใจ พร้อมแนะนำให้สลับปุ่มคู่ไหน", fs=10, gap=0.2)
    p.ax.text(M, H - 0.55, "[ชื่อทีม] · [รายวิชา] · [ภาคการศึกษา/ปี]", fontsize=8.5, color=GRAY, va="top", zorder=3)
    print("outside panel3 end y", round(y, 2)); assert y < H - 0.75
    folds(fig)
    return fig


def inside():
    fig = new_page()
    # ----- ช่อง A: ปัญหา + แนวคิด
    p = Panel(fig, 0)
    y = 0.45
    y = p.heading(y, "ปัญหาที่ต้องการแก้")
    for t in ("ถอดคีย์แคปไปทำความสะอาดแล้วใส่กลับผิดช่อง เพราะปุ่มตัวอักษรหน้าตาและขนาดเหมือนกัน",
              "ตรวจด้วยตาช้า และพลาดง่ายเมื่อผิดเพียงหนึ่งคู่จาก 26 ตัว",
              "ตัวอักษรบนปุ่มเป็นตัวเดียว ฟอนต์หลากหลาย มีไฟ RGB และบางรุ่นมีอักษรไทยร่วม"):
        y = p.para(y, t, fs=9, bullet=True)
    y += 0.1
    y = p.heading(y, "แนวคิด (Solution)")
    y = p.para(y, "ถ่ายภาพคีย์บอร์ด 1 ภาพ แล้วแตะ 4 จุดที่ปุ่ม Q, P, M, Z ระบบจะบอกผลของทั้ง 26 ช่อง", fs=9)
    y += 0.02
    y = p.heading(y, "อัลกอริทึมหลัก", fs=11, rule=False)
    for t in ("Homography (DLT 4 จุด): ปรับภาพเอียงให้เป็นมุมมองตรงในหน่วยปุ่ม",
              "Hungarian algorithm O(N³): จับคู่ปุ่ม–ช่องแบบหนึ่งต่อหนึ่งด้วย “ตำแหน่ง” พร้อม dummy และ gating จึงเห็นปุ่มที่ถูกสลับ",
              "กฎตัดสินหลายชั้น: ไม่แน่ใจ → งดตอบ, layout ไม่เข้ากัน → ปฏิเสธ",
              "กราฟหา swap pair / cycle: แนะนำปุ่มที่ต้องสลับ",
              "Coordinate descent: จูน threshold จาก 124,416 ชุด เหลือประมาณ 100 ชุด",
              "ResNet18 (transfer learning) + YOLO11n: อ่านตัวอักษรและตรวจจับปุ่ม"):
        y = p.para(y, t, fs=8.6, bullet=True, gap=0.05)
    print("inside A end y", round(y, 2)); assert y < H - 0.4

    # ----- ช่อง B: ระบบทำงานอย่างไร
    p = Panel(fig, 1, fill=LIGHT)
    y = 0.45
    y = p.heading(y, "ระบบทำงานอย่างไร")
    steps = [("Rectify", "ปรับภาพให้ตรงด้วย Homography"), ("Detect", "หากรอบคีย์แคปด้วย YOLO11n"),
             ("Read", "อ่านตัวอักษรด้วย ResNet18 (A–Z + อื่น ๆ)"), ("Match", "จับคู่ปุ่มกับ 26 ช่องด้วยตำแหน่ง (Hungarian)"),
             ("Decide", "ถูก / ผิด / ไม่แน่ใจ + แนะนำการสลับ")]
    for i, (a, b) in enumerate(steps, 1):
        y = p.step(y, i, a, b)
        if i < len(steps):
            y = p.arrow(y)
    y += 0.2
    y = p.heading(y, "ผลที่ผู้ใช้เห็น", fs=11, rule=False)
    for t in ("ผลรายช่องซ้อนบนภาพ: ✓ ถูก  ! ผิด  ? ไม่แน่ใจ",
              "คำแนะนำสลับปุ่ม (คู่หรือวงสามปุ่ม) เมื่อมั่นใจครบ",
              "ถ้าแตะจุดผิด/layout ไม่ตรง ระบบปฏิเสธและให้แตะใหม่"):
        y = p.para(y, t, fs=9, bullet=True)
    y += 0.05
    y = p.para(y, "เว็บแอป: SvelteKit + FastAPI ประมวลผลผ่านคิวงาน ตรวจไฟล์และสิทธิ์ผู้ใช้ก่อนเข้าโมเดล", fs=8.5, color=GRAY)
    print("inside B end y", round(y, 2)); assert y < H - 0.4

    # ----- ช่อง C: ผลลัพธ์
    p = Panel(fig, 2)
    y = 0.45
    y = p.heading(y, "ผลลัพธ์ที่ได้")
    y = p.card(y, "0.854  vs  0.815", "mAP50-95 ของตัวตรวจจับ YOLO11n เทียบ Faster R-CNN (ชุด Validation)")
    y = p.card(y, "0.37  vs  ≈9.9 ชม.", "เวลาฝึก YOLO11n เทียบ Faster R-CNN เร็วกว่าราว 27 เท่า (2.58 ล้านพารามิเตอร์)")
    y = p.card(y, "สูงสุด 82%", "OCR สำเร็จรูปอ่านปุ่มได้สูงสุดเพียง 82% และปฏิเสธไม่อ่าน ≥ 16% จึงเปลี่ยนเป็นโมเดลจำแนกเฉพาะทาง")
    y = p.card(y, "1.311  vs  1.204", "คะแนนรวมของ pipeline (เต็ม 1.35): YOLO11n เทียบกับ baseline ที่ไม่ใช้ detector")
    y += 0.02
    y = p.para(y, "ชุดข้อมูล: Kaggle QWERTZ 5,254 ภาพ แบ่งชุดตามยี่ห้อกันข้อมูลรั่ว ผลทั้งหมดเป็นผลบน Validation ของข้อมูลตัวแทน ยังไม่ใช่ความแม่นยำของระบบกับภาพ QWERTY จริง", fs=8.3, color=GRAY)
    print("inside C end y", round(y, 2)); assert y < H - 0.4
    folds(fig)
    return fig


if __name__ == "__main__":
    f1, f2 = outside(), inside()
    with PdfPages(HERE / "keycheck_brochure.pdf") as pdf:
        pdf.savefig(f1, facecolor="white")
        pdf.savefig(f2, facecolor="white")
    f1.savefig(HERE / "brochure_outside.png", dpi=150, facecolor="white")
    f2.savefig(HERE / "brochure_inside.png", dpi=150, facecolor="white")
    print("done")
