import os
import io
import re
import json
import time
import base64
import gc
import uuid
import urllib.request
import urllib.parse
from datetime import datetime
from PIL import Image, ImageOps
import numpy as np
import easyocr
import streamlit as st
import streamlit.components.v1 as components

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSHEETS_INSTALLED = True
except ImportError:
    GSHEETS_INSTALLED = False

st.set_page_config(
    page_title="Fransızca Hikaye Kütüphanesi",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 0. ÇOK DİLLİ ARAYÜZ METİNLERİ (TR / EN / BG)
# ==========================================
UI_TRANSLATIONS = {
    "tr": {
        "title": "📚 Fransızca Hikaye Kütüphanesi",
        "subtitle": "Fransızca Hikayeleri Keşfet ve Birlikte Öğren",
        "created_by": "Bu uygulama Tolga Küreç tarafından oluşturulmuştur (Timuçin ve Teoman'ın Babası)",
        "purpose_title": "🎯 Uygulamanın Amacı",
        "purpose_text": (
            "Bu kütüphane, Fransızca bilmeyen ailelerin kitap okurken çocukları ile kaliteli ve verimli "
            "vakit geçirmelerini sağlamak; hikayelerin konusunu kavramada ve Fransızca telaffuz (prononciation) "
            "konusunda velilere rehberlik etmek için tasarlanmıştır."
        ),
        "usage_title": "💡 Nasıl Kullanılır?",
        "usage_text": (
            "1. Okumak istediğiniz hikayeyi kütüphaneden seçin ve açın.\n"
            "2. Sayfadaki kelimelere dokunarak doğru Fransızca sesli okunuşunu dinleyin ve anlık çevirisini görün.\n"
            "3. 'Sesli Dinle' butonu ile sayfanın tamamını akıcı olarak takip edin.\n"
            "4. 'Sayfa Çevirisi' butonu ile hikayenin Türkçe özet mealini okuyun."
        ),
        "email_label": "E-posta Adresiniz:",
        "login_btn": "Giriş Yap",
        "email_warn": "Lütfen geçerli bir e-posta adresi girin.",
        "welcome": "Hoş Geldiniz",
        "logout": "🚪 Çıkış Yap",
        "thanks_btn": "❤️ Teşekkür Et",
        "thanks_success": "Teşekkürünüz Tolga Küreç'e iletildi! İyi okumalar dileriz.",
        "lib_title": "📖 Kütüphane Havuzu",
        "add_tab": "➕ Yeni Kitap Ekle",
        "empty_lib": "Kütüphanede henüz kitap bulunmuyor.",
        "select_book": "Okumak istediğiniz kitabı seçin:",
        "open_read": "🚀 Kitabı Aç ve Oku",
        "edit_book": "✏️ Kitabı Düzenle",
        "delete_book": "🗑️ Sil",
        "delete_confirm": "Kitap silindi.",
        "save_changes": "💾 Değişiklikleri Kaydet (Veritabanına Ekle)",
        "save_and_read": "🚀 Kaydet & Hemen Oku",
        "exit_editor": "✕ Çık",
        "saving_db": "Google Sheets'e kaydediliyor...",
        "ocr_processing": "Görseller taranıyor...",
        "reading_lang_label": "Okuma & Çeviri Dili:",
        "zen_close": "✕ Kapat",
        "zen_page": "Sayfa",
        "zen_listen": "Sesli Dinle",
        "zen_stop": "Durdur",
        "zen_page_trans": "Sayfa Çevirisi",
        "zen_loading_trans": "Çeviri hazırlanıyor..."
    },
    "en": {
        "title": "📚 French Storybook Library",
        "subtitle": "Explore French Stories & Learn Together",
        "created_by": "This application was created by Tolga Küreç (Father of Timuçin & Teoman)",
        "purpose_title": "🎯 Purpose of the App",
        "purpose_text": (
            "This library is designed for non-French speaking families to spend productive, enjoyable reading "
            "time with their children. It assists parents in understanding the storyline and mastering French "
            "pronunciation alongside their kids."
        ),
        "usage_title": "💡 How to Use?",
        "usage_text": (
            "1. Select a storybook from the library pool and open it.\n"
            "2. Tap any word or phrase on the page to hear genuine French pronunciation and view instant translation.\n"
            "3. Use 'Listen Aloud' to experience karaoke audio playback of the whole page.\n"
            "4. Use 'Page Translation' to reveal the full meaning of the page."
        ),
        "email_label": "Your Email Address:",
        "login_btn": "Sign In",
        "email_warn": "Please enter a valid email address.",
        "welcome": "Welcome",
        "logout": "🚪 Sign Out",
        "thanks_btn": "❤️ Send Thanks",
        "thanks_success": "Your thank-you note was sent to Tolga Küreç! Enjoy reading.",
        "lib_title": "📖 Library Pool",
        "add_tab": "➕ Add New Book",
        "empty_lib": "There are no books in the library yet.",
        "select_book": "Select a book to read:",
        "open_read": "🚀 Open & Read",
        "edit_book": "✏️ Edit Book",
        "delete_book": "🗑️ Delete",
        "delete_confirm": "Book deleted successfully.",
        "save_changes": "💾 Save Changes (To Database)",
        "save_and_read": "🚀 Save & Read Now",
        "exit_editor": "✕ Exit",
        "saving_db": "Saving to Google Sheets database...",
        "ocr_processing": "Processing pages with OCR...",
        "reading_lang_label": "Reading & Translation Language:",
        "zen_close": "✕ Close",
        "zen_page": "Page",
        "zen_listen": "Listen Aloud",
        "zen_stop": "Stop",
        "zen_page_trans": "Page Translation",
        "zen_loading_trans": "Preparing translation..."
    },
    "bg": {
        "title": "📚 Френска библиотека с приказки",
        "subtitle": "Открийте френските приказки и учете заедно",
        "created_by": "Това приложение е създадено от Толга Кюреч (Бащата на Тимучин и Теоман)",
        "purpose_title": "🎯 Цел на приложението",
        "purpose_text": (
            "Тази библиотека е създадена, за да помогне на семействата, които не говорят френски, "
            "да прекарват пълноценно и приятно време с децата си по време на четене. Тя подпомага родителите "
            "в разбирането на сюжета и правилното френско произношение."
        ),
        "usage_title": "💡 Как се използва?",
        "usage_text": (
            "1. Изберете приказка от библиотеката и я отворете.\n"
            "2. Докоснете дума или фраза на страницата, за да чуете произношението ѝ и да видите превода.\n"
            "3. Натиснете 'Слушай', за да чуете гладкото четене на цялата страница с караоке ефект.\n"
            "4. Натиснете 'Превод на страницата', за да прочетете пълния смислов превод."
        ),
        "email_label": "Вашият имейл адрес:",
        "login_btn": "Вход",
        "email_warn": "Моля, въведете валиден имейл адрес.",
        "welcome": "Добре дошли",
        "logout": "🚪 Изход",
        "thanks_btn": "❤️ Изпрати благодарност",
        "thanks_success": "Вашата благодарност бе изпратена на Толга Кюреч! Приятно четене.",
        "lib_title": "📖 Библиотека",
        "add_tab": "➕ Добави нова книга",
        "empty_lib": "В библиотеката все още няма добавени книги.",
        "select_book": "Изберете книга за четене:",
        "open_read": "🚀 Отвори и чети",
        "edit_book": "✏️ Редактирай",
        "delete_book": "🗑️ Изтрий",
        "delete_confirm": "Книгата бе изтрита успешно.",
        "save_changes": "💾 Запази промените (В базата данни)",
        "save_and_read": "🚀 Запази и чети веднага",
        "exit_editor": "✕ Изход",
        "saving_db": "Запазване в Google Sheets...",
        "ocr_processing": "Обработка на страниците...",
        "reading_lang_label": "Език за превод при четене:",
        "zen_close": "✕ Затвори",
        "zen_page": "Страница",
        "zen_listen": "Слушай",
        "zen_stop": "Спри",
        "zen_page_trans": "Превод на страницата",
        "zen_loading_trans": "Подготвя се превод..."
    }
}

LANGUAGES = {
    "tr": {"name": "Türkçe", "flag": "🇹🇷"},
    "en": {"name": "English", "flag": "🇬🇧"},
    "bg": {"name": "Български", "flag": "🇧🇬"},
    "de": {"name": "Deutsch", "flag": "🇩🇪"},
    "es": {"name": "Español", "flag": "🇪🇸"},
    "ru": {"name": "Русский", "flag": "🇷🇺"},
}

if "app_lang" not in st.session_state: st.session_state.app_lang = "tr"
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "user_role" not in st.session_state: st.session_state.user_role = "user"
if "reading_mode" not in st.session_state: st.session_state.reading_mode = False
if "editor_mode" not in st.session_state: st.session_state.editor_mode = False
if "uploaded_book_pages" not in st.session_state: st.session_state.uploaded_book_pages = []
if "current_book_title" not in st.session_state: st.session_state.current_book_title = ""
if "editor_pages" not in st.session_state: st.session_state.editor_pages = []
if "editor_book_title" not in st.session_state: st.session_state.editor_book_title = ""
if "editor_orig_book_id" not in st.session_state: st.session_state.editor_orig_book_id = None
if "editor_page_idx" not in st.session_state: st.session_state.editor_page_idx = 0

def T(key):
    lang = st.session_state.app_lang if st.session_state.app_lang in UI_TRANSLATIONS else "tr"
    return UI_TRANSLATIONS[lang].get(key, UI_TRANSLATIONS["tr"].get(key, key))

# ==========================================
# 1. GOOGLE SHEETS ENTEGRASYONU & ANAHTAR ONARIMI
# ==========================================
def clean_private_key(key_str):
    if not key_str or not isinstance(key_str, str):
        return key_str
    key_str = key_str.replace("\r\n", "\n").replace("\r", "\n")
    if "\\n" in key_str:
        key_str = key_str.replace("\\n", "\n")
    return key_str.strip()

def get_service_account_dict():
    creds_dict = None
    if hasattr(st, "secrets"):
        if "gcp_json" in st.secrets:
            raw = st.secrets["gcp_json"]
            creds_dict = json.loads(raw) if isinstance(raw, str) else dict(raw)
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        elif "type" in st.secrets and st.secrets.get("type") == "service_account":
            creds_dict = dict(st.secrets)
            
    if not creds_dict:
        for fname in ["google_secret.json", "secrets.json", "service_account.json"]:
            if os.path.exists(fname):
                try:
                    with open(fname, "r", encoding="utf-8") as f:
                        creds_dict = json.load(f)
                        break
                except:
                    pass

    if creds_dict and "private_key" in creds_dict:
        creds_dict["private_key"] = clean_private_key(creds_dict["private_key"])
        
    return creds_dict

@st.cache_resource
def get_gsheet_client():
    if not GSHEETS_INSTALLED:
        return None, "gspread veya oauth2client kütüphaneleri eksik.", ""
    
    creds_dict = get_service_account_dict()
    if not creds_dict:
        return None, "Google kimlik anahtarı bulunamadı! Secrets (gcp_json) ayarlarını kontrol edin.", ""
    
    sa_email = creds_dict.get("client_email", "Bilinmeyen Servis Hesabı")
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client, None, sa_email
    except Exception as e:
        return None, f"Yetkilendirme Hatası: {str(e)}", sa_email

def get_sheet(sheet_name):
    client, err, sa_email = get_gsheet_client()
    if not client:
        return None, err
    try:
        doc = client.open_by_key("1Ec0v2Oo-7BlILvb35TGgo5j-SOGivJwmf5xpF85oGoU")
    except Exception as e:
        return None, f"Tablo açılamadı! Lütfen E-Tabloyu şu hesaba 'Düzenleyen' (Editor) olarak yetkilendirin:\n👉 {sa_email}\n(Hata: {str(e)})"
    
    try:
        worksheet = doc.worksheet(sheet_name)
        return worksheet, None
    except Exception as e:
        return None, f"'{sheet_name}' isimli sekme bulunamadı! (Hata: {str(e)})"

def login_user(email):
    email = email.lower().strip()
    if email == "tolgakurec@gmail.com":
        return True, {"Email": email, "Role": "admin"}, "Giriş Başarılı"
    
    sheet, err = get_sheet("Users")
    if not sheet:
        return False, None, f"Veritabanı hatası: {err}"
    
    try:
        records = sheet.get_all_records()
        for r in records:
            if str(r.get("Email", "")).lower().strip() == email:
                return True, r, "Giriş başarılı."
        
        sheet.append_row([email, "user"])
        return True, {"Email": email, "Role": "user"}, "Yeni hesap kaydedildi."
    except Exception as e:
        return False, None, f"Kayıt işlemi başarısız: {e}"

def record_thanks(email):
    sheet, err = get_sheet("Thanks")
    if not sheet:
        return False
    try:
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            email,
            "Teşekkür Gönderildi"
        ])
        return True
    except:
        return False

