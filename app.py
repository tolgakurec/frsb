import os
import io
import re
import json
import time
import base64
import gc
import urllib.request
import urllib.parse
from PIL import Image, ImageOps
import numpy as np
import easyocr
import streamlit as st
import streamlit.components.v1 as components
import uuid
try:
import gspread
from oauth2client.service_account import ServiceAccountCredentials
GSHEETS_INSTALLED = True
except ImportError:
GSHEETS_INSTALLED = False
st.set_page_config(
page_title="Lycée Victor Hugo - Kütüphane",
layout="wide",
initial_sidebar_state="collapsed"
)
==========================================
0. SABİTLER VE DİZİN YAPISI
==========================================
BOOKS_DIR = "books"
os.makedirs(BOOKS_DIR, exist_ok=True)
LANGUAGES = {
"tr": {"name": "Türkçe", "flag": "🇹🇷"},
"bg": {"name": "Български", "flag": "🇧🇬"},
"en": {"name": "English", "flag": "🇬🇧"},
"de": {"name": "Deutsch", "flag": "🇩🇪"},
"es": {"name": "Español", "flag": "🇪🇸"},
"ru": {"name": "Русский", "flag": "🇷🇺"},
}
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "user_nickname" not in st.session_state: st.session_state.user_nickname = ""
if "user_role" not in st.session_state: st.session_state.user_role = "user"
if "app_lang" not in st.session_state: st.session_state.app_lang = "tr"
if "reading_mode" not in st.session_state: st.session_state.reading_mode = False
if "editor_mode" not in st.session_state: st.session_state.editor_mode = False
if "uploaded_book_pages" not in st.session_state: st.session_state.uploaded_book_pages = []
if "current_book_title" not in st.session_state: st.session_state.current_book_title = ""
if "editor_pages" not in st.session_state: st.session_state.editor_pages = []
if "editor_book_title" not in st.session_state: st.session_state.editor_book_title = ""
if "editor_orig_book_id" not in st.session_state: st.session_state.editor_orig_book_id = None
if "editor_page_idx" not in st.session_state: st.session_state.editor_page_idx = 0
==========================================
1. GOOGLE SHEETS ENTEGRASYONU (SECRETS + LOCAL DESTEKLİ)
==========================================
@st.cache_resource
def get_gsheet_client():
if not GSHEETS_INSTALLED: return None
try:
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# 1. Öncelik: Streamlit Cloud Secrets (Bulut Kasa)
if "gcp_json" in st.secrets:
secret_data = st.secrets["gcp_json"]
secret_dict = json.loads(secret_data) if isinstance(secret_data, str) else dict(secret_data)
creds = ServiceAccountCredentials.from_json_keyfile_dict(secret_dict, scope)
# 2. Öncelik: Yerel bilgisayardaki google_secret.json dosyası
elif os.path.exists("google_secret.json"):
creds = ServiceAccountCredentials.from_json_keyfile_name("google_secret.json", scope)
else:
return None
return gspread.authorize(creds)
except Exception as e:
print(f"Auth / Bağlantı hatası: {e}")
return None
def get_sheet(sheet_name):
client = get_gsheet_client()
if not client: return None
try:
doc = client.open_by_key("1Ec0v2Oo-7BlILvb35TGgo5j-SOGivJwmf5xpF85oGoU")
return doc.worksheet(sheet_name)
except Exception as e:
print(f"Sheet erişim hatası: {e}")
return None
def login_user(email, password):
email = email.lower().strip()
if email == "tolgakurec@gmail.com" and password == "1243":
return True, {"Email": email, "Nickname": "Tolga (Admin)", "Role": "admin"}, "Giriş Başarılı"
sheet = get_sheet("Users")
if not sheet: return False, None, "Veritabanına bağlanılamadı."
records = sheet.get_all_records()
for r in records:
if str(r.get("Email", "")).lower().strip() == email:
if str(r.get("Password", "")) == password:
return True, r, "Giriş başarılı."
else:
return False, None, "Hatalı şifre."
return False, None, "Kullanıcı bulunamadı."
def register_user(email, nickname, password):
email = email.lower().strip()
sheet = get_sheet("Users")
if not sheet: return False, "Google Sheets bağlantı hatası."
records = sheet.get_all_records()
for r in records:
if str(r.get("Email", "")).lower().strip() == email:
return False, "Bu e-posta adresi zaten kayıtlı."
sheet.append_row([email, nickname, password, "user", time.strftime("%Y-%m-%d %H:%M:%S")])
return True, "Kayıt başarılı! Lütfen giriş yapın."
==========================================
2. HİBRİT KİTAPLIK İŞLEMLERİ
==========================================
def get_saved_books():
"""Google Sheets'ten kitap indeksini (kütüphane listesini) çeker."""
sheet = get_sheet("Library")
if not sheet: return []
records = sheet.get_all_records()
books_list = []
seen_ids = set()
for r in records:
b_id = str(r.get("BookID", ""))
if not b_id or b_id in seen_ids: continue
seen_ids.add(b_id)
is_shared = str(r.get("IsShared", "")).upper() == "YES"
owner_email = str(r.get("OwnerEmail", ""))
if not is_shared and owner_email != st.session_state.user_email and st.session_state.user_role != 'admin':
continue
books_list.append({
"book_id": b_id,
"title": r.get("BookName", "İsimsiz Kitap"),
"uploader": r.get("OwnerNickname", "Bilinmeyen"),
"uploader_email": owner_email,
"date": r.get("CreatedAt", ""),
"page_count": r.get("PageNum", 0)
})
return sorted(books_list, key=lambda x: x["title"])
def load_book_content(book_id):
"""Ağır JSON verisini sunucudaki books/ klasöründen çeker."""
path = os.path.join(BOOKS_DIR, f"{book_id}.json")
if os.path.exists(path):
with open(path, "r", encoding="utf-8") as file:
data = json.load(file)
return data.get("pages", [])
return None
def save_hybrid_book(title, pages, is_shared="YES", old_book_id=None):
"""Hem Google Sheets'e meta veri ekler, hem de resim/OCR verilerini books/ klasörüne yazar."""
sheet = get_sheet("Library")
if not sheet: return None
if old_book_id:
book_id = old_book_id
records = sheet.get_all_records()
row_to_del = None
for i, r in enumerate(records):
if str(r.get("BookID", "")) == book_id:
row_to_del = i + 2
break
if row_to_del:
sheet.delete_rows(row_to_del)
else:
book_id = str(uuid.uuid4())[:8]
sheet.append_row([
book_id,
time.strftime("%Y-%m-%d %H:%M:%S"),
st.session_state.user_email,
st.session_state.user_nickname,
title,
is_shared,
len(pages),
"LOCAL_JSON",
"LOCAL_JSON"
])
path = os.path.join(BOOKS_DIR, f"{book_id}.json")
with open(path, "w", encoding="utf-8") as f:
json.dump({"title": title, "pages": pages}, f, ensure_ascii=False)
return book_id
def delete_hybrid_book(book_id):
sheet = get_sheet("Library")
if sheet:
records = sheet.get_all_records()
for i, r in enumerate(records):
if str(r.get("BookID", "")) == book_id:
sheet.delete_rows(i + 2)
break
path = os.path.join(BOOKS_DIR, f"{book_id}.json")
if os.path.exists(path):
os.remove(path)
==========================================
3. OCR VE ÇEVİRİ ALTYAPISI
==========================================
@st.cache_resource
def load_ocr():
return easyocr.Reader(['fr', 'en'], gpu=False)
reader = load_ocr()
def sort_reading_order(ocr_items):
if not ocr_items: return []
parsed = []
for item in ocr_items:
box, text, conf = item
if not text.strip(): continue
xs = [p[0] for p in box]; ys = [p[1] for p in box]
min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)
cy = (min_y + max_y) / 2.0
h = max(max_y - min_y, 1.0)
parsed.append({'item': item, 'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y, 'cy': cy, 'h': h})
if not parsed: return []
parsed.sort(key=lambda p: p['cy'])
lines = []
for p in parsed:
matched_line = None
for line in lines:
avg_cy = sum(k['cy'] for k in line) / len(line)
avg_h = sum(k['h'] for k in line) / len(line)
if abs(p['cy'] - avg_cy) < (max(avg_h, p['h']) * 0.65):
matched_line = line
break
if matched_line is not None:
matched_line.append(p)
else:
lines.append([p])
lines.sort(key=lambda line: sum(k['cy'] for k in line) / len(line))
sorted_items = []
for line in lines:
line.sort(key=lambda p: p['min_x'])
for p in line:
sorted_items.append(p['item'])
return sorted_items
@st.cache_data(show_spinner=False)
def translate_text(text, target_lang):
if not text.strip(): return ""
clients = ['gtx', 'dict-chrome-ex', 'te_lib']
for client in clients:
try:
url = f"https://translate.googleapis.com/translate_a/single?client={client}&sl=fr&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
res = urllib.request.urlopen(req, timeout=5)
data = json.loads(res.read().decode('utf-8'))
return "".join([s[0] for s in data[0] if s[0]])
except: continue
return "-"
@st.cache_data(show_spinner=False)
def get_words_dictionary(words_list, target_lang):
clean_words = list(set([re.sub(r"[^\wÀ-ÿ'-]", "", w).strip().lower() for w in words_list if re.sub(r"[^\wÀ-ÿ'-]", "", w).strip()]))
if not clean_words: return {}
combined = " | ".join(clean_words)
translated = translate_text(combined, target_lang)
trans_map = {}
parts = [w.strip() for w in translated.split("|")]
for i, word in enumerate(clean_words):
trans_map[word] = parts[i] if i < len(parts) else "-"
return trans_map
def image_to_base64(img):
buf = io.BytesIO()
img.save(buf, format="JPEG", quality=80)
return base64.b64encode(buf.getvalue()).decode("utf-8")
def process_single_image(img, target_lang):
w, h = img.size
ocr_raw = reader.readtext(np.array(img), detail=1, paragraph=False)
ordered_ocr = sort_reading_order(ocr_raw)
boxes = []
full_text_list = []
for box, text, conf in ordered_ocr:
full_text_list.append(text)
x_pts = [p[0] for p in box]; y_pts = [p[1] for p in box]
min_x, max_x = min(x_pts), max(x_pts)
min_y, max_y = min(y_pts), max(y_pts)
boxes.append({
"id": f"b_{len(boxes)}",
"text": text,
"clean": text.lower().strip(),
"left": (min_x / w) * 100, "top": (min_y / h) * 100,
"width": ((max_x - min_x) / w) * 100, "height": ((max_y - min_y) / h) * 100
})
full_page_str = " ".join(full_text_list)
return {
"img_b64": image_to_base64(img),
"boxes": boxes,
"full_text": full_page_str,
"full_trans": translate_text(full_page_str, target_lang),
"dictionary": get_words_dictionary(full_text_list, target_lang)
}
def update_page_translations(page, target_lang):
words = [b["text"].strip() for b in page["boxes"] if b.get("text", "").strip()]
full_str = " ".join(words)
page["full_text"] = full_str
page["full_trans"] = translate_text(full_str, target_lang)
page["dictionary"] = get_words_dictionary(words, target_lang)
for i, b in enumerate(page["boxes"]):
b["id"] = f"b_{i}"
b["clean"] = b["text"].lower().strip()
return page
==========================================
4. ARAYÜZ (GİRİŞ EKRANI)
==========================================
if not st.session_state.logged_in:
st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>📚 Victor Hugo Veli Kütüphanesi</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Lütfen kütüphaneye erişmek için giriş yapın veya kayıt olun.</p>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
tab_login, tab_reg = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
with tab_login:
l_email = st.text_input("E-posta Adresiniz:", key="log_email")
l_pass = st.text_input("Şifreniz:", type="password", key="log_pass")
if st.button("Giriş", type="primary", use_container_width=True):
success, user_data, msg = login_user(l_email, l_pass)
if success:
st.session_state.logged_in = True
st.session_state.user_email = user_data.get("Email")
st.session_state.user_nickname = user_data.get("Nickname")
st.session_state.user_role = str(user_data.get("Role", "user")).lower()
st.rerun()
else:
st.error(msg)
with tab_reg:
r_email = st.text_input("Geçerli E-posta Adresiniz:", key="reg_email")
r_nick = st.text_input("Adınız / Rumuzunuz:", key="reg_nick")
r_pass = st.text_input("Yeni Şifre Belirleyin:", type="password", key="reg_pass")
if st.button("Kayıt Ol", use_container_width=True):
if not r_email or not r_nick or len(r_pass) < 4:
st.warning("Lütfen tüm alanları doldurun ve en az 4 haneli şifre belirleyin.")
else:
success, msg = register_user(r_email, r_nick, r_pass)
if success: st.success(msg)
else: st.error(msg)
==========================================
5. TAM EKRAN (FULLSCREEN LENS) MODU
==========================================
elif st.session_state.reading_mode:
st.markdown(
"""
<style>
[data-testid="stSidebar"], header, footer { display: none !important; }
.block-container { padding: 0 !important; margin: 0 !important; max-width: 100vw !important; height: 100vh !important; overflow: hidden !important; background: #06090e !important; }
iframe { position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; border: none !important; z-index: 1 !important; }
div[data-testid="stButton"] { position: fixed !important; top: 10px !important; right: 18px !important; z-index: 999999 !important; }
div[data-testid="stButton"] button {
background: rgba(15, 23, 42, 0.45) !important; backdrop-filter: blur(14px) !important; -webkit-backdrop-filter: blur(14px) !important;
border: 1px solid rgba(255, 255, 255, 0.15) !important; color: #cbd5e1 !important; border-radius: 25px !important; padding: 5px 14px !important;
font-weight: 500 !important; font-size: 13px !important; opacity: 0.75 !important; transition: all 0.25s ease !important;
}
div[data-testid="stButton"] button:hover { background: rgba(220, 38, 38, 0.8) !important; border-color: #ef4444 !important; color: #ffffff !important; opacity: 1.0 !important; transform: scale(1.04) !important; }
</style>
""", unsafe_allow_html=True)
if st.button("✕ Kapat", key="btn_exit_zen"):
st.session_state.reading_mode = False
st.rerun()
pages = st.session_state.uploaded_book_pages
pages_json = json.dumps(pages)
target_flag = LANGUAGES[st.session_state.app_lang]["flag"]
HTML_VIEWER = f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
* {{ box-sizing: border-box; user-select: none; -webkit-user-select: none; }}
html, body {{ margin: 0; padding: 0; width: 100vw; height: 100vh; overflow: hidden; background: #06090e; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
#viewport-wrap {{ position: relative; width: 100vw; height: calc(100vh - 120px); margin-top: 48px; display: flex; align-items: center; justify-content: center; }}
#stage {{ position: relative; max-width: 98vw; max-height: calc(100vh - 120px); display: inline-block; }}
#book-img {{ max-width: 98vw; max-height: calc(100vh - 120px); width: auto; height: auto; display: block; margin: auto; object-fit: contain; box-shadow: 0 0 35px rgba(0,0,0,0.85); border-radius: 4px; }}
#boxes-layer {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }}
.word-hitbox {{ position: absolute; border-radius: 4px; cursor: pointer; background: rgba(255,255,255,0.01); pointer-events: auto; transition: background 0.15s ease, outline 0.15s ease; }}
.word-hitbox:hover, .word-hitbox:active {{ background: rgba(254,240,138,0.45); outline: 2px solid #facc15; }}
.karaoke-lit {{ background: rgba(250,204,21,0.65) !important; outline: 2px solid #eab308 !important; }}
.glass-pill {{ position: fixed; top: 10px; left: 18px; background: rgba(15,23,42,0.45); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border: 1px solid rgba(255,255,255,0.15); color: #94a3b8; font-weight: 500; font-size: 13px; padding: 5px 14px; border-radius: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.4); z-index: 1000; transition: opacity 0.35s ease; }}
#whisper-card {{ position: fixed; bottom: 70px; left: 50%; transform: translateX(-50%); background: rgba(15,23,42,0.88); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); color: #ffffff; padding: 10px 22px; border-radius: 20px; font-size: 15px; box-shadow: 0 8px 30px rgba(0,0,0,0.6); border: 1px solid rgba(255,255,255,0.2); display: none; z-index: 1001; text-align: center; max-width: 90vw; line-height: 1.4; }}
.glass-dock {{ position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 6px; background: rgba(15,23,42,0.5); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.15); padding: 6px 12px; border-radius: 35px; box-shadow: 0 8px 25px rgba(0,0,0,0.5); z-index: 1000; max-width: 96vw; transition: opacity 0.35s ease; }}
.glass-btn {{ background: rgba(255,255,255,0.06); color: #e2e8f0; border: 1px solid rgba(255,255,255,0.12); padding: 7px 14px; border-radius: 25px; font-weight: 500; font-size: 13.5px; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.2s ease; white-space: nowrap; }}
.glass-btn:hover {{ background: rgba(255,255,255,0.18); transform: translateY(-1px); color: #ffffff; }}
.glass-btn:active {{ transform: scale(0.96); }}
.glass-btn.active {{ background: #2563eb !important; border-color: #60a5fa !important; box-shadow: 0 0 12px rgba(37,99,255,0.6); }}
.glass-btn:disabled {{ opacity: 0.25; cursor: not-allowed; transform: none !important; }}
.hud-dimmed {{ opacity: 0.18 !important; }}
</style>
</head>
<body onmousemove="resetHudTimer()" onclick="resetHudTimer()" ontouchstart="resetHudTimer()">
<div id="viewport-wrap"><div id="stage"><img id="book-img" src=""><div id="boxes-layer"></div></div></div>
<div id="page-counter" class="glass-pill hud-item">Sayfa 1 / 1</div>
<div id="whisper-card"></div>
<div id="main-dock" class="glass-dock hud-item">
<button id="btn-prev" class="glass-btn" onclick="prevPage()">⬅️</button>
<button id="btn-speed" class="glass-btn" onclick="cycleSpeed()" title="Ses Hızı">⚡ <span id="speed-text">0.8x</span></button>
<button id="btn-karaoke" class="glass-btn" onclick="toggleKaraoke()">🎤 <span id="k-text">Sesli Dinle</span></button>
<button id="btn-trans" class="glass-btn" onclick="toggleTranslation()">{target_flag} <span id="t-text">Sayfa Çevirisi</span></button>
<button id="btn-next" class="glass-btn" onclick="nextPage()">➡️</button>
</div>
<script>
const allPages = {pages_json};
const targetFlag = "{target_flag}";
let currentIndex = 0, isPlaying = false, timer = null, wordIndices = [];
let hudTimer = null;
function resetHudTimer() {{
document.querySelectorAll('.hud-item').forEach(el => el.classList.remove('hud-dimmed'));
clearTimeout(hudTimer);
hudTimer = setTimeout(() => {{ document.querySelectorAll('.hud-item').forEach(el => el.classList.add('hud-dimmed')); }}, 3500);
}}
resetHudTimer();
const speeds = [0.7, 0.8, 1.0]; let speedIdx = 1;
const imgEl = document.getElementById('book-img'), layer = document.getElementById('boxes-layer'), card = document.getElementById('whisper-card');
const pageCounter = document.getElementById('page-counter'), btnPrev = document.getElementById('btn-prev'), btnNext = document.getElementById('btn-next'), btnKaraoke = document.getElementById('btn-karaoke');
function cycleSpeed() {{
resetHudTimer(); speedIdx = (speedIdx + 1) % speeds.length;
document.getElementById('speed-text').innerText = speeds[speedIdx] + "x";
if (isPlaying) {{ toggleKaraoke(); setTimeout(toggleKaraoke, 100); }}
}}
function loadPage(idx) {{
if (idx < 0 || idx >= allPages.length) return;
resetHudTimer(); stopKaraoke(); currentIndex = idx; const page = allPages[idx];
imgEl.src = "data:image/jpeg;base64," + page.img_b64;
pageCounter.innerText = ⁠Sayfa ${{idx + 1}} / ${{allPages.length}}⁠;
btnPrev.disabled = (idx === 0); btnNext.disabled = (idx === allPages.length - 1);
card.style.display = 'none'; layer.innerHTML = ''; wordIndices = []; let charOffset = 0;
page.boxes.forEach((b, i) => {{
wordIndices.push({{ idx: i, start: charOffset, end: charOffset + b.text.length }});
charOffset += b.text.length + 1;
const d = document.createElement('div'); d.className = 'word-hitbox'; d.id = 'box_' + i;
d.style.left = b.left + '%'; d.style.top = b.top + '%'; d.style.width = b.width + '%'; d.style.height = b.height + '%';
d.onclick = () => {{
resetHudTimer(); const trans = page.dictionary[b.clean] || '-';
card.innerHTML = "🇫🇷 <b>" + b.text + "</b> ➔ " + targetFlag + " " + trans; card.style.display = 'block';
window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(b.text); u.lang = 'fr-FR'; u.rate = speeds[speedIdx]; window.speechSynthesis.speak(u);
clearTimeout(timer); timer = setTimeout(() => {{ card.style.display = 'none'; }}, 3500);
}};
layer.appendChild(d);
}});
}}
function nextPage() {{ resetHudTimer(); if (currentIndex < allPages.length - 1) loadPage(currentIndex + 1); }}
function prevPage() {{ resetHudTimer(); if (currentIndex > 0) loadPage(currentIndex - 1); }}
function toggleTranslation() {{
resetHudTimer();
if (card.style.display === 'block') card.style.display = 'none';
else {{ card.innerHTML = "📝 <b>Sayfa Çevirisi:</b> " + allPages[currentIndex].full_trans; card.style.display = 'block'; }}
}}
function toggleKaraoke() {{ resetHudTimer(); if (isPlaying) stopKaraoke(); else playKaraoke(); }}
function playKaraoke() {{
window.speechSynthesis.cancel(); isPlaying = true; btnKaraoke.classList.add('active'); document.getElementById('k-text').innerText = "Durdur";
const page = allPages[currentIndex]; let fullSentence = page.boxes.map(b => b.text).join(' ');
let u = new SpeechSynthesisUtterance(fullSentence); u.lang = 'fr-FR'; u.rate = speeds[speedIdx];
let usedBoundary = false;
u.onboundary = function(e) {{
if (e.name === 'word') {{
usedBoundary = true; const match = wordIndices.find(w => e.charIndex >= w.start && e.charIndex <= w.end);
if (match) {{ document.querySelectorAll('.word-hitbox').forEach(el => el.classList.remove('karaoke-lit')); const el = document.getElementById('box_' + match.idx); if (el) el.classList.add('karaoke-lit'); }}
}}
}};
let fallbackIdx = 0;
function stepFallback() {{
if (!isPlaying || fallbackIdx >= page.boxes.length) return;
if (!usedBoundary) {{ document.querySelectorAll('.word-hitbox').forEach(el => el.classList.remove('karaoke-lit')); const el = document.getElementById('box_' + fallbackIdx); if (el) el.classList.add('karaoke-lit'); }}
let dur = ((page.boxes[fallbackIdx].text.length * 60) + 50) / speeds[speedIdx]; fallbackIdx++; timer = setTimeout(stepFallback, dur);
}}
u.onend = stopKaraoke; u.onerror = stopKaraoke; window.speechSynthesis.speak(u); stepFallback();
}}
function stopKaraoke() {{ isPlaying = false; clearTimeout(timer); window.speechSynthesis.cancel(); btnKaraoke.classList.remove('active'); document.getElementById('k-text').innerText = "Sesli Dinle"; document.querySelectorAll('.word-hitbox').forEach(el => el.classList.remove('karaoke-lit')); }}
window.addEventListener('keydown', (e) => {{ if (e.key === 'ArrowRight') nextPage(); if (e.key === 'ArrowLeft') prevPage(); }});
let touchStartX = 0;
window.addEventListener('touchstart', (e) => {{ touchStartX = e.changedTouches[0].screenX; }}, {{passive: true}});
window.addEventListener('touchend', (e) => {{ let diff = e.changedTouches[0].screenX - touchStartX; if (diff < -50) nextPage(); if (diff > 50) prevPage(); }}, {{passive: true}});
loadPage(0);
</script>
</body>
</html>
"""
components.html(HTML_VIEWER, height=850, scrolling=False)
==========================================
6. KİTAP & METİN DÜZENLEYİCİ (EDITOR MODU)
==========================================
elif st.session_state.editor_mode:
st.subheader(f"✏️ Kitap Düzenleyici: {st.session_state.editor_book_title}")
col_t1, col_t2, col_t3, col_t4 = st.columns([2.5, 1.5, 1.5, 1])
with col_t1:
st.session_state.editor_book_title = st.text_input("Kitap Başlığı:", value=st.session_state.editor_book_title, label_visibility="collapsed")
with col_t2:
if st.button("💾 Değişiklikleri Kaydet (Kütüphaneye Ekle)", type="secondary", use_container_width=True):
saved_f = save_hybrid_book(st.session_state.editor_book_title, st.session_state.editor_pages, "YES", st.session_state.editor_orig_book_id)
st.session_state.editor_orig_book_id = saved_f
st.success("Kitap ortak havuza başarıyla kaydedildi!")
with col_t3:
if st.button("🚀 Kaydet & Hemen Oku", type="primary", use_container_width=True):
saved_f = save_hybrid_book(st.session_state.editor_book_title, st.session_state.editor_pages, "YES", st.session_state.editor_orig_book_id)
st.session_state.uploaded_book_pages = st.session_state.editor_pages
st.session_state.current_book_title = st.session_state.editor_book_title
st.session_state.editor_mode = False
st.reading_mode = True
st.rerun()
with col_t4:
if st.button("✕ Çık", use_container_width=True):
st.session_state.editor_mode = False
st.rerun()
st.divider()
pages = st.session_state.editor_pages
total_p = len(pages)
if total_p == 0:
st.warning("Bu kitapta hiç sayfa kalmadı. Yeni sayfa yükleyebilirsiniz.")
else:
if st.session_state.editor_page_idx >= total_p: st.session_state.editor_page_idx = total_p - 1
p_idx = st.session_state.editor_page_idx
curr_page = pages[p_idx]
col_left, col_right = st.columns([1, 1.4])
with col_left:
st.markdown(f"### 📄 Sayfa {p_idx + 1} / {total_p}")
row_sel, row_up, row_down, row_del = st.columns([2, 1, 1, 1])
with row_sel:
new_idx = st.selectbox("Sayfaya Git:", options=list(range(total_p)), format_func=lambda i: f"Sayfa {i + 1}", index=p_idx, label_visibility="collapsed")
if new_idx != p_idx:
st.session_state.editor_page_idx = new_idx
st.rerun()
with row_up:
if st.button("⬆️", disabled=(p_idx == 0)):
pages[p_idx], pages[p_idx - 1] = pages[p_idx - 1], pages[p_idx]
st.session_state.editor_page_idx -= 1
st.rerun()
with row_down:
if st.button("⬇️", disabled=(p_idx == total_p - 1)):
pages[p_idx], pages[p_idx + 1] = pages[p_idx + 1], pages[p_idx]
st.session_state.editor_page_idx += 1
st.rerun()
with row_del:
if st.button("🗑️"):
pages.pop(p_idx)
if st.session_state.editor_page_idx >= len(pages) and len(pages) > 0: st.session_state.editor_page_idx = len(pages) - 1
st.rerun()
img_html = f"""<div style="text-align: center; background: #0f172a; border-radius: 8px; padding: 10px; margin-top: 10px;">
<img src="data:image/jpeg;base64,{curr_page['img_b64']}" style="max-width: 100%; max-height: 480px; object-fit: contain; border-radius: 4px;" /></div>"""
st.markdown(img_html, unsafe_allow_html=True)
with st.expander("➕ Bu Kitaba Yeni Sayfa Ekle"):
new_single_file = st.file_uploader("Ek Sayfa Seç (PNG/JPG):", type=["png", "jpg", "jpeg"], key="add_new_p")
if new_single_file and st.button("Taramaya Ekle"):
b_img = ImageOps.exif_transpose(Image.open(new_single_file)).convert("RGB")
new_page_obj = process_single_image(b_img, st.session_state.app_lang)
pages.append(new_page_obj)
st.session_state.editor_page_idx = len(pages) - 1
st.rerun()
with col_right:
st.markdown("### 🔤 Tespit Edilen Kelimeler")
col_b1, col_b2 = st.columns([1.5, 1])
with col_b1:
if st.button("🧹 Sayfa Numaralarını Otomatik Kaldır"):
curr_page["boxes"] = [b for b in curr_page["boxes"] if not b["text"].strip().isdigit()]
update_page_translations(curr_page, st.session_state.app_lang)
st.rerun()
table_data = [{"Kaldır 🗑️": False, "Metin (Fransızca)": b["text"]} for b in curr_page["boxes"]]
edited_table = st.data_editor(
table_data, key=f"editor_table_{p_idx}", use_container_width=True, height=380,
column_config={
"Kaldır 🗑️": st.column_config.CheckboxColumn("Kaldır 🗑️", default=False),
"Metin (Fransızca)": st.column_config.TextColumn("Metin (Fransızca)", required=True)
}
)
if st.button("🔄 Değişiklikleri Bu Sayfaya Uygula", type="primary", use_container_width=True):
new_boxes = []
for row_idx, row in enumerate(edited_table):
if not row["Kaldır 🗑️"] and row["Metin (Fransızca)"].strip():
orig_box = curr_page["boxes"][row_idx]
orig_box["text"] = row["Metin (Fransızca)"].strip()
new_boxes.append(orig_box)
curr_page["boxes"] = new_boxes
update_page_translations(curr_page, st.session_state.app_lang)
st.success("Güncellendi!")
time.sleep(0.4)
st.rerun()
with st.expander("📝 Önizleme", expanded=True):
st.markdown(f"🇫🇷: {curr_page.get('full_text', '-')}")
st.markdown(f"{LANGUAGES[st.session_state.app_lang]['flag']}: {curr_page.get('full_trans', '-')}")
==========================================
7. ANA KÜTÜPHANE EKRANI
==========================================
else:
st.title("📚 Ortak Havuz ve Kütüphane")
col_info1, col_info2, col_info3 = st.columns([2, 2, 1])
with col_info1:
st.markdown(f"👤 Hesap: {st.session_state.user_nickname} ({st.session_state.user_role.upper()})")
with col_info2:
st.session_state.app_lang = st.selectbox(
"Varsayılan Çeviri Dili:", options=list(LANGUAGES.keys()),
format_func=lambda x: f"{LANGUAGES[x]['flag']} {LANGUAGES[x]['name']}",
index=list(LANGUAGES.keys()).index(st.session_state.app_lang),
label_visibility="collapsed"
)
with col_info3:
if st.button("🚪 Çıkış Yap", use_container_width=True):
st.session_state.logged_in = False
st.rerun()
tabs = ["📖 Kütüphane Havuzu", "➕ Yeni Kitap Ekle"]
app_tabs = st.tabs(tabs)
with app_tabs[0]:
saved_books = get_saved_books()
if not saved_books:
st.info("Havuzda henüz kitap yok. Yan sekmeden ilk kitabı siz tarayıp ekleyin!")
else:
book_titles = {b["book_id"]: f"{b['title']} ({b['page_count']} sayfa) - Ekleyen: {b['uploader']}" for b in saved_books}
selected_id = st.selectbox("Okumak istediğiniz kitabı seçin:", options=list(book_titles.keys()), format_func=lambda x: book_titles[x])
col_r, col_e, col_d = st.columns([2, 2, 1])
with col_r:
if st.button("🚀 Kitabı Aç ve Oku", type="primary", use_container_width=True):
with st.spinner("Kitap yükleniyor..."):
book_pages = load_book_content(selected_id)
if book_pages:
st.session_state.uploaded_book_pages = book_pages
st.session_state.current_book_title = next((b["title"] for b in saved_books if b["book_id"] == selected_id), "")
st.session_state.reading_mode = True
st.rerun()
else:
st.error("Kitap veri dosyası (JSON) sunucuda bulunamadı.")
with col_e:
if st.button("✏️ Kitabı Düzenle", use_container_width=True):
with st.spinner("Kitap yükleniyor..."):
book_pages = load_book_content(selected_id)
if book_pages:
st.session_state.editor_pages = book_pages
st.session_state.editor_book_title = next((b["title"] for b in saved_books if b["book_id"] == selected_id), "")
st.session_state.editor_orig_book_id = selected_id
st.session_state.editor_page_idx = 0
st.session_state.editor_mode = True
st.rerun()
with col_d:
uploader = next((b["uploader_email"] for b in saved_books if b["book_id"] == selected_id), "")
can_delete = st.session_state.user_role == "admin" or uploader == st.session_state.user_email
if st.button("🗑️ Sil", use_container_width=True, disabled=not can_delete):
delete_hybrid_book(selected_id)
st.success("Kitap silindi.")
time.sleep(0.5)
st.rerun()
# ==========================================
# RAM OPTİMİZASYONLU YÜKLEME ALANI
# ==========================================
with app_tabs[1]:
book_title_input = st.text_input("Kitabın Adı (Örn: Le Petit Prince):", value="Yeni Kitap")
uploaded_files = st.file_uploader("Kitap sayfalarını seçin (PNG, JPG):", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
col_c1, col_c2 = st.columns(2)
with col_c1:
split_spreads = st.checkbox("📖 Çift Sayfa Çekimlerini Otomatik İkiye Böl", value=True)
with col_c2:
is_shared_cb = st.checkbox("🌐 Bu kitabı diğer velilerle paylaş (Ortak Havuz)", value=True)
if uploaded_files:
if st.button("⚡ Taramayı Başlat & Düzenleyiciye Aktar", type="primary", use_container_width=True):
extracted_pages = []
total_files = len(uploaded_files)
progress_bar = st.progress(0, text="Sayfalar taranmaya başlanıyor...")
status_text = st.empty()
for f_idx, file in enumerate(uploaded_files):
status_text.text(f"İşleniyor: Görsel {f_idx + 1} / {total_files}...")
# 1. RAM'i rahatlatmak için fotoğrafı anında küçült
base_img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
base_img.thumbnail((1200, 1600), Image.Resampling.LANCZOS)
# 2. İkiye bölme işlemi
sub_images = []
if split_spreads and (base_img.width / base_img.height) > 1.25:
mid_x = base_img.width // 2
sub_images.append(base_img.crop((0, 0, mid_x, base_img.height)))
sub_images.append(base_img.crop((mid_x, 0, base_img.width, base_img.height)))
else:
sub_images.append(base_img)
# 3. Her sayfayı teker teker yapay zekaya gönder ve işlemi bitince fotoğrafı imha et
for sub_img in sub_images:
page_obj = process_single_image(sub_img, st.session_state.app_lang)
extracted_pages.append(page_obj)
del sub_img
# 4. Ana fotoğrafı ve listeyi RAM'den silip çöp toplayıcıyı çalıştır
del base_img
del sub_images
gc.collect()
progress_bar.progress((f_idx + 1) / total_files)
status_text.text("Kitap veritabanına kaydediliyor...")
saved_title = book_title_input.strip() or "İsimsiz Kitap"
shared_str = "YES" if is_shared_cb else "NO"
saved_id = save_hybrid_book(saved_title, extracted_pages, shared_str, None)
st.session_state.editor_pages = extracted_pages
st.session_state.editor_book_title = saved_title
st.session_state.editor_orig_book_id = saved_id
st.session_state.editor_page_idx = 0
st.session_state.editor_mode = True
st.rerun()
