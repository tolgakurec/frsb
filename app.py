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

try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from streamlit_cropper import st_cropper
    CROPPER_SUPPORT = True
except ImportError:
    CROPPER_SUPPORT = False

st.set_page_config(
    page_title="Fransızca Hikaye Kütüphanesi",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 0. HİKAYE METİNLERİ VE ARAYÜZ ÇEVİRİLERİ
# ==========================================
STORY_PARAGRAPHS = [
    {
        "tr": "Sofya’da Kalan Gençlik: Bir İmparatorluğun İhtişamı ve Yarım Kalan Bir Aşk",
        "fr": "La Jeunesse laissée à Sofia : La splendeur d'un empire et un amour inachevé"
    },
    {
        "tr": "Yıl 1914. Balkan Savaşları'nın barut kokusu henüz dağılmamış, Avrupa'nın üzerinde yaklaşan Büyük Savaş'ın kara bulutları toplanırken, Sofya'nın soğuk sokakları o gece Askerî Kulüp'ten yükselen vals ezgileriyle ısınıyordu. 11 Mayıs gecesi, Bulgar Kralı Ferdinand'ın ev sahipliğinde düzenlenen bu görkemli maskeli balo, sıradan bir diplomatik davet değil; tarihin en zarif meydan okumalarından birine ve son nefese kadar unutulmayacak, kalpleri sızlatan bir aşka sahne olacaktı.",
        "fr": "L'année 1914. L'odeur de poudre des guerres balkaniques ne s'était pas encore dissipée et les sombres nuages de la Grande Guerre imminente s'amoncelaient sur l'Europe, tandis que les rues froides de Sofia étaient réchauffées par les airs de valse s'échappant du Club Militaire ce soir-là. Ce grand bal masqué, organisé par le roi Ferdinand de Bulgarie dans la nuit du 11 mai, n'était pas une simple invitation diplomatique ; il allait être le théâtre de l'un des défis les plus élégants de l'histoire et d'un amour déchirant qui ne serait jamais oublié jusqu'au dernier souffle."
    },
    {
        "tr": "Salonda Bir Yeniçeri Ağası",
        "fr": "Un Agha Janissaire dans le Salon"
    },
    {
        "tr": "Avrupalı diplomatlar, generaller ve elitler frakları, smokinleri ve şatafatlı elbiseleriyle salonu doldurmuşken, devasa kapılar ağır ağır açıldı. İçeriye adım atan adam, henüz 32 yaşında genç ve karizmatik bir Osmanlı Kurmay Yarbayı olan Mustafa Kemal'di. Ancak o gece üzerinde alışıldık bir üniforma yoktu. Balkan Savaşları'nda zedelenen milletinin gururunu ayağa kaldırmak istercesine, İstanbul'dan, Harbiye Askerî Müzesi'nden gizlice getirttiği orijinal bir Yeniçeri Ağası kıyafetiyle salona girmişti. Börk serpuşu, gösterişli kuşağı ve belindeki kılıcıyla adeta geçmişin kudretli imparatorluğunun ete kemiğe bürünmüş haliydi.",
        "fr": "Alors que les diplomates, les généraux et l'élite européenne remplissaient la salle avec leurs queues-de-pie, leurs smokings et leurs robes flamboyantes, les portes géantes s'ouvrirent lentement. L'homme qui y entra était Mustafa Kemal, un jeune et charismatique lieutenant-colonel d'état-major ottoman âgé de 32 ans à peine. Cependant, il ne portait pas d'uniforme habituel ce soir-là. Comme pour relever la fierté de sa nation ébranlée par les guerres des Balkans, il était entré dans la salle avec une tenue originale d'Agha janissaire qu'il avait secrètement ramenée d'Istanbul, du Musée militaire de Harbiye. Avec sa coiffe en feutre, sa ceinture ostentatoire et l'épée à sa taille, il incarnait le puissant empire du passé."
    },
    {
        "tr": "O an salona derin, büyüleyici bir sessizlik çöktü; ardından bu sessizlik yerini devasa bir hayranlığa bıraktı. İşte yanda yer alan ve o tarihi balodaki büyüleyici anı yansıtan kareden de hissedilebileceği üzere, bu görkemli kostümün içindeki genç ataşe herkesi büyülemiş ve gecenin yıldızı olmuştu.",
        "fr": "À ce moment-là, un silence profond et fascinant tomba sur la salle ; puis ce silence fit place à une immense admiration. Comme on peut le voir sur la photo ci-contre qui reflète ce moment magique de ce bal historique, le jeune attaché dans ce magnifique costume avait fasciné tout le monde et était devenu la star de la soirée."
    },
    {
        "tr": "Mavi Tuna'nın Sularında Süzülen Bir Aşk: 'Bulgar Gülü' Miti",
        "fr": "Un amour planant sur les eaux du Danube bleu : Miti, la 'Rose Bulgare'"
    },
    {
        "tr": "Bu ihtişamlı gece, Mustafa Kemal için sadece bir diplomatik zafer değil, kalbinin derinliklerine kazınan bir sevdanın da en güzel sahnesiydi. Gecenin ilerleyen saatlerinde Johann Strauss'un 'Güzel Mavi Tuna' valsi çalmaya başladığında, Mustafa Kemal Bulgaristan’ın eski Savunma Bakanı General Kovaçev’in kızı Dimitrina Kovaçeva'ya, namıdiğer 'Miti'ye doğru ilerledi. İsviçre'de eğitim almış, yüksek kültürü ve eşsiz güzelliğiyle 'Bulgar Gülü' olarak anılan Miti ile Mustafa Kemal dansa kalktığında, Sofya sosyetesi için zaman adeta durdu.",
        "fr": "Cette magnifique soirée ne fut pas seulement un triomphe diplomatique pour Mustafa Kemal, ce fut aussi la plus belle scène d'un amour gravé au fond de son cœur. Plus tard dans la nuit, lorsque la valse du 'Beau Danube bleu' de Johann Strauss a commencé à jouer, Mustafa Kemal s'est avancé vers Dimitrina Kovacheva, fille de l'ancien ministre bulgare de la Défense, le général Kovachev, alias 'Miti'. Éduquée en Suisse et connue sous le nom de 'Rose bulgare' pour sa grande culture et sa beauté inégalée, lorsque Miti et Mustafa Kemal se sont levés pour danser, le temps s'est arrêté pour la haute société de Sofia."
    },
    {
        "tr": "Bu dans, aslında alevlenmiş bir aşkın toplum önündeki cesur bir ilanıydı. Boris Parkı'nda yaptıkları uzun romantik yürüyüşlerin, buz pateni pistindeki gizli bakışmaların taçlandığı andı. Mustafa Kemal, bu büyük aşka teslim olmuş ve Miti'ye evlenme teklif etmiş, genç kızdan tereddütsüz bir 'Evet' almıştı.",
        "fr": "Cette danse était en fait la déclaration courageuse devant la société d'un amour enflammé. C'était le couronnement de leurs longues promenades romantiques dans le parc Boris et de leurs regards secrets sur la patinoire. Mustafa Kemal, s'abandonnant à ce grand amour, avait demandé Miti en mariage et avait reçu un 'Oui' sans hésitation de la jeune fille."
    },
    {
        "tr": "Vatan Borcu ve Kırık Bir Kalp",
        "fr": "Le Devoir de la Patrie et un Cœur Brisé"
    },
    {
        "tr": "Fakat tarih, büyük aşkları genellikle büyük trajedilerle sınar. İki eski düşman millet... Biri Çatalca'ya kadar ilerlemiş bir Bulgar generalinin kızı, diğeri ise vatanının kurtuluşunu omuzlarında taşıyan bir Osmanlı subayı. General Kovaçev, din ve siyaset duvarlarını örerek bu aşka iki kez kesin bir dille karşı çıktı. General, kızını apar topar bir mühendisle nişanlayıp bu sevdayı koparıp atmaya çalışırken, Mustafa Kemal'in içindeki fırtınalar, yalnız geçirdiği günlerde dostu Salih Bozok'a yazdığı mektuptaki şu dizelere dökülüyordu:",
        "fr": "Mais l'histoire met souvent les grands amours à l'épreuve des grandes tragédies. Deux anciennes nations ennemies... L'une est la fille d'un général bulgare qui a avancé jusqu'à Çatalca, l'autre est un officier ottoman qui porte la libération de sa patrie sur ses épaules. Le général Kovachev s'est opposé à cet amour à deux reprises avec un ton catégorique, construisant des murs de religion et de politique. Alors que le général tentait d'arracher cet amour en fiançant précipitamment sa fille à un ingénieur, les tempêtes intérieures de Mustafa Kemal se déversaient dans les lignes suivantes d'une lettre qu'il écrivit à son ami Salih Bozok pendant ses jours de solitude :"
    },
    {
        "tr": "'Hayat kısacık... birazcık umut, birazcık aşk ve sonra elveda...'",
        "fr": "'La vie est très courte... un peu d'espoir, un peu d'amour et puis adieu...'"
    },
    {
        "tr": "Genç yarbay, Madam Corinne'e yazdığı mektuplarda ise acısını ve yaralı kalbini büyük bir ideale gömdüğünü fısıldıyordu: 'Benim ihtiraslarım var, hem de pek büyükleri... Ben bu ihtirasların gerçekleşmesini vatanıma büyük bir hizmet borcu olarak görüyorum.' Mustafa Kemal, yaklaşan cihan harbinin ayak seslerini duyuyor ve vatanı için kendi kalbinden vazgeçiyordu. Savaş tamtamları çalmaya başladığında, yarım kalan aşkını Sofya'da bırakarak Çanakkale Cephesi'ne, dünya tarihini değiştireceği o destana doğru yola çıktı.",
        "fr": "Dans ses lettres à Madame Corinne, le jeune lieutenant-colonel murmurait qu'il enterrait sa douleur et son cœur blessé dans un grand idéal : 'J'ai des ambitions, et des très grandes... Je considère la réalisation de ces ambitions comme un grand devoir envers ma patrie.' Mustafa Kemal entendait les bruits de pas de la guerre mondiale imminente et renonçait à son propre cœur pour sa patrie. Lorsque les tambours de guerre commencèrent à battre, il laissa son amour inachevé à Sofia et partit pour le front des Dardanelles, pour l'épopée où il allait changer l'histoire du monde."
    },
    {
        "tr": "'Gençliğimi Bıraktım Sofya'da...'",
        "fr": "'J'ai laissé ma jeunesse à Sofia...'"
    },
    {
        "tr": "Yıllar su gibi aktı. Mustafa Kemal bir imparatorluğun küllerinden yepyeni bir cumhuriyet kurup dünyanın saygı duyduğu bir lider oldu. Miti ise ailesinin zoruyla evlenip saygın bir eş ve anne olarak hayatına devam etti. Ancak ikisinin de kalbindeki o ince sızı, o Mavi Tuna valsinde yarım kalan melodi hiç susmadı. Miti, yıllarca Atatürk'ün her başarısını Bulgar gazetelerinden yaşlı gözlerle takip etti. Atatürk ise yıllar sonra Ankara'da o günleri anımsadığında, içindeki sönmeyen hüznü şu sözlerle itiraf edecekti:",
        "fr": "Les années passèrent comme de l'eau. Mustafa Kemal a construit une toute nouvelle république sur les cendres d'un empire et est devenu un leader respecté du monde entier. Miti, en revanche, a été forcée de se marier par sa famille et a poursuivi sa vie en tant qu'épouse et mère respectée. Mais la fine douleur dans leurs deux cœurs, la mélodie inachevée de cette valse du Danube bleu ne s'est jamais tue. Pendant des années, Miti a suivi chaque succès d'Atatürk dans les journaux bulgares, les larmes aux yeux. Atatürk, d'autre part, lorsqu'il s'est souvenu de ces jours à Ankara des années plus tard, confessait sa tristesse inextinguible avec ces mots :"
    },
    {
        "tr": "'Bir kız sevdim ataşeyken, vermediler. Gençliğimi bıraktım Sofya'da...'",
        "fr": "'J'ai aimé une fille quand j'étais attaché, ils ne me l'ont pas donnée. J'ai laissé ma jeunesse à Sofia...'"
    },
    {
        "tr": "Bu destansı sevdanın son perdesi ise, Ağustos 1966'da, Sofya rüzgarlarından çok uzakta kapandı. Miti, ölüm döşeğinde son nefesini vermeden hemen önce, başucunda bekleyen kız kardeşine şu sarsıcı cümleyi fısıldadı:",
        "fr": "Le dernier acte de cet amour épique s'est clos en août 1966, loin des vents de Sofia. Miti, juste avant de rendre son dernier souffle sur son lit de mort, a murmuré cette phrase bouleversante à sa sœur qui l'attendait à son chevet :"
    },
    {
        "tr": "'Biliyor musun? Rüyamda onu gördüm. Sanıyorum ki nihayet Mustafa Kemal’e kavuşacağım...'",
        "fr": "'Tu sais ? Je l'ai vu dans mon rêve. Je pense que je vais enfin retrouver Mustafa Kemal...'"
    },
    {
        "tr": "Askerî Kulüp'teki o büyülü vals ve ölümsüz aşk, bugün tarihin sayfalarında sadece askeri bir dehanın değil; vatanı için en derin sevgisinden vazgeçmek zorunda kalan bir devin en insani, en hüzünlü hatırası olarak yankılanmaya devam ediyor.",
        "fr": "Cette valse magique au Club et cet amour immortel continuent de résonner aujourd'hui dans les pages de l'histoire, non seulement comme le souvenir d'un génie militaire, mais aussi comme le souvenir le plus humain et le plus triste d'un géant qui a dû renoncer à son amour le plus profond pour sa patrie."
    }
]

UI_TRANSLATIONS = {
    "tr": {
        "title": "📚 Fransızca Hikaye Kütüphanesi",
        "subtitle": "Fransızca Hikayeleri Keşfet ve Birlikte Öğren",
        "created_by": "Bu uygulama Tolga Küreç tarafından oluşturulmuştur (Timuçin ve Teoman'ın Babası)",
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
        "split_page_btn": "✂️ Bu Çift Sayfayı İkiye Böl",
        "ocr_processing": "Görseller taranıyor...",
        "reading_lang_label": "Okuma & Çeviri Dili:",
        "zen_close": "✕ Kapat",
        "zen_page": "Sayfa",
        "zen_listen": "Sesli Dinle",
        "zen_stop": "Durdur",
        "zen_page_trans": "Sayfa Çevirisi",
        "miti_title": "Sofya’da Kalan Gençlik: Bir İmparatorluğun İhtişamı ve Yarım Kalan Bir Aşk",
        "miti_exit": "✕ Çıkış / Exit",
        "listen_fr": "🔊 Fransızca Dinle",
        "listen_sys": "🔊 Türkçe Dinle",
        "stop_btn": "⏹ Durdur"
    },
    "en": {
        "title": "📚 French Storybook Library",
        "subtitle": "Explore French Stories & Learn Together",
        "created_by": "This application was created by Tolga Küreç (Father of Timuçin & Teoman)",
        "email_label": "Your Email Address:",
        "login_btn": "Sign In",
        "email_warn": "Please enter a valid email address.",
        "welcome": "Welcome",
        "logout": "🚪 Sign Out",
        "thanks_btn": "❤️ Send Thanks",
        "thanks_success": "Your thank-you note was sent to Tolga Küreç!",
        "lib_title": "📖 Library Pool",
        "add_tab": "➕ Add New Book",
        "empty_lib": "There are no books in the library yet.",
        "select_book": "Select a book to read:",
        "open_read": "🚀 Open & Read",
        "edit_book": "✏️ Edit Book",
        "delete_book": "🗑️ Delete",
        "delete_confirm": "Book deleted successfully.",
        "save_changes": "💾 Save Changes",
        "save_and_read": "🚀 Save & Read Now",
        "exit_editor": "✕ Exit",
        "split_page_btn": "✂️ Split Double Page",
        "ocr_processing": "Processing pages with OCR...",
        "reading_lang_label": "Translation Language:",
        "zen_close": "✕ Close",
        "zen_page": "Page",
        "zen_listen": "Listen Aloud",
        "zen_stop": "Stop",
        "zen_page_trans": "Page Translation",
        "miti_title": "The Youth Left in Sofia: The Splendor of an Empire and an Unfinished Love",
        "miti_exit": "✕ Exit",
        "listen_fr": "🔊 Listen in French",
        "listen_sys": "🔊 Listen in English",
        "stop_btn": "⏹ Stop"
    },
    "bg": {
        "title": "📚 Френска библиотека с приказки",
        "subtitle": "Открийте френските приказки и учете заедно",
        "created_by": "Това приложение е създадено от Толга Кюреч (Бащата на Тимучин и Теоман)",
        "email_label": "Вашият имейл адрес:",
        "login_btn": "Вход",
        "email_warn": "Моля, въведете валиден имейл адрес.",
        "welcome": "Добре дошли",
        "logout": "🚪 Изход",
        "thanks_btn": "❤️ Изпрати благодарност",
        "thanks_success": "Вашата благодарност бе изпратена на Толга Кюреч!",
        "lib_title": "📖 Библиотека",
        "add_tab": "➕ Добави нова книга",
        "empty_lib": "В библиотеката все още няма добавени книги.",
        "select_book": "Изберете книга за четене:",
        "open_read": "🚀 Отвори и чети",
        "edit_book": "✏️ Редактирай",
        "delete_book": "🗑️ Изтрий",
        "delete_confirm": "Книгата бе изтрита успешно.",
        "save_changes": "💾 Запази промените",
        "save_and_read": "🚀 Запази и чети веднага",
        "exit_editor": "✕ Изход",
        "split_page_btn": "✂️ Раздели двойната страница",
        "ocr_processing": "Обработка на страниците...",
        "reading_lang_label": "Език за превод:",
        "zen_close": "✕ Затвори",
        "zen_page": "Страница",
        "zen_listen": "Слушай",
        "zen_stop": "Спри",
        "zen_page_trans": "Превод на страницата",
        "miti_title": "Младостта, оставена в София: Великолепието на една империя и една недовършена любов",
        "miti_exit": "✕ Изход",
        "listen_fr": "🔊 Слушай на френски",
        "listen_sys": "🔊 Слушай на български",
        "stop_btn": "⏹ Спри"
    }
}

LANGUAGES = {
    "tr": {"name": "Türkçe", "flag": "🇹🇷"},
    "en": {"name": "English", "flag": "🇬🇧"},
    "bg": {"name": "Български", "flag": "🇧🇬"}
}

if "app_lang" not in st.session_state: st.session_state.app_lang = "tr"
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "user_role" not in st.session_state: st.session_state.user_role = "user"
if "reading_mode" not in st.session_state: st.session_state.reading_mode = False
if "miti_mode" not in st.session_state: st.session_state.miti_mode = False
if "editor_mode" not in st.session_state: st.session_state.editor_mode = False
if "uploaded_book_pages" not in st.session_state: st.session_state.uploaded_book_pages = []
if "current_book_title" not in st.session_state: st.session_state.current_book_title = ""
if "editor_pages" not in st.session_state: st.session_state.editor_pages = []
if "editor_book_title" not in st.session_state: st.session_state.editor_book_title = ""
if "editor_orig_book_id" not in st.session_state: st.session_state.editor_orig_book_id = None
if "editor_page_idx" not in st.session_state: st.session_state.editor_page_idx = 0
if "staged_camera_pages" not in st.session_state: st.session_state.staged_camera_pages = []

def T(key):
    lang = st.session_state.app_lang if st.session_state.app_lang in UI_TRANSLATIONS else "tr"
    return UI_TRANSLATIONS[lang].get(key, UI_TRANSLATIONS["tr"].get(key, key))

@st.cache_data(show_spinner=False)
def translate_ui_text(text, target_lang):
    if target_lang == "tr": return text
    if not text or not text.strip(): return ""
    clients = ['gtx', 'dict-chrome-ex']
    for client in clients:
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client={client}&sl=tr&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req, timeout=5)
            data = json.loads(res.read().decode('utf-8'))
            translated_parts = []
            if data and data[0]:
                for s in data[0]:
                    if s and s[0]: translated_parts.append(s[0])
            res_str = "".join(translated_parts).strip()
            if res_str: return res_str
        except Exception:
            continue
    return text

