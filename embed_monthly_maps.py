from pathlib import Path
import base64
import json
import mimetypes
import re

# =========================
# CONFIG
# =========================

HTML_FILE = Path("test.html")
MAP_DIR = Path("monthly_maps")
OUT_FILE = Path("test_embedded.html")

MONTHS = [
    "2024-01", "2024-02", "2024-03", "2024-04",
    "2024-05", "2024-06", "2024-07", "2024-08",
    "2024-09", "2024-10", "2024-11", "2024-12"
]

MAP_SPECS = {
    "sst": {
        "prefix": "sst_anomaly_map_",
        "label": "SST anomaly map"
    },
    "risk": {
        "prefix": "preliminary_heat_risk_map_",
        "label": "Preliminary heat-risk map"
    }
}


# =========================
# EMBED IMAGES AS BASE64
# =========================

def file_to_data_uri(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime is None:
        mime = "image/png"

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def build_embedded_map_object():
    embedded = {
        "sst": {},
        "risk": {}
    }

    missing = []

    for map_type, spec in MAP_SPECS.items():
        for month in MONTHS:
            filename = f"{spec['prefix']}{month}.png"
            path = MAP_DIR / filename

            if not path.exists():
                missing.append(str(path))
                continue

            embedded[map_type][month] = file_to_data_uri(path)

    return embedded, missing


# =========================
# CSS / HTML / JS TO INJECT
# =========================

CSS_BLOCK = r"""
/* ---------- Notebook-generated monthly map viewer start ---------- */
.pretty-map-viewer{
  display:grid;
  grid-template-columns:1fr 340px;
  gap:1rem;
  align-items:start;
  margin-top:1rem;
}

.pretty-map-frame{
  background:white;
  border:1px solid var(--border);
  border-radius:7px;
  padding:1rem;
}

.pretty-map-img{
  width:100%;
  max-height:760px;
  object-fit:contain;
  display:block;
  background:white;
  border:1px solid var(--border);
  border-radius:7px;
}

.pretty-map-side{
  background:white;
  border:1px solid var(--border);
  border-radius:7px;
  padding:1rem;
}

.pretty-map-path{
  font-family:var(--font-num);
  font-size:12px;
  color:var(--teal);
  word-break:break-all;
  background:var(--teal-pale);
  padding:.65rem;
  border-radius:6px;
  margin-top:.6rem;
}

.pretty-map-error{
  display:none;
  background:#fff0eb;
  border:1px solid #e7b7a7;
  color:#8a3d2b;
  border-radius:6px;
  padding:.75rem .9rem;
  font-size:13px;
  margin-top:.7rem;
}

@media(max-width:1100px){
  .pretty-map-viewer{
    grid-template-columns:1fr;
  }
}
/* ---------- Notebook-generated monthly map viewer end ---------- */
"""

HTML_BLOCK = r"""
  <!-- ---------- Notebook-generated monthly map viewer start ---------- -->
  <div class="card" style="margin-bottom:1rem">
    <div class="card-title">Notebook-Generated Monthly Maps · รูปแผนที่รายเดือนจาก Pipeline</div>

    <div class="notice">
      ส่วนนี้แสดงรูป PNG ที่ generate จาก notebook/script โดยตรง เช่น แผนที่ SST anomaly และ preliminary heat-risk map รายเดือน
      หลังรัน embed script แล้ว รูปจะถูกฝังไว้ในไฟล์ HTML นี้ ทำให้เปิด demo ได้โดยไม่ต้องพึ่ง path ของโฟลเดอร์ monthly_maps
    </div>

    <div class="pretty-map-viewer">
      <div class="pretty-map-frame">
        <img id="prettyPipelineMapImg" class="pretty-map-img" alt="Notebook-generated monthly map">

        <div id="prettyPipelineMapError" class="pretty-map-error">
          โหลดรูปไม่สำเร็จ ถ้ายังไม่ได้รัน embed script ให้เช็กว่าโฟลเดอร์ monthly_maps อยู่ข้างไฟล์ HTML และชื่อไฟล์ตรงกัน
        </div>
      </div>

      <div class="pretty-map-side">
        <div class="card-title">Map Selector</div>

        <div class="controls" style="margin-bottom:.8rem">
          <label>เดือน:</label>
          <select id="prettyMapMonthSelect" onchange="updatePrettyPipelineMap()">
            <option value="2024-01">2024-01</option>
            <option value="2024-02">2024-02</option>
            <option value="2024-03">2024-03</option>
            <option value="2024-04">2024-04</option>
            <option value="2024-05">2024-05</option>
            <option value="2024-06">2024-06</option>
            <option value="2024-07">2024-07</option>
            <option value="2024-08">2024-08</option>
            <option value="2024-09">2024-09</option>
            <option value="2024-10">2024-10</option>
            <option value="2024-11">2024-11</option>
            <option value="2024-12" selected>2024-12</option>
          </select>
        </div>

        <div class="controls" style="margin-bottom:.8rem">
          <label>รูปแบบแผนที่:</label>
          <select id="prettyMapTypeSelect" onchange="updatePrettyPipelineMap()">
            <option value="sst">SST anomaly map</option>
            <option value="risk" selected>Preliminary heat-risk map</option>
          </select>
        </div>

        <div class="stat-box amber" style="margin-bottom:.8rem">
          <div class="stat-label">Selected Output</div>
          <div class="stat-val" id="prettyMapSelectedLabel" style="font-size:20px">—</div>
          <div class="stat-sub">Notebook-generated PNG</div>
        </div>

        <div class="pretty-map-path" id="prettyPipelineMapPath">—</div>

        <div class="grid-note">
          ใช้รูปนี้เป็น Figure ใน proposal ได้ เช่น “Preliminary SST-only pipeline output generated from NOAA OISST and administrative boundary.”
        </div>
      </div>
    </div>
  </div>
  <!-- ---------- Notebook-generated monthly map viewer end ---------- -->
"""

JS_BLOCK_TEMPLATE = r"""
/* ---------- Notebook-generated monthly map viewer JS start ---------- */
const EMBEDDED_MONTHLY_MAPS = __EMBEDDED_JSON__;

const prettyMapConfig = {
  sst: {
    label: "SST anomaly map",
    prefix: "sst_anomaly_map_"
  },
  risk: {
    label: "Preliminary heat-risk map",
    prefix: "preliminary_heat_risk_map_"
  }
};

function getPrettyPipelineMapInfo(){
  const monthSelect = document.getElementById("prettyMapMonthSelect");
  const typeSelect = document.getElementById("prettyMapTypeSelect");

  const month = monthSelect && monthSelect.value ? monthSelect.value : "2024-12";
  const type = typeSelect && typeSelect.value ? typeSelect.value : "risk";
  const config = prettyMapConfig[type] || prettyMapConfig.risk;

  const filename = `${config.prefix}${month}.png`;

  return {
    month,
    type,
    label: config.label,
    filename,
    path: `monthly_maps/${filename}`
  };
}

function updatePrettyPipelineMap(){
  const img = document.getElementById("prettyPipelineMapImg");
  const pathBox = document.getElementById("prettyPipelineMapPath");
  const labelBox = document.getElementById("prettyMapSelectedLabel");
  const errorBox = document.getElementById("prettyPipelineMapError");

  if(!img || !pathBox || !labelBox){
    return;
  }

  const info = getPrettyPipelineMapInfo();

  labelBox.textContent = `${info.label} · ${info.month}`;

  const embeddedSrc =
    EMBEDDED_MONTHLY_MAPS &&
    EMBEDDED_MONTHLY_MAPS[info.type] &&
    EMBEDDED_MONTHLY_MAPS[info.type][info.month]
      ? EMBEDDED_MONTHLY_MAPS[info.type][info.month]
      : null;

  if(embeddedSrc){
    pathBox.textContent = `embedded in HTML · ${info.type} · ${info.month}`;

    if(errorBox){
      errorBox.style.display = "none";
    }

    img.onerror = function(){
      if(errorBox){
        errorBox.style.display = "block";
        errorBox.innerHTML = "โหลด embedded image ไม่สำเร็จ อาจเกิดจากไฟล์ HTML ใหญ่มากหรือ browser จำกัดการแสดงผล";
      }
    };

    img.onload = function(){
      if(errorBox){
        errorBox.style.display = "none";
      }
    };

    img.src = embeddedSrc;
  } else {
    pathBox.textContent = info.path;

    if(errorBox){
      errorBox.style.display = "none";
    }

    img.onerror = function(){
      if(errorBox){
        errorBox.style.display = "block";
        errorBox.innerHTML = "ไม่พบรูปตาม path นี้ ให้เช็กชื่อไฟล์ใน monthly_maps หรือรัน embed script ใหม่";
      }
    };

    img.onload = function(){
      if(errorBox){
        errorBox.style.display = "none";
      }
    };

    img.src = info.path;
  }
}

document.addEventListener("DOMContentLoaded", function(){
  setTimeout(updatePrettyPipelineMap, 200);

  document.querySelectorAll(".nav-tab").forEach(function(tab){
    tab.addEventListener("click", function(){
      setTimeout(updatePrettyPipelineMap, 250);
    });
  });
});
/* ---------- Notebook-generated monthly map viewer JS end ---------- */
"""


# =========================
# REMOVE OLD INJECTIONS
# =========================

def remove_old_blocks(html: str) -> str:
    patterns = [
        r"/\* ---------- Notebook-generated monthly map viewer start ---------- \*/.*?/\* ---------- Notebook-generated monthly map viewer end ---------- \*/",
        r"<!-- ---------- Notebook-generated monthly map viewer start ---------- -->.*?<!-- ---------- Notebook-generated monthly map viewer end ---------- -->",
        r"/\* ---------- Notebook-generated monthly map viewer JS start ---------- \*/.*?/\* ---------- Notebook-generated monthly map viewer JS end ---------- \*/",
        r"/\* ---------- Embedded PNG maps object start ---------- \*/.*?/\* ---------- Embedded PNG maps object end ---------- \*/",
        r"/\* ---------- Embedded PNG map override start ---------- \*/.*?/\* ---------- Embedded PNG map override end ---------- \*/",
    ]

    for pattern in patterns:
        html = re.sub(pattern, "", html, flags=re.S)

    return html


# =========================
# INSERT HELPERS
# =========================

def insert_css(html: str) -> str:
    if "</style>" not in html:
        raise RuntimeError("ไม่พบ </style> ใน HTML")

    return html.replace("</style>", CSS_BLOCK + "\n</style>", 1)


def insert_html_viewer(html: str) -> str:
    """
    Insert viewer inside page-pipeline, before its closing </section>.
    This is more robust than matching exact Interpretation Note text.
    """

    start_marker = '<section id="page-pipeline"'
    next_marker = '<section id="page-profile"'

    start_idx = html.find(start_marker)
    next_idx = html.find(next_marker)

    if start_idx == -1:
        raise RuntimeError("ไม่พบ <section id=\"page-pipeline\"> ใน HTML")

    if next_idx == -1:
        raise RuntimeError("ไม่พบ <section id=\"page-profile\"> ใน HTML")

    pipeline_chunk = html[start_idx:next_idx]
    close_idx_in_chunk = pipeline_chunk.rfind("</section>")

    if close_idx_in_chunk == -1:
        raise RuntimeError("ไม่พบ </section> ปิด page-pipeline")

    insert_pos = start_idx + close_idx_in_chunk

    return html[:insert_pos] + "\n" + HTML_BLOCK + "\n" + html[insert_pos:]


def insert_js(html: str, embedded: dict) -> str:
    embedded_json = json.dumps(embedded, ensure_ascii=False)
    js_block = JS_BLOCK_TEMPLATE.replace("__EMBEDDED_JSON__", embedded_json)

    marker = "/* ---------- Start ---------- */"

    if marker in html:
        return html.replace(marker, js_block + "\n\n" + marker, 1)

    # fallback: insert before last </script>
    last_script_close = html.rfind("</script>")

    if last_script_close == -1:
        raise RuntimeError("ไม่พบตำแหน่งใส่ JavaScript")

    return html[:last_script_close] + js_block + "\n" + html[last_script_close:]


# =========================
# MAIN
# =========================

def main():
    if not HTML_FILE.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ HTML: {HTML_FILE}")

    if not MAP_DIR.exists():
        raise FileNotFoundError(f"ไม่พบโฟลเดอร์รูป: {MAP_DIR}")

    html = HTML_FILE.read_text(encoding="utf-8")
    html = remove_old_blocks(html)

    embedded, missing = build_embedded_map_object()

    html = insert_css(html)
    html = insert_html_viewer(html)
    html = insert_js(html, embedded)

    OUT_FILE.write_text(html, encoding="utf-8")

    print("Done.")
    print(f"Created: {OUT_FILE.resolve()}")
    print(f"Embedded SST maps: {len(embedded['sst'])}/12")
    print(f"Embedded risk maps: {len(embedded['risk'])}/12")
    print("Injected UI: Notebook-Generated Monthly Maps")

    if missing:
        print("\nWARNING: มีไฟล์รูปที่ไม่พบ:")
        for m in missing:
            print(" -", m)
        print("\nสร้างไฟล์แล้ว แต่บางเดือนอาจไม่มีรูป ให้เช็กชื่อไฟล์ใน monthly_maps/")
    else:
        print("\nฝังรูปครบ 24 รูป + ใส่ UI monthly map viewer แล้ว")
        print("เปิด test_embedded.html แล้วไปที่แท็บ Real Data Pipeline")


if __name__ == "__main__":
    main()