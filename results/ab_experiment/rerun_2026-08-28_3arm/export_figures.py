"""Export paper figures (PNG, 2x) from the three-arm HTML pages: combo_grounded.png (bar + box side by side),
qa_topic_bubbles.png, qa_topic_flow.png, qa_composition.png. Writes into this folder's figures/ subfolder only."""
import subprocess, re, sys
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent; OUT = HERE / "figures"; OUT.mkdir(exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def svg_only(html_path, width):
    """Wrap just the <svg> of a page in a bare white document at a fixed CSS width."""
    s = html_path.read_text(); svg = re.search(r"<svg.*?</svg>", s, flags=re.S).group(0)
    h = int(re.search(r'viewBox="0 0 (\d+) (\d+)"', svg).group(2)) * width // int(re.search(r'viewBox="0 0 (\d+)', svg).group(1))
    tmp = OUT / (html_path.stem + ".svgonly.html")
    tmp.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0;background:#fff}}svg{{width:{width}px;height:{h}px;display:block}}</style></head><body>{svg}</body></html>')
    return tmp, width, h

def shot(html_path, width, height, png):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    f"--window-size={width},{height}", f"--screenshot={png}", f"file://{html_path}"], check=True, capture_output=True)

def render_svg(name, width):
    tmp, w, h = svg_only(HERE / f"{name}.html", width); png = OUT / f"{name}.png"; shot(tmp, w, h, png); tmp.unlink(); return png

def main():
    a = render_svg("domain_accuracy_chart", 1280); b = render_svg("relatedness_boxplot", 1280)
    ia, ib = Image.open(a), Image.open(b); H = max(ia.height, ib.height)
    combo = Image.new("RGB", (ia.width + ib.width + 40, H), "white"); combo.paste(ia, (0, H - ia.height)); combo.paste(ib, (ia.width + 40, H - ib.height))
    combo.save(OUT / "combo_grounded.png"); print("combo", combo.size)
    comp = render_svg("golden_set_composition", 1280); (OUT / "qa_composition.png").write_bytes(comp.read_bytes()); print("composition", Image.open(comp).size)
    bub = render_svg("bubble_chart", 1420); print("bubbles", Image.open(bub).size); (OUT / "qa_topic_bubbles.png").write_bytes(bub.read_bytes())
    # flow diagram is JS-rendered: screenshot the whole page
    fl = OUT / "qa_topic_flow.png"; shot(HERE / "golden_set_question_types.html", 1500, 1900, fl)
    im = Image.open(fl); bbox = Image.eval(im.convert("L"), lambda p: 255 - p if p < 245 else 0).getbbox(); im.crop(bbox).save(fl); print("flow", Image.open(fl).size)

if __name__ == "__main__":
    main()