def get_file_base64(filename, mime_type):
    """GitHub reposundaki yerel dosyayı (resim/mp3) Base64 olarak okur"""
    script_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
    paths = [filename, os.path.join(script_dir, filename)]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    return f"data:{mime_type};base64,{b64}"
            except Exception:
                pass
    return ""

def get_ataturk_img_data():
    img_b64 = get_file_base64("ataturk_miti.jpg", "image/jpeg")
    if not img_b64:
        img_b64 = get_file_base64("atatürk ve miti.jpg", "image/jpeg")
    if img_b64:
        return img_b64
    return "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Mustafa_Kemal_Atat%C3%BCrk_in_janissary_costume.jpg/440px-Mustafa_Kemal_Atat%C3%BCrk_in_janissary_costume.jpg"

def get_blue_danube_audio_data():
    audio_b64 = get_file_base64("blue_danube.mp3", "audio/mp3")
    if audio_b64:
        return audio_b64
    return "https://upload.wikimedia.org/wikipedia/commons/transcoded/e/e0/Johann_Strauss_II_-_The_Blue_Danube_Waltz.ogg/Johann_Strauss_II_-_The_Blue_Danube_Waltz.ogg.mp3"

# ==========================================
# 1. GOOGLE SHEETS ENTEGRASYONU
# ==========================================
def clean_private_key(key_str):
    if not key_str or not isinstance(key_str, str): return key_str
    return key_str.replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n").strip()