# ==========================================
# 2. VERİTABANI İŞLEMLERİ (LIBRARY & PAGES)
# ==========================================
def get_saved_books():
    sheet, err = get_sheet("Library")
    if not sheet:
        return [], err
    try:
        records = sheet.get_all_records()
        books_list = []
        seen_ids = set()
        
        for r in records:
            b_id = str(r.get("BookID", ""))
            if not b_id or b_id in seen_ids:
                continue
            seen_ids.add(b_id)
            
            books_list.append({
                "book_id": b_id,
                "title": r.get("BookName", "İsimsiz Kitap"),
                "date": r.get("CreatedAt", ""),
                "page_count": r.get("PageCount", 0)
            })
        return sorted(books_list, key=lambda x: x["title"]), None
    except Exception as e:
        return [], str(e)

def load_book_content(book_id):
    sheet, err = get_sheet("Pages")
    if not sheet:
        return None, err
    try:
        records = sheet.get_all_records()
        pages = []
        for r in records:
            if str(r.get("BookID", "")) == book_id:
                try:
                    boxes = json.loads(r.get("OCRText", "[]"))
                except:
                    boxes = []
                
                pages.append({
                    "page_no": int(r.get("PageNo", 0)),
                    "img_b64": r.get("ImageBase64", ""),
                    "boxes": boxes
                })
                
        if not pages:
            return None, "Bu kitaba ait sayfa verisi bulunamadı."
        return sorted(pages, key=lambda x: x["page_no"]), None
    except Exception as e:
        return None, str(e)