def get_service_account_dict():
    creds_dict = None
    if hasattr(st, "secrets"):
        if "gcp_json" in st.secrets:
            raw = st.secrets["gcp_json"]
            creds_dict = json.loads(raw) if isinstance(raw, str) else dict(raw)
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
    if not creds_dict:
        for fname in ["google_secret.json", "secrets.json", "service_account.json"]:
            if os.path.exists(fname):
                try:
                    with open(fname, "r", encoding="utf-8") as f: creds_dict = json.load(f); break
                except: pass
    if creds_dict and "private_key" in creds_dict:
        creds_dict["private_key"] = clean_private_key(creds_dict["private_key"])
    return creds_dict

@st.cache_resource
def get_gsheet_client():
    if not GSHEETS_INSTALLED: return None, "gspread veya oauth2client eksik.", ""
    creds_dict = get_service_account_dict()
    if not creds_dict: return None, "Google kimlik anahtarı bulunamadı!", ""
    sa_email = creds_dict.get("client_email", "Bilinmeyen Servis Hesabı")
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client, None, sa_email
    except Exception as e: return None, f"Yetkilendirme Hatası: {str(e)}", sa_email

def get_sheet(sheet_name):
    client, err, sa_email = get_gsheet_client()
    if not client: return None, err
    try: doc = client.open_by_key("1Ec0v2Oo-7BlILvb35TGgo5j-SOGivJwmf5xpF85oGoU")
    except Exception as e: return None, f"Tablo açılamadı! (Hata: {str(e)})"
    try: return doc.worksheet(sheet_name), None
    except Exception as e: return None, f"'{sheet_name}' sekmesi bulunamadı!"

def login_user(email):
    email = email.lower().strip()
    if email == "tolgakurec@gmail.com": return True, {"Email": email, "Role": "admin"}, "Giriş Başarılı"
    sheet, err = get_sheet("Users")
    if not sheet: return False, None, err
    try:
        records = sheet.get_all_records()
        for r in records:
            if str(r.get("Email", "")).lower().strip() == email: return True, r, "Giriş başarılı."
        sheet.append_row([email, "user"])
        return True, {"Email": email, "Role": "user"}, "Kayıt edildi."
    except Exception as e: return False, None, str(e)

def record_thanks(email):
    sheet, err = get_sheet("Thanks")
    if not sheet: return False
    try:
        sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email, "Teşekkür Gönderildi"])
        return True
    except: return False

def get_saved_books():
    sheet, err = get_sheet("Library")
    if not sheet: return [], err
    try:
        records = sheet.get_all_records()
        books_list, seen_ids = [], set()
        for r in records:
            b_id = str(r.get("BookID", ""))
            if not b_id or b_id in seen_ids: continue
            seen_ids.add(b_id)
            books_list.append({"book_id": b_id, "title": r.get("BookName", "İsimsiz"), "page_count": r.get("PageCount", 0)})
        return sorted(books_list, key=lambda x: x["title"]), None
    except Exception as e: return [], str(e)

def load_book_content(book_id):
    sheet, err = get_sheet("Pages")
    if not sheet: return None, err
    try:
        records = sheet.get_all_records()
        pages = []
        for r in records:
            if str(r.get("BookID", "")) == book_id:
                try: boxes = json.loads(r.get("OCRText", "[]"))
                except: boxes = []
                pages.append({"page_no": int(r.get("PageNo", 0)), "img_b64": r.get("ImageBase64", ""), "boxes": boxes})
        if not pages: return None, "Sayfa verisi yok."
        return sorted(pages, key=lambda x: x["page_no"]), None
    except Exception as e: return None, str(e)

def save_hybrid_book(title, pages, old_book_id=None):
    lib_sheet, err1 = get_sheet("Library")
    pages_sheet, err2 = get_sheet("Pages")
    if not lib_sheet or not pages_sheet: return None, "Veritabanı hatası."
    try:
        if old_book_id:
            book_id = old_book_id
            for i, r in enumerate(lib_sheet.get_all_records()):
                if str(r.get("BookID", "")) == book_id: lib_sheet.delete_rows(i + 2); break
            page_records = pages_sheet.get_all_records()
            rows_to_del = [i + 2 for i, r in enumerate(page_records) if str(r.get("BookID", "")) == book_id]
            for row_idx in reversed(rows_to_del): pages_sheet.delete_rows(row_idx); time.sleep(0.1)
        else: book_id = str(uuid.uuid4())[:8]
        
        lib_sheet.append_row([book_id, title, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(pages)])
        all_page_rows = [[book_id, idx + 1, page["img_b64"], json.dumps(page["boxes"], ensure_ascii=False)] for idx, page in enumerate(pages)]
        for i in range(0, len(all_page_rows), 10): pages_sheet.append_rows(all_page_rows[i:i + 10]); time.sleep(0.5)
        return book_id, "Kitap kaydedildi!"
    except Exception as e: return None, str(e)

def delete_hybrid_book(book_id):
    lib_sheet, _ = get_sheet("Library")
    pages_sheet, _ = get_sheet("Pages")
    if lib_sheet:
        for i, r in enumerate(lib_sheet.get_all_records()):
            if str(r.get("BookID", "")) == book_id: lib_sheet.delete_rows(i + 2); break
    if pages_sheet:
        rows_to_delete = [i + 2 for i, r in enumerate(pages_sheet.get_all_records()) if str(r.get("BookID", "")) == book_id]
        for row_idx in reversed(rows_to_delete): pages_sheet.delete_rows(row_idx); time.sleep(0.1)

# ==========================================
# 3. OCR, ÇEVİRİ VE DİNAMİK SÖZLÜK MOTORU
# ==========================================
@st.cache_resource
def load_ocr(): return easyocr.Reader(['fr', 'en'], gpu=False)
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
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        parsed.append({'item': item, 'min_x': min_x, 'cy': (min_y + max_y) / 2.0, 'h': max(max_y - min_y, 1.0)})
    parsed.sort(key=lambda p: p['cy'])
    lines = []
    for p in parsed:
        matched_line = None
        for line in lines:
            avg_cy = sum(k['cy'] for k in line) / len(line)
            avg_h = sum(k['h'] for k in line) / len(line)
            if abs(p['cy'] - avg_cy) < (max(avg_h, p['h']) * 0.65): matched_line = line; break
        if matched_line: matched_line.append(p)
        else: lines.append([p])
    lines.sort(key=lambda line: sum(k['cy'] for k in line) / len(line))
    return [p['item'] for line in lines for p in sorted(line, key=lambda p: p['min_x'])]

def clean_word_key(text):
    if not text: return ""
    return re.sub(r"\s+", " ", re.sub(r"^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$", "", text).strip().lower())

def build_coherent_page_text(boxes):
    if not boxes: return ""
    filtered = [b.get("text", "").strip() for b in boxes if b.get("text", "").strip() and not re.fullmatch(r'[\s\-\.–—]*\d{1,3}[\s\-\.–—]*', b.get("text", "").strip())]
    if not filtered: return ""
    cleaned, i = [], 0
    while i < len(filtered):
        curr = filtered[i]
        if i + 1 < len(filtered) and len(curr) == 1 and curr.isalpha() and filtered[i+1]:
            cleaned.append(curr + filtered[i+1]); i += 2; continue
        cleaned.append(curr); i += 1
    fs = " ".join(cleaned)
    fs = re.sub(r'(\w+)[\-\–]\s+(\w+)', r'\1\2', fs)
    fs = re.sub(r'\s+([,.;:!?])', r'\1', fs)
    return re.sub(r'\s+', ' ', re.sub(r'([.!?])([A-Za-zÀ-ÿ])', r'\1 \2', fs)).strip()

@st.cache_data(show_spinner=False)
def translate_text(text, target_lang):
    return translate_ui_text(text, target_lang)

@st.cache_data(show_spinner=False)
def get_words_dictionary(texts_list, target_lang):
    trans_map, unique_items = {}, set()
    for raw in texts_list:
        clean = clean_word_key(raw)
        if clean: unique_items.add(clean)
        for word in re.findall(r"[\wÀ-ÿ'-]+", raw):
            w_clean = clean_word_key(word)
            if len(w_clean) > 1: unique_items.add(w_clean)
    items_list = sorted(list(unique_items))
    for i in range(0, len(items_list), 15):
        batch = items_list[i:i + 15]
        combined = "\n".join(batch)
        t_combined = translate_text(combined, target_lang)
        lines = [line.strip() for line in t_combined.split("\n") if line.strip()]
        if len(lines) == len(batch):
            for orig, trans in zip(batch, lines): trans_map[orig] = trans
        else:
            for orig in batch: trans_map[orig] = translate_text(orig, target_lang)
    return trans_map

def ensure_reading_ready(pages, target_lang):
    for page in pages:
        if page.get("current_lang") != target_lang or "full_trans" not in page or "dictionary" not in page:
            raw_texts = [b.get("text", "").strip() for b in page.get("boxes", []) if b.get("text", "").strip()]
            for b in page.get("boxes", []): b["clean"] = clean_word_key(b.get("text", ""))
            full_str = build_coherent_page_text(page.get("boxes", []))
            page["full_text"], page["full_trans"] = full_str, translate_text(full_str, target_lang)
            page["dictionary"] = get_words_dictionary(raw_texts, target_lang)
            page["current_lang"] = target_lang
    return pages

def process_single_image(img):
    img_opt = img.copy()
    img_opt.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    w, h = img_opt.size
    ordered_ocr = sort_reading_order(reader.readtext(np.array(img_opt), detail=1, paragraph=False))
    boxes = []
    for box, text, conf in ordered_ocr:
        x_pts, y_pts = [p[0] for p in box], [p[1] for p in box]
        min_x, max_x, min_y, max_y = min(x_pts), max(x_pts), min(y_pts), max(y_pts)
        boxes.append({
            "id": f"b_{len(boxes)}", "text": text, "clean": clean_word_key(text),
            "left": (min_x / w) * 100, "top": (min_y / h) * 100,
            "width": ((max_x - min_x) / w) * 100, "height": ((max_y - min_y) / h) * 100
        })
    b64_str = compress_image_for_sheets(img_opt)
    del img_opt; gc.collect()
    return {"img_b64": b64_str, "boxes": boxes}

# ==========================================
# 4. GİRİŞ EKRANI
# ==========================================
if not st.session_state.logged_in:
    col_t_empty, col_lang = st.columns([3.5, 1.5])
    with col_lang:
        selected_lang = st.selectbox("Language:", options=list(LANGUAGES.keys()), format_func=lambda x: f"{LANGUAGES[x]['flag']} {LANGUAGES[x]['name']}", index=list(LANGUAGES.keys()).index(st.session_state.app_lang) if st.session_state.app_lang in LANGUAGES else 0, label_visibility="collapsed")
        if selected_lang != st.session_state.app_lang: st.session_state.app_lang = selected_lang; st.rerun()

    st.markdown(f"<h1 style='text-align: center; color: #1e3a8a; margin-bottom: 2px;'>{T('title')}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #64748b; font-size: 16px; margin-bottom: 20px;'>{T('subtitle')}</p>", unsafe_allow_html=True)
    
    col_l1, col_center, col_l2 = st.columns([1, 2.2, 1])
    with col_center:
        l_email = st.text_input(T("email_label"), key="log_email", placeholder="ornek@email.com")
        if st.button(T("login_btn"), type="primary", use_container_width=True):
            if l_email and "@" in l_email:
                success, user_data, msg = login_user(l_email)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_email = user_data.get("Email")
                    st.session_state.user_role = str(user_data.get("Role", "user")).lower()
                    st.rerun()
                else: st.error(msg)
            else: st.warning(T("email_warn"))