def save_hybrid_book(title, pages, old_book_id=None):
    lib_sheet, err1 = get_sheet("Library")
    if not lib_sheet:
        return None, f"Library sekmesine bağlanılamadı:\n{err1}"
    
    pages_sheet, err2 = get_sheet("Pages")
    if not pages_sheet:
        return None, f"Pages sekmesine bağlanılamadı:\n{err2}"
    
    try:
        if old_book_id:
            book_id = old_book_id
            lib_records = lib_sheet.get_all_records()
            for i, r in enumerate(lib_records):
                if str(r.get("BookID", "")) == book_id:
                    lib_sheet.delete_rows(i + 2)
                    break
            page_records = pages_sheet.get_all_records()
            rows_to_delete = [i + 2 for i, r in enumerate(page_records) if str(r.get("BookID", "")) == book_id]
            for row_idx in reversed(rows_to_delete):
                pages_sheet.delete_rows(row_idx)
                time.sleep(0.1)
        else:
            book_id = str(uuid.uuid4())[:8]
            
        lib_sheet.append_row([
            book_id,
            title,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            len(pages)
        ])
        
        all_page_rows = []
        for idx, page in enumerate(pages):
            ocr_json = json.dumps(page["boxes"], ensure_ascii=False)
            all_page_rows.append([
                book_id,
                idx + 1,
                page["img_b64"],
                ocr_json
            ])
            
        chunk_size = 10
        for i in range(0, len(all_page_rows), chunk_size):
            chunk = all_page_rows[i:i + chunk_size]
            pages_sheet.append_rows(chunk)
            time.sleep(0.5)
            
        return book_id, "Kitap Google Sheets veritabanına başarıyla kaydedildi!"
    except Exception as e:
        return None, f"Google Sheets yazma hatası: {str(e)}"

def delete_hybrid_book(book_id):
    lib_sheet, _ = get_sheet("Library")
    pages_sheet, _ = get_sheet("Pages")
    
    if lib_sheet:
        records = lib_sheet.get_all_records()
        for i, r in enumerate(records):
            if str(r.get("BookID", "")) == book_id:
                lib_sheet.delete_rows(i + 2)
                break
                
    if pages_sheet:
        records = pages_sheet.get_all_records()
        rows_to_delete = [i + 2 for i, r in enumerate(records) if str(r.get("BookID", "")) == book_id]
        for row_idx in reversed(rows_to_delete):
            pages_sheet.delete_rows(row_idx)
            time.sleep(0.1)

# ==========================================
# 3. OCR, ÇEVİRİ VE DİNAMİK SÖZLÜK MOTORU
# ==========================================
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['fr', 'en'], gpu=False)

reader = load_ocr()

def compress_image_for_sheets(img):
    img.thumbnail((600, 800), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    quality = 40
    img.save(buf, format="JPEG", quality=quality)
    
    while len(buf.getvalue()) > 35000 and quality > 10:
        quality -= 5
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        
    return base64.b64encode(buf.getvalue()).decode("utf-8")

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

def clean_word_key(text):
    if not text: return ""
    cleaned = re.sub(r"^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$", "", text).strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned

@st.cache_data(show_spinner=False)
def translate_text(text, target_lang):
    if not text or not text.strip(): return ""
    clients = ['gtx', 'dict-chrome-ex', 'te_lib']
    for client in clients:
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client={client}&sl=fr&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req, timeout=5)
            data = json.loads(res.read().decode('utf-8'))
            translated_parts = []
            if data and data[0]:
                for s in data[0]:
                    if s and s[0]:
                        translated_parts.append(s[0])
            return "".join(translated_parts).strip()
        except:
            continue
    return "-"

@st.cache_data(show_spinner=False)
def get_words_dictionary(texts_list, target_lang):
    trans_map = {}
    unique_items = set()

    for raw in texts_list:
        clean = clean_word_key(raw)
        if clean:
            unique_items.add(clean)
        for word in re.findall(r"[\wÀ-ÿ'-]+", raw):
            w_clean = clean_word_key(word)
            if len(w_clean) > 1:
                unique_items.add(w_clean)

    if not unique_items:
        return {}

    items_list = sorted(list(unique_items))
    batch_size = 15
    for i in range(0, len(items_list), batch_size):
        batch = items_list[i:i + batch_size]
        combined = "\n".join(batch)
        translated_combined = translate_text(combined, target_lang)

        lines = [line.strip() for line in translated_combined.split("\n") if line.strip()]
        if len(lines) == len(batch):
            for orig, trans in zip(batch, lines):
                trans_map[orig] = trans
        else:
            for orig in batch:
                trans_map[orig] = translate_text(orig, target_lang)

    return trans_map

def ensure_reading_ready(pages, target_lang):
    for page in pages:
        if page.get("current_lang") != target_lang or "full_trans" not in page or "dictionary" not in page:
            boxes = page.get("boxes", [])
            raw_texts = []
            for b in boxes:
                raw = b.get("text", "").strip()
                if raw:
                    raw_texts.append(raw)
                    b["clean"] = clean_word_key(raw)

            full_str = " ".join(raw_texts)
            page["full_text"] = full_str
            page["full_trans"] = translate_text(full_str, target_lang)
            page["dictionary"] = get_words_dictionary(raw_texts, target_lang)
            page["current_lang"] = target_lang
    return pages