# ==========================================
# 4.1. MİTİ & ATATÜRK ANMA SAYFASI (3 SÜTUNLU KUSURSUZ TASARIM)
# ==========================================
elif st.session_state.miti_mode:
    target_lang = st.session_state.app_lang
    img_data_uri = get_ataturk_img_data()
    audio_data_uri = get_blue_danube_audio_data()
    
    # Paragrafları seçilen dile göre çevir
    prepared_pairs = []
    for p in STORY_PARAGRAPHS:
        sys_text = translate_ui_text(p["tr"], target_lang) if target_lang != "tr" else p["tr"]
        prepared_pairs.append({
            "fr": p["fr"],
            "sys": sys_text
        })
    story_json = json.dumps(prepared_pairs, ensure_ascii=False)

    # 1. Çıkış Butonunu Ekranın Tam Üstüne Sabitleyen CSS (Z-INDEX 99999999)
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"], header, footer { display: none !important; }
            .block-container { padding: 0 !important; margin: 0 !important; max-width: 100vw !important; height: 100vh !important; overflow: hidden !important; background: #080c14 !important; }
            iframe { position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; border: none !important; z-index: 1 !important; }
            
            div[data-testid="stButton"], .stButton {
                position: fixed !important;
                top: 14px !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                z-index: 99999999 !important;
            }
            div[data-testid="stButton"] button, .stButton button {
                background: #dc2626 !important;
                border: 2px solid #fca5a5 !important;
                color: #ffffff !important;
                border-radius: 30px !important;
                padding: 8px 32px !important;
                font-weight: 800 !important;
                font-size: 15px !important;
                cursor: pointer !important;
                box-shadow: 0 4px 25px rgba(220, 38, 38, 0.6) !important;
                transition: all 0.2s ease !important;
            }
            div[data-testid="stButton"] button:hover, .stButton button:hover {
                background: #b91c1c !important;
                transform: scale(1.08) !important;
                box-shadow: 0 6px 30px rgba(220, 38, 38, 0.8) !important;
            }
        </style>
        """, unsafe_allow_html=True)

    # ÇIKIŞ BUTONU (Sistem Dilinde ve En Üstte Sabit)
    if st.button(T("miti_exit"), key="btn_top_exit"):
        st.session_state.miti_mode = False
        st.rerun()

    MITI_HTML = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            * {{ box-sizing: border-box; }}
            body {{ margin: 0; padding: 0; overflow: hidden; background-color: #080c14; color: #e2e8f0; font-family: 'Georgia', serif; height: 100vh; display: flex; }}
            
            /* Sütun 1: Sabit Fotoğraf (Sol Sütun) */
            #col-photo {{
                width: 30%; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center;
                padding: 65px 20px 20px 25px; background: #04060a; border-right: 1.5px dashed rgba(255,255,255,0.15); position: relative;
            }}
            #col-photo img {{
                max-width: 100%; max-height: 82vh; object-fit: contain; border-radius: 12px;
                box-shadow: 0 15px 45px rgba(0,0,0,0.85); border: 1px solid rgba(255,255,255,0.12);
            }}
            
            /* Sütun 2 ve 3: Metin Sütunları (Orta ve Sağ) */
            #col-french, #col-system {{
                width: 35%; height: 100vh; padding: 75px 25px 40px 25px; overflow-y: auto; scroll-behavior: smooth; position: relative;
            }}
            #col-french {{ border-right: 1.5px dashed rgba(255,255,255,0.15); }}
            
            /* Sticky Başlıklar ve Dinle Butonları */
            .col-header {{
                position: sticky; top: -75px; background: rgba(8, 12, 20, 0.95); backdrop-filter: blur(12px);
                padding: 10px 0 16px 0; z-index: 10; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 20px;
            }}
            .listen-btn {{
                display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%;
                background: rgba(251, 191, 36, 0.15); color: #fbbf24; border: 1.5px solid #fbbf24;
                padding: 11px 18px; border-radius: 25px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                font-size: 14.5px; font-weight: bold; cursor: pointer; transition: all 0.25s ease;
            }}
            .listen-btn:hover {{ background: #fbbf24; color: #000; transform: translateY(-1px); }}
            .listen-btn.active {{ background: #ef4444 !important; border-color: #ef4444 !important; color: #fff !important; }}
            
            /* Metin Paragrafları */
            .story-p {{
                font-size: 1.05rem; line-height: 1.85; margin-bottom: 18px; color: #cbd5e1;
                padding: 10px 14px; border-radius: 6px; transition: all 0.3s ease; text-align: justify;
            }}
            .story-title {{
                font-size: 1.35rem; font-weight: bold; color: #fbbf24; margin-bottom: 20px; line-height: 1.4; text-align: left;
                padding: 8px 12px;
            }}
            
            /* Kindle Stili Canlı Vurgulama */
            .highlight {{
                background-color: rgba(250, 204, 21, 0.28) !important;
                color: #ffffff !important;
                border-left: 5px solid #facc15 !important;
                padding-left: 16px !important;
                box-shadow: 0 0 20px rgba(250, 204, 21, 0.2) !important;
                border-radius: 4px !important;
            }}
            
            ::-webkit-scrollbar {{ width: 5px; }}
            ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.2); border-radius: 4px; }}
            
            /* Müzik Kontrol Butonu */
            #music-toggle {{
                position: fixed; bottom: 15px; left: 15px; z-index: 1000;
                background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255,255,255,0.2);
                color: #fbbf24; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-family: sans-serif;
                cursor: pointer; display: flex; align-items: center; gap: 8px; backdrop-filter: blur(8px);
                transition: all 0.2s;
            }}
            #music-toggle:hover {{ background: rgba(251, 191, 36, 0.2); transform: scale(1.04); }}
        </style>
    </head>
    <body>
        <!-- Yerel MP3 Dosyasından Doğrudan Çalan Ses Öğesi -->
        <audio id="bgMusic" src="{audio_data_uri}" loop preload="auto"></audio>

        <button id="music-toggle" onclick="toggleMusic(event)">🎵 <span id="m-state">Vals Çalıyor</span></button>

        <!-- 1. SÜTUN: ATATÜRK & MİTİ DANS FOTOĞRAFI -->
        <div id="col-photo">
            <img src="{img_data_uri}" alt="Atatürk ve Miti">
        </div>

        <!-- 2. SÜTUN: FRANSIZCA METİN -->
        <div id="col-french">
            <div class="col-header">
                <button class="listen-btn" id="btn-listen-fr" onclick="startReading('fr')">{T('listen_fr')}</button>
            </div>
            <div id="french-content"></div>
        </div>

        <!-- 3. SÜTUN: SİSTEM DİLİ METİN -->
        <div id="col-system">
            <div class="col-header">
                <button class="listen-btn" id="btn-listen-sys" onclick="startReading('sys')">{T('listen_sys')}</button>
            </div>
            <div id="system-content"></div>
        </div>

        <script>
            const paragraphs = {story_json};
            const frContent = document.getElementById("french-content");
            const sysContent = document.getElementById("system-content");
            const music = document.getElementById("bgMusic");
            music.volume = 0.35;

            // Metinleri Sütunlara Yerleştir
            let frHtml = "", sysHtml = "";
            paragraphs.forEach((p, idx) => {{
                let cls = (idx === 0 || idx === 2 || idx === 5 || idx === 8 || idx === 12) ? "story-title" : "story-p";
                frHtml += `<div class="${{cls}}" id="fr_p_${{idx}}">${{p.fr}}</div>`;
                sysHtml += `<div class="${{cls}}" id="sys_p_${{idx}}">${{p.sys}}</div>`;
            }});
            frContent.innerHTML = frHtml;
            sysContent.innerHTML = sysHtml;

            // Müziği Güvenli Başlatma & Otomatik Oynatma
            function playMusicSafe() {{
                if (!music) return;
                const p = music.play();
                if (p !== undefined) {{
                    p.then(() => {{
                        document.getElementById("m-state").innerText = "Vals Çalıyor 🎵";
                    }}).catch(() => {{
                        document.getElementById("m-state").innerText = "Valsi Başlat ▶️";
                    }});
                }}
            }}

            window.addEventListener("DOMContentLoaded", playMusicSafe);
            setTimeout(playMusicSafe, 400);

            // Kullanıcı ekranda herhangi bir yere ilk dokunduğunda müziği hemen başlat
            window.addEventListener("click", () => {{
                if (music.paused && !isReading) playMusicSafe();
            }}, {{ once: true }});
            window.addEventListener("touchstart", () => {{
                if (music.paused && !isReading) playMusicSafe();
            }}, {{ once: true }});

            function toggleMusic(e) {{
                e.stopPropagation();
                if (music.paused) {{
                    playMusicSafe();
                }} else {{
                    music.pause();
                    document.getElementById("m-state").innerText = "Valsi Başlat ▶️";
                }}
            }}

            // KINDLE STİLİ SENKRONİZE OKUMA & OTOMATİK KAYDIRMA
            let isReading = false;
            let currentLang = "";
            let currentIdx = 0;
            let activeUtterance = null; // Garbage collector engellemek için global tutulur

            function stopReading() {{
                isReading = false;
                currentLang = "";
                if (window.speechSynthesis) {{
                    window.speechSynthesis.cancel();
                }}
                const bFr = document.getElementById("btn-listen-fr");
                const bSys = document.getElementById("btn-listen-sys");
                if (bFr) {{ bFr.innerText = "{T('listen_fr')}"; bFr.classList.remove("active"); }}
                if (bSys) {{ bSys.innerText = "{T('listen_sys')}"; bSys.classList.remove("active"); }}
                document.querySelectorAll(".story-p, .story-title").forEach(el => el.classList.remove("highlight"));
                playMusicSafe();
            }}

            function startReading(lang) {{
                if (isReading && currentLang === lang) {{
                    stopReading();
                    return;
                }}
                if (isReading) {{
                    stopReading();
                }}

                try {{
                    if (music && !music.paused) {{
                        music.pause();
                        document.getElementById("m-state").innerText = "Valsi Başlat ▶️";
                    }}
                }} catch(e) {{}}

                isReading = true;
                currentLang = lang;
                currentIdx = 0;

                const bFr = document.getElementById("btn-listen-fr");
                const bSys = document.getElementById("btn-listen-sys");
                if (lang === 'fr' && bFr) {{ bFr.innerText = "{T('stop_btn')}"; bFr.classList.add("active"); }}
                else if (bSys) {{ bSys.innerText = "{T('stop_btn')}"; bSys.classList.add("active"); }}

                if (window.speechSynthesis) {{
                    window.speechSynthesis.cancel();
                    window.speechSynthesis.resume();
                }}

                playParagraph(0);
            }}

            function playParagraph(idx) {{
                if (!isReading || idx >= paragraphs.length) {{
                    stopReading();
                    return;
                }}
                currentIdx = idx;

                // 1. İki sütunda aynı anda paragrafı vurgula
                document.querySelectorAll(".story-p, .story-title").forEach(el => el.classList.remove("highlight"));
                const frEl = document.getElementById(`fr_p_${{idx}}`);
                const sysEl = document.getElementById(`sys_p_${{idx}}`);
                if (frEl) frEl.classList.add("highlight");
                if (sysEl) sysEl.classList.add("highlight");

                // 2. Ekranı okunan paragrafın hizasına otomatik kaydır (Auto-scroll)
                if (frEl) {{ frEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }}); }}
                if (sysEl) {{ sysEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }}); }}

                // 3. Seslendirmeyi başlat
                const textToSpeak = (currentLang === 'fr') ? paragraphs[idx].fr : paragraphs[idx].sys;
                if (!window.speechSynthesis) return;

                activeUtterance = new SpeechSynthesisUtterance(textToSpeak);
                if (currentLang === 'fr') {{
                    activeUtterance.lang = 'fr-FR';
                }} else {{
                    const tLang = '{target_lang}';
                    if (tLang === 'tr') activeUtterance.lang = 'tr-TR';
                    else if (tLang === 'en') activeUtterance.lang = 'en-US';
                    else if (tLang === 'bg') activeUtterance.lang = 'bg-BG';
                    else activeUtterance.lang = 'fr-FR';
                }}
                activeUtterance.rate = 0.95;

                activeUtterance.onend = function() {{
                    if (isReading) playParagraph(idx + 1);
                }};
                activeUtterance.onerror = function() {{
                    if (isReading) playParagraph(idx + 1);
                }};

                window.speechSynthesis.speak(activeUtterance);
            }}
        </script>
    </body>
    </html>
    """
    components.html(MITI_HTML, height=850, scrolling=False)

# ==========================================
# 5. OKUMA MODU (ZEN VIEWER)
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
                background: rgba(15, 23, 42, 0.45) !important; backdrop-filter: blur(14px) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; color: #cbd5e1 !important; border-radius: 25px !important; padding: 5px 14px !important; font-weight: 500 !important; font-size: 13px !important; transition: all 0.25s ease !important;
            }
            div[data-testid="stButton"] button:hover { background: rgba(220, 38, 38, 0.8) !important; border-color: #ef4444 !important; color: #ffffff !important; transform: scale(1.04) !important; }
        </style>
        """, unsafe_allow_html=True)

    if st.button(T("zen_close"), key="btn_exit_zen"): st.session_state.reading_mode = False; st.rerun()

    pages = ensure_reading_ready(st.session_state.uploaded_book_pages, st.session_state.app_lang)
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
            .word-hitbox {{ position: absolute; border-radius: 4px; cursor: pointer; background: rgba(255,255,255,0.01); pointer-events: auto; transition: 0.15s; }}
            .word-hitbox:hover, .word-hitbox:active {{ background: rgba(254,240,138,0.45); outline: 2px solid #facc15; }}
            .karaoke-lit {{ background: rgba(250,204,21,0.65) !important; outline: 2px solid #eab308 !important; }}
            .glass-pill {{ position: fixed; top: 10px; left: 18px; background: rgba(15,23,42,0.45); backdrop-filter: blur(14px); color: #94a3b8; font-weight: 500; font-size: 13px; padding: 5px 14px; border-radius: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.4); z-index: 1000; }}
            #whisper-card {{ position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); background: rgba(15,23,42,0.92); backdrop-filter: blur(24px); color: #ffffff; padding: 14px 22px; border-radius: 18px; box-shadow: 0 12px 40px rgba(0,0,0,0.7); display: none; z-index: 1001; max-width: 680px; width: 90vw; line-height: 1.6; }}
            .card-close-btn {{ position: absolute; top: 8px; right: 12px; background: transparent; border: none; color: #94a3b8; font-size: 16px; cursor: pointer; }}
            .glass-dock {{ position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 6px; background: rgba(15,23,42,0.5); backdrop-filter: blur(16px); padding: 6px 12px; border-radius: 35px; box-shadow: 0 8px 25px rgba(0,0,0,0.5); z-index: 1000; }}
            .glass-btn {{ background: rgba(255,255,255,0.06); color: #e2e8f0; border: 1px solid rgba(255,255,255,0.12); padding: 7px 14px; border-radius: 25px; font-weight: 500; font-size: 13.5px; cursor: pointer; }}
            .glass-btn.active {{ background: #2563eb !important; border-color: #60a5fa !important; }}
        </style>
    </head>
    <body>
        <div id="viewport-wrap"><div id="stage"><img id="book-img" src=""><div id="boxes-layer"></div></div></div>
        <div id="page-counter" class="glass-pill">{T('zen_page')} 1 / 1</div>
        <div id="whisper-card"><button class="card-close-btn" onclick="dismissCard()">✕</button><div id="whisper-body"></div></div>
        <div id="main-dock" class="glass-dock">
            <button id="btn-prev" class="glass-btn" onclick="prevPage()">⬅️</button>
            <button id="btn-speed" class="glass-btn" onclick="cycleSpeed()">⚡ <span id="speed-text">0.8x</span></button>
            <button id="btn-karaoke" class="glass-btn" onclick="toggleKaraoke()">🎤 <span id="k-text">{T('zen_listen')}</span></button>
            <button id="btn-trans" class="glass-btn" onclick="toggleTranslation()">{LANGUAGES[st.session_state.app_lang]['flag']} <span>{T('zen_page_trans')}</span></button>
            <button id="btn-next" class="glass-btn" onclick="nextPage()">➡️</button>
        </div>
        <script>
            const allPages = {json.dumps(pages)};
            const targetFlag = "{LANGUAGES[st.session_state.app_lang]['flag']}";
            let currentIndex = 0, isPlaying = false, timer = null, wordIndices = [];
            const speeds = [0.7, 0.8, 1.0]; let speedIdx = 1;

            function dismissCard() {{ document.getElementById('whisper-card').style.display = 'none'; clearTimeout(timer); }}
            function cycleSpeed() {{ speedIdx = (speedIdx + 1) % speeds.length; document.getElementById('speed-text').innerText = speeds[speedIdx] + "x"; if(isPlaying) {{ toggleKaraoke(); setTimeout(toggleKaraoke,100); }} }}

            function loadPage(idx) {{
                if (idx < 0 || idx >= allPages.length) return;
                stopKaraoke(); currentIndex = idx; const page = allPages[idx];
                document.getElementById('book-img').src = "data:image/jpeg;base64," + page.img_b64;
                document.getElementById('page-counter').innerText = `{T('zen_page')} ${{idx + 1}} / ${{allPages.length}}`;
                dismissCard(); document.getElementById('boxes-layer').innerHTML = ''; wordIndices = []; let charOffset = 0;
                
                (page.boxes || []).forEach((b, i) => {{
                    wordIndices.push({{ idx: i, start: charOffset, end: charOffset + b.text.length }});
                    charOffset += b.text.length + 1;
                    const d = document.createElement('div'); d.className = 'word-hitbox'; d.id = 'box_' + i;
                    d.style.left = b.left + '%'; d.style.top = b.top + '%'; d.style.width = b.width + '%'; d.style.height = b.height + '%';
                    
                    d.onclick = () => {{
                        clearTimeout(timer);
                        const dict = page.dictionary || {{}};
                        const cleanKey = b.clean || b.text.toLowerCase().trim();
                        let trans = dict[cleanKey] || dict[b.text] || '-';
                        document.getElementById('whisper-body').innerHTML = "<div style='text-align: center;'>🇫🇷 <b>" + b.text + "</b> &nbsp;➔&nbsp; " + targetFlag + " <b>" + trans + "</b></div>";
                        document.getElementById('whisper-card').style.display = 'block';
                        window.speechSynthesis.cancel(); 
                        const u = new SpeechSynthesisUtterance(b.text); u.lang = 'fr-FR'; u.rate = speeds[speedIdx]; window.speechSynthesis.speak(u);
                        timer = setTimeout(dismissCard, 4000);
                    }};
                    document.getElementById('boxes-layer').appendChild(d);
                }});
            }}
            function nextPage() {{ if (currentIndex < allPages.length - 1) loadPage(currentIndex + 1); }}
            function prevPage() {{ if (currentIndex > 0) loadPage(currentIndex - 1); }}

            function toggleTranslation() {{
                clearTimeout(timer);
                const tText = allPages[currentIndex].full_trans || "...";
                if (document.getElementById('whisper-card').style.display === 'block') dismissCard();
                else {{ 
                    document.getElementById('whisper-body').innerHTML = `<div style="color: #93c5fd; margin-bottom: 6px;">📝 {T('zen_page_trans')}</div><div>${{tText}}</div>`;
                    document.getElementById('whisper-card').style.display = 'block'; 
                }}
            }}

            function toggleKaraoke() {{ if (isPlaying) stopKaraoke(); else playKaraoke(); }}
            function playKaraoke() {{
                window.speechSynthesis.cancel(); isPlaying = true; document.getElementById('btn-karaoke').classList.add('active'); document.getElementById('k-text').innerText = "{T('zen_stop')}";
                const page = allPages[currentIndex]; let fSent = (page.boxes || []).map(b => b.text).join(' ');
                let u = new SpeechSynthesisUtterance(fSent); u.lang = 'fr-FR'; u.rate = speeds[speedIdx];
                u.onboundary = (e) => {{
                    if (e.name === 'word') {{
                        const match = wordIndices.find(w => e.charIndex >= w.start && e.charIndex <= w.end);
                        if (match) {{ document.querySelectorAll('.word-hitbox').forEach(el => el.classList.remove('karaoke-lit')); document.getElementById('box_' + match.idx).classList.add('karaoke-lit'); }}
                    }}
                }};
                u.onend = stopKaraoke; u.onerror = stopKaraoke; window.speechSynthesis.speak(u);
            }}
            function stopKaraoke() {{ isPlaying = false; window.speechSynthesis.cancel(); document.getElementById('btn-karaoke').classList.remove('active'); document.getElementById('k-text').innerText = "{T('zen_listen')}"; document.querySelectorAll('.word-hitbox').forEach(el => el.classList.remove('karaoke-lit')); }}
            
            window.addEventListener('keydown', (e) => {{ if (e.key === 'ArrowRight') nextPage(); if (e.key === 'ArrowLeft') prevPage(); }});
            loadPage(0);
        </script>
    </body>
    </html>
    """
    components.html(HTML_VIEWER, height=850, scrolling=False)

# ==========================================
# 6. DÜZENLEYİCİ EKRANI
# ==========================================
elif st.session_state.editor_mode:
    st.subheader(f"✏️ Kitap Düzenleyici: {st.session_state.editor_book_title}")
    col_t1, col_t2, col_t3, col_t4 = st.columns([2.5, 1.5, 1.5, 1])
    with col_t1: st.session_state.editor_book_title = st.text_input("Kitap Başlığı:", value=st.session_state.editor_book_title, label_visibility="collapsed")
    with col_t2:
        if st.button(T("save_changes"), type="secondary", use_container_width=True):
            saved_f, msg = save_hybrid_book(st.session_state.editor_book_title, st.session_state.editor_pages, st.session_state.editor_orig_book_id)
            if saved_f: st.session_state.editor_orig_book_id = saved_f; st.success(msg)
            else: st.error(msg)
    with col_t3:
        if st.button(T("save_and_read"), type="primary", use_container_width=True):
            saved_f, msg = save_hybrid_book(st.session_state.editor_book_title, st.session_state.editor_pages, st.session_state.editor_orig_book_id)
            if saved_f:
                st.session_state.uploaded_book_pages = ensure_reading_ready(st.session_state.editor_pages, st.session_state.app_lang)
                st.session_state.current_book_title = st.session_state.editor_book_title
                st.session_state.editor_mode = False; st.session_state.reading_mode = True; st.rerun()
    with col_t4:
        if st.button(T("exit_editor"), use_container_width=True): st.session_state.editor_mode = False; st.rerun()

    st.divider()
    pages = st.session_state.editor_pages
    total_p = len(pages)
    if total_p == 0: st.warning("Bu kitapta sayfa bulunmuyor.")
    else:
        if st.session_state.editor_page_idx >= total_p: st.session_state.editor_page_idx = total_p - 1
        p_idx = st.session_state.editor_page_idx
        curr_page = pages[p_idx]

        col_left, col_right = st.columns([1, 1.4])
        with col_left:
            row_sel, row_up, row_down, row_del = st.columns([2, 1, 1, 1])
            with row_sel:
                new_idx = st.selectbox("Sayfa Git:", list(range(total_p)), index=p_idx, label_visibility="collapsed")
                if new_idx != p_idx: st.session_state.editor_page_idx = new_idx; st.rerun()
            with row_del:
                if st.button("🗑️"):
                    pages.pop(p_idx); st.session_state.editor_page_idx = max(0, min(p_idx, len(pages)-1)); st.rerun()

            if st.button(T("split_page_btn"), type="primary", use_container_width=True):
                img_bytes = base64.b64decode(curr_page['img_b64'])
                orig_pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                w, h = orig_pil.size; mid_x = w // 2
                lp, rp = orig_pil.crop((0,0,mid_x,h)), orig_pil.crop((mid_x,0,w,h))
                pages[p_idx] = process_single_image(lp)
                pages.insert(p_idx + 1, process_single_image(rp))
                st.rerun()

            st.markdown(f"""<div style="text-align: center; background: #0f172a; padding: 10px;"><img src="data:image/jpeg;base64,{curr_page['img_b64']}" style="max-height: 400px;" /></div>""", unsafe_allow_html=True)

        with col_right:
            st.markdown("### 🔤 Tespit Edilen Kelimeler")
            table_data = [{"Kaldır 🗑️": False, "Metin": b["text"]} for b in curr_page["boxes"]]
            edited_table = st.data_editor(table_data, key=f"tbl_{p_idx}", use_container_width=True, height=380)
            if st.button("🔄 Değişiklikleri Uygula", type="primary"):
                curr_page["boxes"] = [b for i, b in enumerate(curr_page["boxes"]) if not edited_table[i]["Kaldır 🗑️"] and edited_table[i]["Metin"].strip()]
                for i, b in enumerate(curr_page["boxes"]): b["text"] = edited_table[i]["Metin"].strip(); b["clean"] = clean_word_key(b["text"])
                st.rerun()

# ==========================================
# 7. ANA KÜTÜPHANE EKRANI
# ==========================================
else:
    col_info1, col_thanks, col_info2, col_info3 = st.columns([2.5, 1.2, 1.8, 1])
    with col_info1: st.markdown(f"👤 `{st.session_state.user_email}`")
    with col_thanks:
        if st.button(T("thanks_btn"), use_container_width=True): record_thanks(st.session_state.user_email); st.toast(T("thanks_success"))
    with col_info2:
        new_lang = st.selectbox("Dil", options=list(LANGUAGES.keys()), format_func=lambda x: f"{LANGUAGES[x]['flag']} {LANGUAGES[x]['name']}", index=list(LANGUAGES.keys()).index(st.session_state.app_lang), label_visibility="collapsed")
        if new_lang != st.session_state.app_lang: st.session_state.app_lang = new_lang; st.rerun()
    with col_info3:
        if st.button(T("logout"), use_container_width=True): st.session_state.logged_in = False; st.rerun()

    st.markdown(f"<h2 style='text-align: center; color: #1e3a8a;'>{T('lib_title')}</h2>", unsafe_allow_html=True)
    
    saved_books, b_err = get_saved_books()
    if not saved_books: st.info(T("empty_lib"))
    else:
        book_titles = {b["book_id"]: f"{b['title']} ({b['page_count']} sayfa)" for b in saved_books}
        selected_id = st.selectbox(T("select_book"), options=list(book_titles.keys()), format_func=lambda x: book_titles[x])
        
        col_r, col_e, col_d = st.columns([2, 2, 1])
        with col_r:
            if st.button(T("open_read"), type="primary", use_container_width=True):
                with st.spinner(T("ocr_processing")):
                    book_pages, l_err = load_book_content(selected_id)
                    if book_pages:
                        st.session_state.uploaded_book_pages = book_pages
                        st.session_state.reading_mode = True; st.rerun()
        with col_e:
            if st.button(T("edit_book"), use_container_width=True) and st.session_state.user_role == "admin":
                book_pages, l_err = load_book_content(selected_id)
                if book_pages:
                    st.session_state.editor_pages = book_pages
                    st.session_state.editor_orig_book_id = selected_id
                    st.session_state.editor_book_title = next((b["title"] for b in saved_books if b["book_id"] == selected_id), "")
                    st.session_state.editor_mode = True; st.rerun()
        with col_d:
            if st.button(T("delete_book"), use_container_width=True) and st.session_state.user_role == "admin":
                delete_hybrid_book(selected_id); st.rerun()

    if st.session_state.user_role == "admin":
        with st.expander(T("add_tab")):
            st.markdown("### 📚 Yeni Kitap Oluştur & Sayfa Aktar")
            book_title_input = st.text_input("Kitabın Adı:", value="Yeni Kitap")
            split_spreads = st.checkbox("📖 Çift Sayfaları Otomatik İkiye Böl", value=True)
            upload_mode = st.radio("Yükleme Yöntemini Seçin:", ["📄 Taranmış PDF Yükle", "📸 Kameradan Çek & Kırp", "📁 Çoklu Fotoğraf"], horizontal=True)

            if upload_mode == "📄 Taranmış PDF Yükle":
                uploaded_pdf = st.file_uploader("Kitabın PDF dosyasını seçin:", type=["pdf"])
                if uploaded_pdf and st.button("⚡ PDF'i Düzenleyiciye Aktar"):
                    pdf_doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
                    extracted_pages = []
                    for p_no in range(len(pdf_doc)):
                        base_img = Image.open(io.BytesIO(pdf_doc[p_no].get_pixmap(dpi=150).tobytes("jpeg"))).convert("RGB")
                        if split_spreads and (base_img.width / base_img.height) > 1.05:
                            extracted_pages.append(process_single_image(base_img.crop((0, 0, base_img.width // 2, base_img.height))))
                            extracted_pages.append(process_single_image(base_img.crop((base_img.width // 2, 0, base_img.width, base_img.height))))
                        else: extracted_pages.append(process_single_image(base_img))
                    pdf_doc.close()
                    st.session_state.editor_pages = extracted_pages; st.session_state.editor_book_title = book_title_input
                    st.session_state.editor_mode = True; st.rerun()

            elif upload_mode == "📸 Kameradan Çek & Kırp":
                cam_pic = st.camera_input("Sayfanın Fotoğrafını Çekin")
                alt_file = st.file_uploader("veya Telefondan Tek Fotoğraf Seçin:", type=["png", "jpg"])
                active_pic = cam_pic if cam_pic else alt_file
                if active_pic:
                    raw_img = ImageOps.exif_transpose(Image.open(active_pic)).convert("RGB")
                    c_img = st_cropper(raw_img, realtime_update=True) if CROPPER_SUPPORT else raw_img
                    if st.button("✂️ Sepete Ekle"):
                        buf = io.BytesIO(); c_img.save(buf, format="JPEG"); st.session_state.staged_camera_pages.append(buf.getvalue())
                        st.success(f"Eklendi! Sepette: {len(st.session_state.staged_camera_pages)}")
                if len(st.session_state.staged_camera_pages) > 0:
                    if st.button("⚡ Sepettekileri Düzenleyiciye Aktar", type="primary"):
                        st.session_state.editor_pages = [process_single_image(Image.open(io.BytesIO(b)).convert("RGB")) for b in st.session_state.staged_camera_pages]
                        st.session_state.staged_camera_pages = []; st.session_state.editor_book_title = book_title_input; st.session_state.editor_mode = True; st.rerun()

            else:
                upl_files = st.file_uploader("Kitap sayfaları (PNG/JPG):", type=["png", "jpg"], accept_multiple_files=True)
                if upl_files and st.button("⚡ Taramayı Başlat"):
                    extracted_pages = []
                    for file in upl_files:
                        b_img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
                        if split_spreads and (b_img.width / b_img.height) > 1.05:
                            extracted_pages.append(process_single_image(b_img.crop((0, 0, b_img.width // 2, b_img.height))))
                            extracted_pages.append(process_single_image(b_img.crop((b_img.width // 2, 0, b_img.width, b_img.height))))
                        else: extracted_pages.append(process_single_image(b_img))
                    st.session_state.editor_pages = extracted_pages; st.session_state.editor_book_title = book_title_input; st.session_state.editor_mode = True; st.rerun()

    st.markdown("<br><br><hr>", unsafe_allow_html=True)
    
    # GİRİŞ EKRANINDA ORTADA ATATÜRK FOTOĞRAFI & ANMA BUTONU
    st.markdown(
        f"""
        <div style="text-align: center; color: #94a3b8; font-size: 13.5px; padding-top: 5px; margin-bottom: 15px;">
            ✍️ <b>{T('created_by')}</b>
        </div>
        """, unsafe_allow_html=True
    )
    
    t_title = translate_ui_text(T("miti_title"), st.session_state.app_lang)
    img_data_uri = get_ataturk_img_data()
    
    col_img1, col_img2, col_img3 = st.columns([1, 1, 1])
    with col_img2:
        st.markdown(
            f"""
            <div style="text-align: center; margin-bottom: 15px;">
                <img src="{img_data_uri}" 
                     style="width: 170px; height: 170px; object-fit: cover; border-radius: 50%; border: 3px solid #cbd5e1; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
            </div>
            """, unsafe_allow_html=True
        )
        if st.button(f"✨ {t_title}", use_container_width=True):
            st.session_state.miti_mode = True
            st.rerun()