def process_single_image(img):
    # RAM KORUMA: Çözünürlüğü OCR öncesi 1200 piksele indirerek bellek taşmasını önler
    img_opt = img.copy()
    img_opt.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    
    w, h = img_opt.size
    ocr_raw = reader.readtext(np.array(img_opt), detail=1, paragraph=False)
    ordered_ocr = sort_reading_order(ocr_raw)
    
    boxes = []
    for box, text, conf in ordered_ocr:
        x_pts = [p[0] for p in box]; y_pts = [p[1] for p in box]
        min_x, max_x = min(x_pts), max(x_pts)
        min_y, max_y = min(y_pts), max(y_pts)
        
        boxes.append({
            "id": f"b_{len(boxes)}",
            "text": text,
            "clean": clean_word_key(text),
            "left": (min_x / w) * 100,
            "top": (min_y / h) * 100,
            "width": ((max_x - min_x) / w) * 100,
            "height": ((max_y - min_y) / h) * 100
        })
    
    b64_str = compress_image_for_sheets(img_opt)
    del img_opt
    gc.collect()
    
    return {
        "img_b64": b64_str,
        "boxes": boxes
    }

# ==========================================
# 4. GİRİŞ EKRANI (AÇIKLAMA, DİL VE İMZA)
# ==========================================
if not st.session_state.logged_in:
    col_t_empty, col_lang = st.columns([3.5, 1.5])
    with col_lang:
        selected_lang = st.selectbox(
            "Language / Dil / Език:",
            options=["tr", "en", "bg"],
            format_func=lambda x: f"{LANGUAGES[x]['flag']} {LANGUAGES[x]['name']}",
            index=["tr", "en", "bg"].index(st.session_state.app_lang) if st.session_state.app_lang in ["tr", "en", "bg"] else 0,
            label_visibility="collapsed"
        )
        if selected_lang != st.session_state.app_lang:
            st.session_state.app_lang = selected_lang
            st.rerun()

    st.markdown(f"<h1 style='text-align: center; color: #1e3a8a; margin-bottom: 2px;'>{T('title')}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #64748b; font-size: 16px; margin-bottom: 20px;'>{T('subtitle')}</p>", unsafe_allow_html=True)
    
    col_l1, col_center, col_l2 = st.columns([1, 2.2, 1])
    with col_center:
        st.markdown(
            f"""
            <div style="background: rgba(30, 58, 138, 0.05); border: 1px solid rgba(30, 58, 138, 0.18); border-radius: 12px; padding: 18px; margin-bottom: 22px;">
                <h4 style="margin: 0 0 8px 0; color: #1e3a8a;">{T('purpose_title')}</h4>
                <p style="margin: 0 0 14px 0; font-size: 14.5px; line-height: 1.5; color: #334155;">{T('purpose_text')}</p>
                <h4 style="margin: 0 0 8px 0; color: #1e3a8a;">{T('usage_title')}</h4>
                <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #475569; white-space: pre-line;">{T('usage_text')}</p>
            </div>
            """, unsafe_allow_html=True
        )

        l_email = st.text_input(T("email_label"), key="log_email", placeholder="ornek@email.com")
        if st.button(T("login_btn"), type="primary", use_container_width=True):
            if l_email and "@" in l_email:
                success, user_data, msg = login_user(l_email)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_email = user_data.get("Email")
                    st.session_state.user_role = str(user_data.get("Role", "user")).lower()
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning(T("email_warn"))

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="text-align: center; color: #94a3b8; font-size: 13.5px; border-top: 1px solid #e2e8f0; padding-top: 15px;">
                ✍️ <b>{T('created_by')}</b>
            </div>
            """, unsafe_allow_html=True
        )

# ==========================================
# 5. OKUMA MODU (ZEN VIEWER - ÇOK DİLLİ)
# ==========================================
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

    if st.button(T("zen_close"), key="btn_exit_zen"):
        st.session_state.reading_mode = False
        st.rerun()

    pages = ensure_reading_ready(st.session_state.uploaded_book_pages, st.session_state.app_lang)
    pages_json = json.dumps(pages)
    target_flag = LANGUAGES[st.session_state.app_lang]["flag"]
    
    lbl_page = T("zen_page")
    lbl_listen = T("zen_listen")
    lbl_stop = T("zen_stop")
    lbl_page_trans = T("zen_page_trans")
    lbl_loading_trans = T("zen_loading_trans")

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
        <div id="page-counter" class="glass-pill hud-item">{lbl_page} 1 / 1</div>
        <div id="whisper-card"></div>
        <div id="main-dock" class="glass-dock hud-item">
            <button id="btn-prev" class="glass-btn" onclick="prevPage()">⬅️</button>
            <button id="btn-speed" class="glass-btn" onclick="cycleSpeed()" title="Speed">⚡ <span id="speed-text">0.8x</span></button>
            <button id="btn-karaoke" class="glass-btn" onclick="toggleKaraoke()">🎤 <span id="k-text">{lbl_listen}</span></button>
            <button id="btn-trans" class="glass-btn" onclick="toggleTranslation()">{target_flag} <span id="t-text">{lbl_page_trans}</span></button>
            <button id="btn-next" class="glass-btn" onclick="nextPage()">➡️</button>
        </div>
        <script>
            const allPages = {pages_json};
            const targetFlag = "{target_flag}";
            const txtPage = "{lbl_page}";
            const txtListen = "{lbl_listen}";
            const txtStop = "{lbl_stop}";
            const txtPageTrans = "{lbl_page_trans}";
            const txtLoading = "{lbl_loading_trans}";

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
                pageCounter.innerText = `${{txtPage}} ${{idx + 1}} / ${{allPages.length}}`;
                btnPrev.disabled = (idx === 0); btnNext.disabled = (idx === allPages.length - 1);
                card.style.display = 'none'; card.dataset.type = ''; layer.innerHTML = ''; wordIndices = []; let charOffset = 0;
                
                (page.boxes || []).forEach((b, i) => {{
                    wordIndices.push({{ idx: i, start: charOffset, end: charOffset + b.text.length }});
                    charOffset += b.text.length + 1;
                    const d = document.createElement('div'); d.className = 'word-hitbox'; d.id = 'box_' + i;
                    d.style.left = b.left + '%'; d.style.top = b.top + '%'; d.style.width = b.width + '%'; d.style.height = b.height + '%';
                    d.onclick = () => {{
                        resetHudTimer(); 
                        clearTimeout(timer);
                        const dict = page.dictionary || {{}};
                        const cleanKey = b.clean || b.text.toLowerCase().trim();
                        let trans = dict[cleanKey] || dict[b.text.toLowerCase().trim()] || dict[b.text] || '-';
                        if (trans === '-' || !trans) {{
                            let noPunct = b.text.replace(/^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$/g, "").trim().toLowerCase();
                            trans = dict[noPunct] || '-';
                        }}
                        card.innerHTML = "🇫🇷 <b>" + b.text + "</b> ➔ " + targetFlag + " " + trans; 
                        card.style.display = 'block';
                        card.dataset.type = 'word';
                        window.speechSynthesis.cancel(); 
                        const u = new SpeechSynthesisUtterance(b.text); 
                        u.lang = 'fr-FR'; 
                        u.rate = speeds[speedIdx]; 
                        window.speechSynthesis.speak(u);
                        timer = setTimeout(() => {{ card.style.display = 'none'; card.dataset.type = ''; }}, 4000);
                    }};
                    layer.appendChild(d);
                }});
            }}
            function nextPage() {{ resetHudTimer(); if (currentIndex < allPages.length - 1) loadPage(currentIndex + 1); }}
            function prevPage() {{ resetHudTimer(); if (currentIndex > 0) loadPage(currentIndex - 1); }}
            function toggleTranslation() {{
                resetHudTimer();
                clearTimeout(timer);
                const transText = (allPages[currentIndex] && allPages[currentIndex].full_trans) ? allPages[currentIndex].full_trans : txtLoading;
                if (card.style.display === 'block' && card.dataset.type === 'page') {{
                    card.style.display = 'none';
                    card.dataset.type = '';
                }} else {{ 
                    card.innerHTML = "📝 <b>" + txtPageTrans + ":</b> " + transText; 
                    card.style.display = 'block'; 
                    card.dataset.type = 'page';
                }}
            }}
            function toggleKaraoke() {{ resetHudTimer(); if (isPlaying) stopKaraoke(); else playKaraoke(); }}
            function playKaraoke() {{
                window.speechSynthesis.cancel(); isPlaying = true; btnKaraoke.classList.add('active'); document.getElementById('k-text').innerText = txtStop;
                const page = allPages[currentIndex]; let fullSentence = (page.boxes || []).map(b => b.text).join(' ');
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
                    if (!isPlaying || !page.boxes || fallbackIdx >= page.boxes.length) return;
                    if (!usedBoundary) {{ document.querySelectorAll('.word-hitbox').forEach(el => el.classList.remove('karaoke-lit')); const el = document.getElementById('box_' + fallbackIdx); if (el) el.classList.add('karaoke-lit'); }}
                    let dur = ((page.boxes[fallbackIdx].text.length * 60) + 50) / speeds[speedIdx]; fallbackIdx++; timer = setTimeout(stepFallback, dur);
                }}
                u.onend = stopKaraoke; u.onerror = stopKaraoke; window.speechSynthesis.speak(u); stepFallback();
            }}
            function stopKaraoke() {{ isPlaying = false; clearTimeout(timer); window.speechSynthesis.cancel(); btnKaraoke.classList.remove('active'); document.getElementById('k-text').innerText = txtListen; document.querySelectorAll('.word-hitbox').forEach(el => el.classList.remove('karaoke-lit')); }}
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

# ==========================================
# 6. DÜZENLEYİCİ EKRANI (ADMIN)
# ==========================================
elif st.session_state.editor_mode:
    st.subheader(f"✏️ Kitap Düzenleyici: {st.session_state.editor_book_title}")
    
    col_t1, col_t2, col_t3, col_t4 = st.columns([2.5, 1.5, 1.5, 1])
    with col_t1:
        st.session_state.editor_book_title = st.text_input("Kitap Başlığı:", value=st.session_state.editor_book_title, label_visibility="collapsed")
    with col_t2:
        if st.button(T("save_changes"), type="secondary", use_container_width=True):
            with st.spinner(T("saving_db")):
                saved_f, msg = save_hybrid_book(st.session_state.editor_book_title, st.session_state.editor_pages, st.session_state.editor_orig_book_id)
                if saved_f:
                    st.session_state.editor_orig_book_id = saved_f
                    st.success(msg)
                else:
                    st.error(msg)
    with col_t3:
        if st.button(T("save_and_read"), type="primary", use_container_width=True):
            with st.spinner(T("saving_db")):
                saved_f, msg = save_hybrid_book(st.session_state.editor_book_title, st.session_state.editor_pages, st.session_state.editor_orig_book_id)
                if saved_f:
                    prepared = ensure_reading_ready(st.session_state.editor_pages, st.session_state.app_lang)
                    st.session_state.uploaded_book_pages = prepared
                    st.session_state.current_book_title = st.session_state.editor_book_title
                    st.session_state.editor_mode = False
                    st.session_state.reading_mode = True
                    st.rerun()
                else:
                    st.error(msg)
    with col_t4:
        if st.button(T("exit_editor"), use_container_width=True):
            st.session_state.editor_mode = False
            st.rerun()

    st.divider()
    pages = st.session_state.editor_pages
    total_p = len(pages)

    if total_p == 0:
        st.warning("Bu kitapta sayfa bulunmuyor.")
    else:
        if st.session_state.editor_page_idx >= total_p:
            st.session_state.editor_page_idx = total_p - 1
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
                    if st.session_state.editor_page_idx >= len(pages) and len(pages) > 0:
                        st.session_state.editor_page_idx = len(pages) - 1
                    st.rerun()

            img_html = f"""<div style="text-align: center; background: #0f172a; border-radius: 8px; padding: 10px; margin-top: 10px;">
                <img src="data:image/jpeg;base64,{curr_page['img_b64']}" style="max-width: 100%; max-height: 480px; object-fit: contain; border-radius: 4px;" /></div>"""
            st.markdown(img_html, unsafe_allow_html=True)

            with st.expander("➕ Bu Kitaba Yeni Sayfa Ekle"):
                new_single_file = st.file_uploader("Ek Sayfa Seç (PNG/JPG):", type=["png", "jpg", "jpeg"], key="add_new_p")
                if new_single_file and st.button("Taramaya Ekle"):
                    b_img = ImageOps.exif_transpose(Image.open(new_single_file)).convert("RGB")
                    new_page_obj = process_single_image(b_img)
                    pages.append(new_page_obj)
                    del b_img
                    gc.collect()
                    st.session_state.editor_page_idx = len(pages) - 1
                    st.rerun()

        with col_right:
            st.markdown("### 🔤 Tespit Edilen Kelimeler")
            if st.button("🧹 Sayfa Numaralarını Otomatik Kaldır"):
                curr_page["boxes"] = [b for b in curr_page["boxes"] if not b["text"].strip().isdigit()]
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
                        orig_box["clean"] = clean_word_key(orig_box["text"])
                        new_boxes.append(orig_box)
                curr_page["boxes"] = new_boxes
                st.success("Güncellendi!")
                time.sleep(0.4)
                st.rerun()

# ==========================================
# 7. ANA KÜTÜPHANE EKRANI (VELİ & ADMIN)
# ==========================================
else:
    col_info1, col_thanks, col_info2, col_info3 = st.columns([2.5, 1.2, 1.8, 1])
    with col_info1:
        st.markdown(f"👤 **{T('welcome')}:** `{st.session_state.user_email}`")
    with col_thanks:
        if st.button(T("thanks_btn"), use_container_width=True):
            if record_thanks(st.session_state.user_email):
                st.balloons()
                st.toast(T("thanks_success"), icon="❤️")
    with col_info2:
        new_lang = st.selectbox(
            T("reading_lang_label"),
            options=["tr", "en", "bg"],
            format_func=lambda x: f"{LANGUAGES[x]['flag']} {LANGUAGES[x]['name']}",
            index=["tr", "en", "bg"].index(st.session_state.app_lang) if st.session_state.app_lang in ["tr", "en", "bg"] else 0,
            label_visibility="collapsed"
        )
        if new_lang != st.session_state.app_lang:
            st.session_state.app_lang = new_lang
            st.rerun()
    with col_info3:
        if st.button(T("logout"), use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    if st.session_state.user_role == "admin":
        _client, _err, _email = get_gsheet_client()
        if _client:
            _test_sheet, _sheet_err = get_sheet("Library")
            if _test_sheet:
                st.caption(f"🟢 **Google Sheets Bağlantısı Aktif** (Admin Modu)")
            else:
                st.error(_sheet_err)
        else:
            st.error(_err)

    if st.session_state.user_role == "admin":
        tabs = [T("lib_title"), T("add_tab")]
        app_tabs = st.tabs(tabs)
        tab_havuz = app_tabs[0]
        tab_ekle = app_tabs[1]
    else:
        st.markdown(f"<h2 style='text-align: center; color: #1e3a8a; margin-top:15px;'>{T('lib_title')}</h2>", unsafe_allow_html=True)
        tab_havuz = st.container()
        tab_ekle = None

    with tab_havuz:
        saved_books, b_err = get_saved_books()
        if b_err:
            st.error(f"Kitap listesi yüklenemedi: {b_err}")
        elif not saved_books:
            st.info(T("empty_lib"))
        else:
            book_titles = {b["book_id"]: f"{b['title']} ({b['page_count']} sayfa)" for b in saved_books}
            selected_id = st.selectbox(T("select_book"), options=list(book_titles.keys()), format_func=lambda x: book_titles[x])
            
            if st.session_state.user_role == "admin":
                col_r, col_e, col_d = st.columns([2, 2, 1])
                with col_r:
                    if st.button(T("open_read"), type="primary", use_container_width=True):
                        with st.spinner("Kitap yükleniyor..."):
                            book_pages, l_err = load_book_content(selected_id)
                            if book_pages:
                                st.session_state.uploaded_book_pages = book_pages
                                st.session_state.current_book_title = next((b["title"] for b in saved_books if b["book_id"] == selected_id), "")
                                st.session_state.reading_mode = True
                                st.rerun()
                            else:
                                st.error(l_err)
                with col_e:
                    if st.button(T("edit_book"), use_container_width=True):
                        with st.spinner("Kitap yükleniyor..."):
                            book_pages, l_err = load_book_content(selected_id)
                            if book_pages:
                                st.session_state.editor_pages = book_pages
                                st.session_state.editor_book_title = next((b["title"] for b in saved_books if b["book_id"] == selected_id), "")
                                st.session_state.editor_orig_book_id = selected_id
                                st.session_state.editor_page_idx = 0
                                st.session_state.editor_mode = True
                                st.rerun()
                            else:
                                st.error(l_err)
                with col_d:
                    if st.button(T("delete_book"), use_container_width=True):
                        delete_hybrid_book(selected_id)
                        st.success(T("delete_confirm"))
                        time.sleep(0.5)
                        st.rerun()
            else:
                if st.button(T("open_read"), type="primary", use_container_width=True):
                    with st.spinner("Kitap yükleniyor..."):
                        book_pages, l_err = load_book_content(selected_id)
                        if book_pages:
                            st.session_state.uploaded_book_pages = book_pages
                            st.session_state.current_book_title = next((b["title"] for b in saved_books if b["book_id"] == selected_id), "")
                            st.session_state.reading_mode = True
                            st.rerun()
                        else:
                            st.error(l_err)

    if tab_ekle:
        with tab_ekle:
            book_title_input = st.text_input("Kitabın Adı (Örn: Le Petit Poucet):", value="Yeni Kitap")
            uploaded_files = st.file_uploader("Kitap sayfalarını seçin (PNG, JPG):", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
            split_spreads = st.checkbox("📖 Çift Sayfa Çekimlerini Otomatik İkiye Böl", value=True)

            if uploaded_files:
                if st.button("⚡ Taramayı Başlat & Düzenleyiciye Aktar", type="primary", use_container_width=True):
                    extracted_pages = []
                    total_files = len(uploaded_files)
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for f_idx, file in enumerate(uploaded_files):
                        status_text.text(f"İşleniyor: Görsel {f_idx + 1} / {total_files}...")
                        base_img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
                        
                        sub_images = []
                        if split_spreads and (base_img.width / base_img.height) > 1.25:
                            mid_x = base_img.width // 2
                            sub_images.append(base_img.crop((0, 0, mid_x, base_img.height)))
                            sub_images.append(base_img.crop((mid_x, 0, base_img.width, base_img.height)))
                        else:
                            sub_images.append(base_img)
                        
                        for sub_img in sub_images:
                            page_obj = process_single_image(sub_img)
                            extracted_pages.append(page_obj)
                            del sub_img
                        
                        del base_img
                        del sub_images
                        gc.collect()
                        progress_bar.progress((f_idx + 1) / total_files)
                    
                    status_text.text("Tarama tamamlandı! Düzenleyiciye aktarılıyor...")
                    st.session_state.editor_pages = extracted_pages
                    st.session_state.editor_book_title = book_title_input.strip() or "İsimsiz Kitap"
                    st.session_state.editor_orig_book_id = None
                    st.session_state.editor_page_idx = 0
                    st.session_state.editor_mode = True
                    st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="text-align: center; color: #94a3b8; font-size: 13.5px; border-top: 1px solid #e2e8f0; padding-top: 15px;">
            ✍️ <b>{T('created_by')}</b>
        </div>
        """, unsafe_allow_html=True
    )
