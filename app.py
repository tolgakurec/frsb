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
import urllib.error
import concurrent.futures
from datetime import datetime
from PIL import Image, ImageOps
import numpy as np
import easyocr
import streamlit as st
import streamlit.components.v1 as components

# PyTorch Bellek Tasarrufu
try:
    import torch
    torch.set_grad_enabled(False)
except Exception:
    pass

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
        "select_book": "Okumak istediğiniz kitabı seçin (En yeni yüklenenler en üstte):",
        "open_read": "🚀 Kitabı Aç ve Oku",
        "edit_book": "✏️ Kitabı Düzenle",
        "delete_book": "🗑️ Sil",
        "delete_confirm": "Kitap silindi.",
        "save_changes": "💾 Değişiklikleri Kaydet (Veritabanına Ekle)",
        "save_and_read": "🚀 Kaydet & Hemen Oku",
        "exit_editor": "✕ Çık",
        "split_page_btn": "✂️ Bu Çift Sayfayı İkiye Böl",
        "merge_page_btn": "🔗 Sonraki Sayfa ile Birleştir (Sol + Sağ)",
        "rescan_page_btn": "🔄 Bu Sayfayı Tekrar Tara",
        "ocr_processing": "Kitap hazırlanıyor...",
        "reading_lang_label": "Okuma & Çeviri Dili:",
        "zen_close": "✕ Kapat",
        "zen_page": "Sayfa",
        "zen_listen": "Sesli Dinle",
        "zen_stop": "Durdur",
        "zen_page_trans": "Sayfa Çevirisi",
        "zen_loading_trans": "Sayfa çevirisi hazırlanıyor...",
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
        "select_book": "Select a book to read (Newest uploads first):",
        "open_read": "🚀 Open & Read",
        "edit_book": "✏️ Edit Book",
        "delete_book": "🗑️ Delete",
        "delete_confirm": "Book deleted successfully.",
        "save_changes": "💾 Save Changes",
        "save_and_read": "🚀 Save & Read Now",
        "exit_editor": "✕ Exit",
        "split_page_btn": "✂️ Split Double Page",
        "merge_page_btn": "🔗 Merge with Next Page (Left + Right)",
        "rescan_page_btn": "🔄 Re-scan Page",
        "ocr_processing": "Preparing book...",
        "reading_lang_label": "Translation Language:",
        "zen_close": "✕ Close",
        "zen_page": "Page",
        "zen_listen": "Listen Aloud",
        "zen_stop": "Stop",
        "zen_page_trans": "Page Translation",
        "zen_loading_trans": "Preparing translation...",
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
        "select_book": "Изберете книга за четене (Най-новите най-отгоре):",
        "open_read": "🚀 Отвори и чети",
        "edit_book": "✏️ Редактирай",
        "delete_book": "🗑️ Изтрий",
        "delete_confirm": "Книгата бе изтрита успешно.",
        "save_changes": "💾 Запази промените",
        "save_and_read": "🚀 Запази и чети веднага",
        "exit_editor": "✕ Изход",
        "split_page_btn": "✂️ Раздели двойната страница",
        "merge_page_btn": "🔗 Обедини със следващата страница",
        "rescan_page_btn": "🔄 Сканирай отново",
        "ocr_processing": "Подготовка на книгата...",
        "reading_lang_label": "Език за превод:",
        "zen_close": "✕ Затвори",
        "zen_page": "Страница",
        "zen_listen": "Слушай",
        "zen_stop": "Спри",
        "zen_page_trans": "Превод на страницата",
        "zen_loading_trans": "Подготвя се превод...",
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
if "manual_gemini_key" not in st.session_state: st.session_state.manual_gemini_key = ""

def T(key):
    lang = st.session_state.app_lang if st.session_state.app_lang in UI_TRANSLATIONS else "tr"
    return UI_TRANSLATIONS[lang].get(key, UI_TRANSLATIONS["tr"].get(key, key))

# ==========================================
# 1. ÇEVİRİ MOTORU VE YARDIMCI FONKSİYONLAR
# ==========================================
@st.cache_data(show_spinner=False)
def translate_api(text, source_lang, target_lang):
    if not text or not text.strip() or source_lang == target_lang:
        return text
    clients = ['gtx', 'dict-chrome-ex', 'te_lib']
    base_url = "ht" + "tps://translate.googleapis" + ".com/translate_a/single"
    for client in clients:
        try:
            url = f"{base_url}?client={client}&sl={source_lang}&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            res = urllib.request.urlopen(req, timeout=4)
            data = json.loads(res.read().decode('utf-8'))
            translated_parts = []
            if data and data[0]:
                for s in data[0]:
                    if s and s[0]:
                        translated_parts.append(s[0])
            res_str = "".join(translated_parts).strip()
            if res_str:
                return res_str
        except Exception:
            continue
    return text

@st.cache_data(show_spinner=False)
def translate_french_to_target(text, target_lang):
    if not text or not text.strip(): return ""
    if target_lang == "fr": return text
    return translate_api(text, source_lang="fr", target_lang=target_lang)

@st.cache_data(show_spinner=False)
def translate_turkish_to_target(text, target_lang):
    if not text or not text.strip(): return ""
    if target_lang == "tr": return text
    return translate_api(text, source_lang="tr", target_lang=target_lang)

def get_file_base64(filename, mime_type):
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
    if img_b64: return img_b64
    return "ht" + "tps://upload.wikimedia" + ".org/wikipedia/commons/thumb/c/c5/Mustafa_Kemal_Atat%C3%BCrk_in_janissary_costume.jpg/440px-Mustafa_Kemal_Atat%C3%BCrk_in_janissary_costume.jpg"

def get_blue_danube_audio_data():
    audio_b64 = get_file_base64("blue_danube.mp3", "audio/mp3")
    if audio_b64: return audio_b64
    return "ht" + "tps://ia800501.us.archive" + ".org/33/items/TheBlueDanubeWaltz/TheBlueDanubeWaltz.mp3"

# ==========================================
# 2. GOOGLE SHEETS ENTEGRASYONU (YÜKLEME TARİHİ SIRALI)
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

def get_gsheet_client():
    if not GSHEETS_INSTALLED: return None, "gspread veya oauth2client eksik.", ""
    creds_dict = get_service_account_dict()
    if not creds_dict: return None, "Google kimlik anahtarı bulunamadı!", ""
    sa_email = creds_dict.get("client_email", "Bilinmeyen Servis Hesabı")
    try:
        scope = [
            "ht" + "tps://spreadsheets.google" + ".com/feeds",
            "ht" + "tps://www.googleapis" + ".com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client, None, sa_email
    except Exception as e: return None, f"Yetkilendirme Hatası: {str(e)}", sa_email

def get_sheet(sheet_name):
    client, err, sa_email = get_gsheet_client()
    if not client: return None, err
    try: doc = client.open_by_key("1Ec0v2Oo-7BlILvb35TGgo5j-SOGivJwmf5xpF85oGoU")
    except Exception as e: return None, f"Tablo açılamadı! ({str(e)})"
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

def format_short_date(date_str):
    if not date_str:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(date_str).strip())
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return str(date_str).strip()[:10]

def get_saved_books():
    sheet, err = get_sheet("Library")
    if not sheet: return [], err
    for attempt in range(2):
        try:
            records = sheet.get_all_records()
            books_list, seen_ids = [], set()
            for idx, r in enumerate(records):
                b_id = str(r.get("BookID", "")).strip()
                if not b_id or b_id in seen_ids: continue
                seen_ids.add(b_id)
                
                # Yükleme tarihi sütununu otomatik tespit et
                date_val = ""
                for k, v in r.items():
                    k_low = str(k).lower()
                    if any(w in k_low for w in ["date", "tarih", "time", "created", "eklenme", "yukleme"]):
                        date_val = str(v).strip()
                        break
                if not date_val:
                    vals = list(r.values())
                    if len(vals) >= 3 and re.match(r"^\d{4}-\d{2}-\d{2}", str(vals[2]).strip()):
                        date_val = str(vals[2]).strip()
                        
                books_list.append({
                    "book_id": b_id,
                    "title": r.get("BookName", "İsimsiz"),
                    "page_count": r.get("PageCount", 0),
                    "date": date_val,
                    "row_idx": idx
                })
            # Son yüklenen kitaplar en üstte olacak şekilde tarihe ve satır sırasına göre ters sırala
            books_list.sort(key=lambda x: (x["date"], x["row_idx"]), reverse=True)
            return books_list, None
        except Exception as e:
            if attempt == 0:
                time.sleep(0.5)
                continue
            return [], str(e)
    return [], "Bilinmeyen hata"

def load_book_content(book_id):
    sheet, err = get_sheet("Pages")
    if not sheet: return None, err
    try:
        records = sheet.get_all_records()
        pages = []
        for r in records:
            if str(r.get("BookID", "")).strip() == str(book_id).strip():
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
                if str(r.get("BookID", "")).strip() == str(book_id).strip(): lib_sheet.delete_rows(i + 2); break
            page_records = pages_sheet.get_all_records()
            rows_to_del = [i + 2 for i, r in enumerate(page_records) if str(r.get("BookID", "")).strip() == str(book_id).strip()]
            for row_idx in reversed(rows_to_del): pages_sheet.delete_rows(row_idx); time.sleep(0.1)
        else: book_id = str(uuid.uuid4())[:8]
        
        lib_sheet.append_row([book_id, title, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(pages)])
        all_page_rows = [[book_id, idx + 1, page["img_b64"], json.dumps(page["boxes"], ensure_ascii=False)] for idx, page in enumerate(pages)]
        for i in range(0, len(all_page_rows), 10): pages_sheet.append_rows(all_page_rows[i:i + 10]); time.sleep(0.5)
        return book_id, "Kitap başarıyla kaydedildi!"
    except Exception as e: return None, str(e)

def delete_hybrid_book(book_id):
    lib_sheet, _ = get_sheet("Library")
    pages_sheet, _ = get_sheet("Pages")
    if lib_sheet:
        for i, r in enumerate(lib_sheet.get_all_records()):
            if str(r.get("BookID", "")).strip() == str(book_id).strip(): lib_sheet.delete_rows(i + 2); break
    if pages_sheet:
        rows_to_delete = [i + 2 for i, r in enumerate(pages_sheet.get_all_records()) if str(r.get("BookID", "")) == book_id]
        for row_idx in reversed(rows_to_delete): pages_sheet.delete_rows(row_idx); time.sleep(0.1)

# ==========================================
# 3. ZIRHLI GEMINI VISION API MOTORU
# ==========================================
def sanitize_gemini_key(raw_key):
    if not raw_key: return ""
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "", str(raw_key)).strip()

def get_active_gemini_key():
    k = st.session_state.get("manual_gemini_key", "").strip()
    if k: return sanitize_gemini_key(k)
    if hasattr(st, "secrets"):
        for name in ["GEMINI_API_KEY", "gemini_api_key", "GEMINI_KEY"]:
            if name in st.secrets:
                val = sanitize_gemini_key(st.secrets[name])
                if val: return val
    return None

def get_gemini_endpoint(model_name="gemini-2.5-flash"):
    proto = "ht" + "tps" + "://"
    domain = "generativelanguage" + "." + "googleapis" + "." + "com"
    return f"{proto}{domain}/v1beta/models/{model_name}:generateContent"

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['fr', 'en'], gpu=False)

def call_gemini_vision_native(base64_image, api_key):
    clean_key = sanitize_gemini_key(api_key)
    if not clean_key:
        return None, "API Key boş veya geçersiz."
        
    prompt = (
        "You are an expert OCR engine for French children's picture books. "
        "Transcribe all visible French text with 100% precision, especially cursive handwriting (écriture cursive). "
        "Return STRICTLY a JSON array where each object has:\n"
        "- 'text': The exact transcribed French text (preserve accents, punctuation, apostrophes).\n"
        "- 'left': Float percentage (0-100) from image left edge.\n"
        "- 'top': Float percentage (0-100) from image top edge.\n"
        "- 'width': Float percentage (0-100) width of text.\n"
        "- 'height': Float percentage (0-100) height of text.\n"
        "Output ONLY raw JSON array, without any markdown formatting, backticks, or explanation."
    )
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64_image
                    }
                }
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    last_error = "Bilinmeyen API hatası"

    for model_name in candidate_models:
        url = get_gemini_endpoint(model_name)
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": clean_key,
                "User-Agent": "Mozilla/5.0"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                resp_body = resp.read().decode("utf-8")
                data = json.loads(resp_body)
                candidates = data.get("candidates", [])
                if not candidates:
                    last_error = "Gemini boş cevap döndürdü."
                    continue
                    
                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "[]").strip()
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text)
                    raw_text = re.sub(r"\n?```$", "", raw_text).strip()
                    
                parsed = json.loads(raw_text)
                items = []
                if isinstance(parsed, list):
                    items = parsed
                elif isinstance(parsed, dict):
                    for k in ["items", "boxes", "text_elements", "lines", "data"]:
                        if k in parsed and isinstance(parsed[k], list):
                            items = parsed[k]; break
                    if not items:
                        for v in parsed.values():
                            if isinstance(v, list): items = v; break
                            
                clean_boxes = []
                for i, b in enumerate(items):
                    t = str(b.get("text", "")).strip()
                    if not t: continue
                    clean_boxes.append({
                        "id": f"b_{i}",
                        "text": t,
                        "clean": clean_word_key(t),
                        "left": float(b.get("left", 5)),
                        "top": float(b.get("top", 5)),
                        "width": float(b.get("width", 30)),
                        "height": float(b.get("height", 8))
                    })
                    
                if clean_boxes:
                    return clean_boxes, None
                last_error = "Görselde okunabilir metin bulunamadı."
                
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode("utf-8", errors="ignore")
            last_error = f"{model_name} HTTP {he.code}: {err_msg[:160]}"
            continue
        except Exception as e:
            last_error = f"{model_name} Bağlantı Hatası: {str(e)}"
            continue

    return None, last_error

def process_single_image(img):
    img_fixed = ImageOps.exif_transpose(img).convert("RGB")
    
    img_c = img_fixed.copy()
    img_c.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img_c.save(buf, format="JPEG", quality=80)
    b64_gemini = base64.b64encode(buf.getvalue()).decode("utf-8")
    del img_c, buf
    
    gemini_key = get_active_gemini_key()
    boxes = None
    engine_name = "EasyOCR"
    error_msg = None
    
    if gemini_key:
        boxes, error_msg = call_gemini_vision_native(b64_gemini, gemini_key)
        if boxes:
            engine_name = "Gemini Vision"
            
    if not boxes:
        reader = load_ocr()
        img_ocr = img_fixed.copy()
        img_ocr.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        try: img_ocr = ImageOps.autocontrast(img_ocr, cutoff=0.5)
        except: pass
            
        w, h = img_ocr.size
        np_arr = np.array(img_ocr)
        
        ocr_raw = reader.readtext(
            np_arr, detail=1, paragraph=False,
            mag_ratio=1.0, contrast_ths=0.1, adjust_contrast=0.5, text_threshold=0.5, low_text=0.3
        )
        ordered_ocr = sort_reading_order(ocr_raw)
        
        boxes = []
        for box, text, conf in ordered_ocr:
            t_clean = text.strip()
            if not t_clean: continue
            x_pts, y_pts = [p[0] for p in box], [p[1] for p in box]
            min_x, max_x = min(x_pts), max(x_pts)
            min_y, max_y = min(y_pts), max(y_pts)
            boxes.append({
                "id": f"b_{len(boxes)}", "text": t_clean, "clean": clean_word_key(t_clean),
                "left": (min_x / w) * 100, "top": (min_y / h) * 100,
                "width": ((max_x - min_x) / w) * 100, "height": ((max_y - min_y) / h) * 100
            })
        del img_ocr, np_arr

    img_s = img_fixed.copy()
    img_s.thumbnail((650, 850), Image.Resampling.LANCZOS)
    buf_s = io.BytesIO()
    quality = 45
    img_s.save(buf_s, format="JPEG", quality=quality)
    while len(buf_s.getvalue()) > 35000 and quality > 10:
        quality -= 5
        buf_s = io.BytesIO()
        img_s.save(buf_s, format="JPEG", quality=quality)
    final_b64 = base64.b64encode(buf_s.getvalue()).decode("utf-8")
    
    del img_s, buf_s, img_fixed
    gc.collect()
    
    return {"img_b64": final_b64, "boxes": boxes}, engine_name, error_msg

def sort_reading_order(ocr_items):
    if not ocr_items: return []
    parsed = []
    for item in ocr_items:
        box, text, conf = item
        t_clean = text.strip()
        if not t_clean: continue
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        parsed.append({
            'item': item, 'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y,
            'cy': (min_y + max_y) / 2.0, 'h': max(max_y - min_y, 1.0)
        })
    if not parsed: return []
    parsed.sort(key=lambda p: (p['min_y'], p['min_x']))
    
    lines = []
    for p in parsed:
        matched_line = None
        for line in lines:
            overlaps = []
            for other in line:
                ov = max(0, min(p['max_y'], other['max_y']) - max(p['min_y'], other['min_y']))
                min_h = min(p['h'], other['h'])
                overlaps.append(ov / min_h)
            if (sum(overlaps) / len(overlaps)) > 0.40:
                matched_line = line; break
        if matched_line is not None: matched_line.append(p)
        else: lines.append([p])
            
    lines.sort(key=lambda line: min(k['min_y'] for k in line))
    sorted_items = []
    for line in lines:
        line.sort(key=lambda p: p['min_x'])
        for p in line: sorted_items.append(p['item'])
    return sorted_items

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
def get_words_dictionary(texts_list, target_lang):
    if target_lang == "fr": return {}
    trans_map, unique_items = {}, set()
    for raw in texts_list:
        clean = clean_word_key(raw)
        if clean: unique_items.add(clean)
        for word in re.findall(r"[\wÀ-ÿ'-]+", raw):
            w_clean = clean_word_key(word)
            if len(w_clean) > 1: unique_items.add(w_clean)
            
    if not unique_items: return {}
    items_list = sorted(list(unique_items))
    batch_size = 25
    for i in range(0, len(items_list), batch_size):
        batch = items_list[i:i + batch_size]
        combined = "\n".join(batch)
        t_combined = translate_french_to_target(combined, target_lang)
        lines = [line.strip() for line in t_combined.split("\n") if line.strip()]
        if len(lines) == len(batch):
            for orig, trans in zip(batch, lines): trans_map[orig] = trans
        else:
            for orig in batch: trans_map[orig] = translate_french_to_target(orig, target_lang)
    return trans_map

def _translate_single_page_task(page, target_lang):
    is_corrupted = (
        target_lang != "fr" and
        page.get("full_trans") == page.get("full_text") and
        len(page.get("full_text", "")) > 5
    )
    if page.get("current_lang") != target_lang or "full_trans" not in page or "dictionary" not in page or is_corrupted:
        raw_texts = [b.get("text", "").strip() for b in page.get("boxes", []) if b.get("text", "").strip()]
        for b in page.get("boxes", []): b["clean"] = clean_word_key(b.get("text", ""))
        full_str = build_coherent_page_text(page.get("boxes", []))
        page["full_text"] = full_str
        
        if target_lang == "fr":
            page["full_trans"] = full_str
            page["dictionary"] = {}
        else:
            page["full_trans"] = translate_french_to_target(full_str, target_lang)
            page["dictionary"] = get_words_dictionary(raw_texts, target_lang)
        page["current_lang"] = target_lang
    return page

def ensure_reading_ready(pages, target_lang):
    if not pages: return pages
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_translate_single_page_task, page, target_lang) for page in pages]
        concurrent.futures.wait(futures)
    return pages

def merge_two_pages(page1, page2):
    b1 = base64.b64decode(page1['img_b64'])
    b2 = base64.b64decode(page2['img_b64'])
    im1 = Image.open(io.BytesIO(b1)).convert("RGB")
    im2 = Image.open(io.BytesIO(b2)).convert("RGB")
    
    target_h = max(im1.height, im2.height)
    if im1.height != target_h:
        im1 = im1.resize((int(im1.width * (target_h / im1.height)), target_h), Image.Resampling.LANCZOS)
    if im2.height != target_h:
        im2 = im2.resize((int(im2.width * (target_h / im2.height)), target_h), Image.Resampling.LANCZOS)
        
    merged_w = im1.width + im2.width
    merged_img = Image.new('RGB', (merged_w, target_h), (255, 255, 255))
    merged_img.paste(im1, (0, 0))
    merged_img.paste(im2, (im1.width, 0))
    
    new_page_obj, _, _ = process_single_image(merged_img)
    del im1, im2, merged_img
    gc.collect()
    return new_page_obj

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
# 4.1. MİTİ & ATATÜRK ANMA SAYFASI
# ==========================================
elif st.session_state.miti_mode:
    target_lang = st.session_state.app_lang
    img_data_uri = get_ataturk_img_data()
    audio_data_uri = get_blue_danube_audio_data()
    
    if target_lang == "tr":
        prepared_pairs = [{"fr": p["fr"], "sys": p["tr"]} for p in STORY_PARAGRAPHS]
    elif target_lang == "fr":
        prepared_pairs = [{"fr": p["fr"], "sys": p["fr"]} for p in STORY_PARAGRAPHS]
    else:
        combined_tr = "\n=====\n".join([p["tr"] for p in STORY_PARAGRAPHS])
        trans_all = translate_turkish_to_target(combined_tr, target_lang)
        parts = [pt.strip() for pt in trans_all.split("=====")]
        if len(parts) == len(STORY_PARAGRAPHS):
            prepared_pairs = [{"fr": p["fr"], "sys": parts[i]} for i, p in enumerate(STORY_PARAGRAPHS)]
        else:
            prepared_pairs = [{"fr": p["fr"], "sys": translate_turkish_to_target(p["tr"], target_lang)} for p in STORY_PARAGRAPHS]

    story_json = json.dumps(prepared_pairs, ensure_ascii=False)

    st.markdown(
        """
        <style>
            [data-testid="stSidebar"], header, footer { display: none !important; }
            .block-container { padding: 0 !important; margin: 0 !important; max-width: 100vw !important; height: 100vh !important; overflow: hidden !important; background: #080c14 !important; }
            iframe { position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; border: none !important; z-index: 1 !important; }
            div[data-testid="stButton"], .stButton { position: fixed !important; top: 14px !important; left: 50% !important; transform: translateX(-50%) !important; z-index: 99999999 !important; }
            div[data-testid="stButton"] button, .stButton button { background: #dc2626 !important; border: 2px solid #fca5a5 !important; color: #ffffff !important; border-radius: 30px !important; padding: 8px 32px !important; font-weight: 800 !important; font-size: 15px !important; cursor: pointer !important; box-shadow: 0 4px 25px rgba(220, 38, 38, 0.6) !important; transition: all 0.2s ease !important; }
            div[data-testid="stButton"] button:hover { background: #b91c1c !important; transform: scale(1.08) !important; }
        </style>
        """, unsafe_allow_html=True)

    if st.button(T("miti_exit"), key="btn_top_exit"):
        st.session_state.miti_mode = False
        st.rerun()

    MITI_HTML = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            * {{ box-sizing: border-box; }}
            body {{ margin: 0; padding: 0; overflow: hidden; background-color: #080c14; color: #e2e8f0; font-family: 'Georgia', serif; height: 100vh; display: flex; }}
            #col-photo {{ width: 28%; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 65px 20px 20px 25px; background: #04060a; border-right: 1.5px dashed rgba(255,255,255,0.15); position: relative; }}
            #col-photo img {{ max-width: 100%; max-height: 82vh; object-fit: contain; border-radius: 12px; box-shadow: 0 15px 45px rgba(0,0,0,0.85); border: 1px solid rgba(255,255,255,0.12); }}
            #cols-wrap {{ width: 72%; height: 100vh; display: flex; }}
            #col-french, #col-system {{ width: 50%; height: 100vh; padding: 75px 25px 40px 25px; overflow-y: auto; scroll-behavior: smooth; position: relative; }}
            #col-french {{ border-right: 1.5px dashed rgba(255,255,255,0.15); }}
            @media (max-width: 768px) {{
                body {{ flex-direction: column !important; }}
                #col-photo {{ width: 100% !important; height: 26vh !important; padding: 60px 10px 10px 10px !important; border-right: none !important; border-bottom: 1.5px dashed rgba(255,255,255,0.15) !important; }}
                #col-photo img {{ max-height: 18vh !important; }}
                #cols-wrap {{ width: 100% !important; height: 74vh !important; }}
                #col-french, #col-system {{ padding: 15px 12px 30px 12px !important; font-size: 0.95rem !important; }}
            }}
            .col-header {{ position: sticky; top: -75px; background: rgba(8, 12, 20, 0.95); backdrop-filter: blur(12px); padding: 10px 0 16px 0; z-index: 10; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 20px; }}
            .listen-btn {{ display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; background: rgba(251, 191, 36, 0.15); color: #fbbf24; border: 1.5px solid #fbbf24; padding: 11px 18px; border-radius: 25px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 14.5px; font-weight: bold; cursor: pointer; transition: all 0.25s ease; }}
            .listen-btn:hover {{ background: #fbbf24; color: #000; transform: translateY(-1px); }}
            .listen-btn.active {{ background: #ef4444 !important; border-color: #ef4444 !important; color: #fff !important; }}
            .story-p {{ font-size: 1.05rem; line-height: 1.85; margin-bottom: 18px; color: #cbd5e1; padding: 10px 14px; border-radius: 6px; transition: all 0.3s ease; text-align: justify; }}
            .story-title {{ font-size: 1.35rem; font-weight: bold; color: #fbbf24; margin-bottom: 20px; line-height: 1.4; text-align: left; padding: 8px 12px; }}
            .highlight {{ background-color: rgba(250, 204, 21, 0.28) !important; color: #ffffff !important; border-left: 5px solid #facc15 !important; padding-left: 16px !important; box-shadow: 0 0 20px rgba(250, 204, 21, 0.2) !important; border-radius: 4px !important; }}
            ::-webkit-scrollbar {{ width: 5px; }}
            ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.2); border-radius: 4px; }}
            #music-toggle {{ position: fixed; bottom: 15px; left: 15px; z-index: 1000; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255,255,255,0.2); color: #fbbf24; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-family: sans-serif; cursor: pointer; display: flex; align-items: center; gap: 8px; backdrop-filter: blur(8px); }}
        </style>
    </head>
    <body>
        <audio id="bgMusic" src="{audio_data_uri}" loop preload="auto"></audio>
        <button id="music-toggle" onclick="toggleMusic(event)">🎵 <span id="m-state">Vals Çalıyor</span></button>
        <div id="col-photo"><img src="{img_data_uri}" alt="Atatürk ve Miti"></div>
        <div id="cols-wrap">
            <div id="col-french">
                <div class="col-header"><button class="listen-btn" id="btn-listen-fr" onclick="startReading('fr')">{T('listen_fr')}</button></div>
                <div id="french-content"></div>
            </div>
            <div id="col-system">
                <div class="col-header"><button class="listen-btn" id="btn-listen-sys" onclick="startReading('sys')">{T('listen_sys')}</button></div>
                <div id="system-content"></div>
            </div>
        </div>
        <script>
            const paragraphs = {story_json};
            const frContent = document.getElementById("french-content");
            const sysContent = document.getElementById("system-content");
            const music = document.getElementById("bgMusic");
            music.volume = 0.35;
            let frHtml = "", sysHtml = "";
            paragraphs.forEach((p, idx) => {{
                let cls = (idx === 0 || idx === 2 || idx === 5 || idx === 8 || idx === 12) ? "story-title" : "story-p";
                frHtml += `<div class="${{cls}}" id="fr_p_${{idx}}">${{p.fr}}</div>`;
                sysHtml += `<div class="${{cls}}" id="sys_p_${{idx}}">${{p.sys}}</div>`;
            }});
            frContent.innerHTML = frHtml;
            sysContent.innerHTML = sysHtml;

            function playMusicSafe() {{
                if (!music) return;
                const p = music.play();
                if (p !== undefined) {{ p.then(() => {{ document.getElementById("m-state").innerText = "Vals Çalıyor 🎵"; }}).catch(() => {{ document.getElementById("m-state").innerText = "Valsi Başlat ▶️"; }}); }}
            }}
            window.addEventListener("DOMContentLoaded", playMusicSafe);
            setTimeout(playMusicSafe, 400);
            window.addEventListener("touchstart", () => {{ if (music.paused && !isReading) playMusicSafe(); }}, {{ once: true }});
            window.addEventListener("click", () => {{ if (music.paused && !isReading) playMusicSafe(); }}, {{ once: true }});
            function toggleMusic(e) {{ e.stopPropagation(); if (music.paused) {{ playMusicSafe(); }} else {{ music.pause(); document.getElementById("m-state").innerText = "Valsi Başlat ▶️"; }} }}

            let isReading = false, currentLang = "", currentIdx = 0, activeUtterance = null;
            function stopReading() {{
                isReading = false; currentLang = "";
                if (window.speechSynthesis) {{ window.speechSynthesis.cancel(); }}
                const bFr = document.getElementById("btn-listen-fr"); const bSys = document.getElementById("btn-listen-sys");
                if (bFr) {{ bFr.innerText = "{T('listen_fr')}"; bFr.classList.remove("active"); }}
                if (bSys) {{ bSys.innerText = "{T('listen_sys')}"; bSys.classList.remove("active"); }}
                document.querySelectorAll(".story-p, .story-title").forEach(el => el.classList.remove("highlight"));
                playMusicSafe();
            }}
            function startReading(lang) {{
                if (isReading && currentLang === lang) {{ stopReading(); return; }}
                if (isReading) {{ stopReading(); }}
                try {{ if (music && !music.paused) {{ music.pause(); document.getElementById("m-state").innerText = "Valsi Başlat ▶️"; }} }} catch(e) {{}}
                isReading = true; currentLang = lang; currentIdx = 0;
                const bFr = document.getElementById("btn-listen-fr"); const bSys = document.getElementById("btn-listen-sys");
                if (lang === 'fr' && bFr) {{ bFr.innerText = "{T('stop_btn')}"; bFr.classList.add("active"); }}
                else if (bSys) {{ bSys.innerText = "{T('stop_btn')}"; bSys.classList.add("active"); }}
                if (window.speechSynthesis) {{ window.speechSynthesis.cancel(); window.speechSynthesis.resume(); }}
                playParagraph(0);
            }}
            function playParagraph(idx) {{
                if (!isReading || idx >= paragraphs.length) {{ stopReading(); return; }}
                currentIdx = idx;
                document.querySelectorAll(".story-p, .story-title").forEach(el => el.classList.remove("highlight"));
                const frEl = document.getElementById(`fr_p_${{idx}}`); const sysEl = document.getElementById(`sys_p_${{idx}}`);
                if (frEl) frEl.classList.add("highlight"); if (sysEl) sysEl.classList.add("highlight");
                if (frEl) {{ frEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }}); }}
                if (sysEl) {{ sysEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }}); }}
                const textToSpeak = (currentLang === 'fr') ? paragraphs[idx].fr : paragraphs[idx].sys;
                if (!window.speechSynthesis) return;
                activeUtterance = new SpeechSynthesisUtterance(textToSpeak);
                if (currentLang === 'fr') {{ activeUtterance.lang = 'fr-FR'; }} else {{
                    const tLang = '{target_lang}';
                    if (tLang === 'tr') activeUtterance.lang = 'tr-TR'; else if (tLang === 'en') activeUtterance.lang = 'en-US'; else if (tLang === 'bg') activeUtterance.lang = 'bg-BG'; else activeUtterance.lang = 'fr-FR';
                }}
                activeUtterance.rate = 0.95;
                activeUtterance.onend = function() {{ if (isReading) playParagraph(idx + 1); }};
                activeUtterance.onerror = function() {{ if (isReading) playParagraph(idx + 1); }};
                window.speechSynthesis.speak(activeUtterance);
            }}
        </script>
    </body>
    </html>
    """
    components.html(MITI_HTML, height=850, scrolling=False)

# ==========================================
# 5. OKUMA MODU (ZEN VIEWER - KİTAP OKUYUCU)
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

    if st.button(T("zen_close"), key="btn_exit_zen"):
        st.session_state.reading_mode = False
        st.rerun()

    pages = ensure_reading_ready(st.session_state.uploaded_book_pages, st.session_state.app_lang)
    target_flag = LANGUAGES[st.session_state.app_lang]["flag"]
    txt_page = T("zen_page")
    txt_listen = T("zen_listen")
    txt_stop = T("zen_stop")
    txt_trans = T("zen_page_trans")
    txt_loading = T("zen_loading_trans")
    pages_json = json.dumps(pages)

    HTML_VIEWER = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            * {{ box-sizing: border-box; user-select: none; -webkit-user-select: none; }}
            html, body {{ margin: 0; padding: 0; width: 100vw; height: 100vh; overflow: hidden; background: #06090e; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
            #viewport-wrap {{ position: relative; width: 100vw; height: calc(100vh - 90px); margin-top: 35px; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
            #stage {{ position: relative; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 35px rgba(0,0,0,0.85); border-radius: 6px; background: #000; }}
            #book-img {{ width: 100%; height: 100%; display: block; border-radius: 6px; }}
            #boxes-layer {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }}
            .word-hitbox {{ position: absolute; border-radius: 4px; cursor: pointer; background: rgba(255,255,255,0.01); pointer-events: auto; transition: background 0.15s ease, outline 0.15s ease; }}
            .word-hitbox:hover, .word-hitbox:active {{ background: rgba(254,240,138,0.45); outline: 2px solid #facc15; }}
            .karaoke-lit {{ background: rgba(250,204,21,0.65) !important; outline: 2px solid #eab308 !important; }}
            .glass-pill {{ position: fixed; top: 10px; left: 18px; background: rgba(15,23,42,0.45); backdrop-filter: blur(14px); color: #94a3b8; font-weight: 500; font-size: 13px; padding: 5px 14px; border-radius: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.4); z-index: 1000; }}
            #whisper-card {{ position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); background: rgba(15,23,42,0.92); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); color: #ffffff; padding: 14px 22px; border-radius: 18px; font-size: 15px; box-shadow: 0 12px 40px rgba(0,0,0,0.7); border: 1px solid rgba(255,255,255,0.18); display: none; z-index: 1001; max-width: 680px; width: 90vw; line-height: 1.6; }}
            .card-close-btn {{ position: absolute; top: 8px; right: 12px; background: transparent; border: none; color: #94a3b8; font-size: 16px; cursor: pointer; }}
            .glass-dock {{ position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 6px; background: rgba(15,23,42,0.5); backdrop-filter: blur(16px); padding: 6px 12px; border-radius: 35px; box-shadow: 0 8px 25px rgba(0,0,0,0.5); z-index: 1000; }}
            .glass-btn {{ background: rgba(255,255,255,0.06); color: #e2e8f0; border: 1px solid rgba(255,255,255,0.12); padding: 7px 14px; border-radius: 25px; font-weight: 500; font-size: 13.5px; cursor: pointer; }}
            .glass-btn.active {{ background: #2563eb !important; border-color: #60a5fa !important; }}
        </style>
    </head>
    <body onmousemove="resetHudTimer()" onclick="resetHudTimer()" ontouchstart="resetHudTimer()">
        <div id="viewport-wrap"><div id="stage"><img id="book-img" src=""><div id="boxes-layer"></div></div></div>
        <div id="page-counter" class="glass-pill hud-item">{txt_page} 1 / 1</div>
        <div id="whisper-card"><button class="card-close-btn" onclick="dismissCard()">✕</button><div id="whisper-body"></div></div>
        <div id="main-dock" class="glass-dock hud-item">
            <button id="btn-prev" class="glass-btn" onclick="prevPage()">⬅️</button>
            <button id="btn-speed" class="glass-btn" onclick="cycleSpeed()">⚡ <span id="speed-text">0.8x</span></button>
            <button id="btn-karaoke" class="glass-btn" onclick="toggleKaraoke()">🎤 <span id="k-text">{txt_listen}</span></button>
            <button id="btn-trans" class="glass-btn" onclick="toggleTranslation()">{target_flag} <span>{txt_trans}</span></button>
            <button id="btn-next" class="glass-btn" onclick="nextPage()">➡️</button>
        </div>
        <script>
            const allPages = {pages_json};
            const targetFlag = "{target_flag}";
            let currentIndex = 0, isPlaying = false, timer = null, wordIndices = [];
            const speeds = [0.7, 0.8, 1.0]; let speedIdx = 1;

            const imgEl = document.getElementById('book-img');
            const stage = document.getElementById('stage');
            const layer = document.getElementById('boxes-layer');
            const wrap = document.getElementById('viewport-wrap');

            function fitPageToScreen() {{
                if (!imgEl.naturalWidth || !imgEl.naturalHeight) return;
                const availW = wrap.clientWidth * 0.96;
                const availH = wrap.clientHeight * 0.96;
                const scale = Math.min(availW / imgEl.naturalWidth, availH / imgEl.naturalHeight);
                const targetW = Math.round(imgEl.naturalWidth * scale);
                const targetH = Math.round(imgEl.naturalHeight * scale);
                stage.style.width = targetW + 'px'; stage.style.height = targetH + 'px';
                imgEl.style.width = targetW + 'px'; imgEl.style.height = targetH + 'px';
                layer.style.width = targetW + 'px'; layer.style.height = targetH + 'px';
            }}
            window.addEventListener('resize', fitPageToScreen);

            let hudTimer = null;
            function resetHudTimer() {{ clearTimeout(hudTimer); }}
            function dismissCard() {{ document.getElementById('whisper-card').style.display = 'none'; clearTimeout(timer); }}
            function cycleSpeed() {{ speedIdx = (speedIdx + 1) % speeds.length; document.getElementById('speed-text').innerText = speeds[speedIdx] + "x"; if (isPlaying) {{ toggleKaraoke(); setTimeout(toggleKaraoke, 100); }} }}

            function loadPage(idx) {{
                if (idx < 0 || idx >= allPages.length) return;
                stopKaraoke(); currentIndex = idx; const page = allPages[idx];
                imgEl.onload = () => {{ fitPageToScreen(); }};
                imgEl.src = "data:image/jpeg;base64," + page.img_b64;
                if (imgEl.complete) {{ fitPageToScreen(); }}
                document.getElementById('page-counter').innerText = `{txt_page} ${{idx + 1}} / ${{allPages.length}}`;
                document.getElementById('btn-prev').disabled = (idx === 0);
                document.getElementById('btn-next').disabled = (idx === allPages.length - 1);
                dismissCard(); layer.innerHTML = ''; wordIndices = []; let charOffset = 0;
                
                (page.boxes || []).forEach((b, i) => {{
                    wordIndices.push({{ idx: i, start: charOffset, end: charOffset + b.text.length }});
                    charOffset += b.text.length + 1;
                    const d = document.createElement('div'); d.className = 'word-hitbox'; d.id = 'box_' + i;
                    d.style.left = b.left + '%'; d.style.top = b.top + '%'; d.style.width = b.width + '%'; d.style.height = b.height + '%';
                    
                    d.onclick = () => {{
                        clearTimeout(timer);
                        const dict = page.dictionary || {{}};
                        const cleanKey = b.clean || b.text.toLowerCase().trim();
                        let trans = dict[cleanKey] || dict[b.text.toLowerCase().trim()] || dict[b.text] || '-';
                        if (trans === '-' || !trans) {{
                            let noPunct = b.text.replace(/^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$/g, "").trim().toLowerCase();
                            trans = dict[noPunct] || '-';
                        }}
                        document.getElementById('whisper-body').innerHTML = "<div style='text-align: center; font-size: 15.5px;'>🇫🇷 <b>" + b.text + "</b> &nbsp;➔&nbsp; " + targetFlag + " <b>" + trans + "</b></div>";
                        document.getElementById('whisper-card').style.display = 'block';
                        document.getElementById('whisper-card').dataset.type = 'word';
                        window.speechSynthesis.cancel(); 
                        const u = new SpeechSynthesisUtterance(b.text); u.lang = 'fr-FR'; u.rate = speeds[speedIdx]; window.speechSynthesis.speak(u);
                        timer = setTimeout(dismissCard, 4500);
                    }};
                    layer.appendChild(d);
                }});
            }}
            function nextPage() {{ if (currentIndex < allPages.length - 1) loadPage(currentIndex + 1); }}
            function prevPage() {{ if (currentIndex > 0) loadPage(currentIndex - 1); }}

            function toggleTranslation() {{
                clearTimeout(timer);
                const tText = (allPages[currentIndex] && allPages[currentIndex].full_trans) ? allPages[currentIndex].full_trans : "{txt_loading}";
                const card = document.getElementById('whisper-card');
                if (card.style.display === 'block' && card.dataset.type === 'page') {{ dismissCard(); }} 
                else {{ 
                    document.getElementById('whisper-body').innerHTML = `<div style="font-size: 13.5px; font-weight: 600; color: #93c5fd; margin-bottom: 6px;">📝 {txt_trans} (${{targetFlag}})</div><div style="font-size: 15px; color: #f8fafc; text-align: left; line-height: 1.65; max-height: 40vh; overflow-y: auto;">${{tText}}</div>`;
                    card.style.display = 'block'; card.dataset.type = 'page';
                }}
            }}

            function toggleKaraoke() {{ if (isPlaying) stopKaraoke(); else playKaraoke(); }}
            function playKaraoke() {{
                window.speechSynthesis.cancel(); isPlaying = true; document.getElementById('btn-karaoke').classList.add('active'); document.getElementById('k-text').innerText = "{txt_stop}";
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
            function stopKaraoke() {{ isPlaying = false; window.speechSynthesis.cancel(); document.getElementById('btn-karaoke').classList.remove('active'); document.getElementById('k-text').innerText = "{txt_listen}"; document.querySelectorAll('.word-hitbox').forEach(el => el.classList.remove('karaoke-lit')); }}
            
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
# 6. DÜZENLEYİCİ EKRANI (TEST BUTONLU & GÜVENİLİR)
# ==========================================
elif st.session_state.editor_mode:
    st.subheader(f"✏️ Kitap Düzenleyici: {st.session_state.editor_book_title}")
    
    active_key = get_active_gemini_key()
    col_k1, col_k2, col_k3 = st.columns([1.5, 2.2, 1])
    with col_k1:
        if active_key:
            st.success("🟢 Gemini Vision Hazır")
        else:
            st.warning("🟠 EasyOCR Devrede (Anahtar Yok)")
    with col_k2:
        m_key = st.text_input("Gemini API Anahtarı:", value=st.session_state.manual_gemini_key, type="password", placeholder="AQ...", label_visibility="collapsed")
        clean_m_key = sanitize_gemini_key(m_key)
        if clean_m_key != st.session_state.manual_gemini_key:
            st.session_state.manual_gemini_key = clean_m_key
            st.rerun()
    with col_k3:
        if st.button("🧪 Anahtarı Test Et", use_container_width=True):
            if not active_key:
                st.error("Önce API anahtarınızı girin!")
            else:
                with st.spinner("Google sunucularına bağlanılıyor..."):
                    clean_k = sanitize_gemini_key(active_key)
                    test_success = False
                    last_test_err = ""
                    for m_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                        test_url = get_gemini_endpoint(m_name)
                        try:
                            t_data = json.dumps({"contents": [{"parts": [{"text": "Say 'OK'"}]}]}).encode("utf-8")
                            t_req = urllib.request.Request(
                                test_url,
                                data=t_data,
                                headers={
                                    "Content-Type": "application/json",
                                    "x-goog-api-key": clean_k,
                                    "User-Agent": "Mozilla/5.0"
                                }
                            )
                            with urllib.request.urlopen(t_req, timeout=12) as t_resp:
                                if t_resp.status == 200:
                                    st.toast(f"✅ Mükemmel! Gemini API ({m_name}) %100 çalışıyor.")
                                    st.success(f"✅ Bağlantı Başarılı: {m_name} Çalışıyor!")
                                    test_success = True
                                    break
                        except urllib.error.HTTPError as he:
                            err_txt = he.read().decode('utf-8', errors='ignore')
                            last_test_err = f"{m_name} HTTP {he.code}: {err_txt[:160]}"
                        except Exception as te:
                            last_test_err = f"{m_name} Bağlantı Hatası: {str(te)}"
                    if not test_success:
                        st.error(last_test_err)

    col_t1, col_t2, col_t3, col_t4 = st.columns([2.5, 1.5, 1.5, 1])
    with col_t1:
        st.session_state.editor_book_title = st.text_input("Kitap Başlığı:", value=st.session_state.editor_book_title, label_visibility="collapsed")
    with col_t2:
        if st.button(T("save_changes"), type="secondary", use_container_width=True):
            with st.spinner("Veritabanı güncelleniyor..."):
                saved_f, msg = save_hybrid_book(st.session_state.editor_book_title, st.session_state.editor_pages, st.session_state.editor_orig_book_id)
                if saved_f:
                    st.session_state.editor_orig_book_id = saved_f
                    st.success(msg)
                else:
                    st.error(msg)
    with col_t3:
        if st.button(T("save_and_read"), type="primary", use_container_width=True):
            with st.spinner("Kaydediliyor ve çeviriler paralel hazırlanıyor..."):
                saved_f, msg = save_hybrid_book(st.session_state.editor_book_title, st.session_state.editor_pages, st.session_state.editor_orig_book_id)
                if saved_f:
                    st.session_state.uploaded_book_pages = ensure_reading_ready(st.session_state.editor_pages, st.session_state.app_lang)
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

    if total_p > 0:
        with st.expander("⚙️ Gelişmiş & Toplu İşlemler"):
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                if st.button("🔄 Tüm Kitabı Baştan Tara (Toplu)", type="primary"):
                    p_bar = st.progress(0)
                    s_txt = st.empty()
                    for idx, p in enumerate(pages):
                        s_txt.text(f"Sayfa {idx + 1} / {total_p} taranıyor...")
                        try:
                            img_bytes = base64.b64decode(p['img_b64'])
                            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                            re_page, engine_name, err = process_single_image(pil_img)
                            p['boxes'] = re_page['boxes']
                        except Exception:
                            pass
                        p_bar.progress((idx + 1) / total_p)
                    s_txt.text("Tüm sayfaların taraması tamamlandı!")
                    st.success("Tüm sayfalar güncellendi! Kalıcı olması için 'Değişiklikleri Kaydet' butonuna basınız.")
                    time.sleep(0.5)
                    st.rerun()
            with col_b2:
                st.caption("Bütün kitabı seçili motorla baştan tarar.")

    with st.expander("➕ Bu Kitaba Yeni Sayfa(lar) Ekle", expanded=(total_p == 0)):
        add_mode = st.radio("Yeni Sayfa Ekleme Türü:", ["📸 Kameradan Çek & Kırp", "📁 Fotoğraf(lar) Yükle", "📄 Taranmış PDF Ekle"], horizontal=True, key="ed_add_mode")
        split_new_spreads = st.checkbox("📖 Yeni Çift Sayfaları Otomatik Böl", value=True, key="ed_split_box")
        
        if add_mode == "📸 Kameradan Çek & Kırp":
            c_input = st.camera_input("Yeni Sayfanın Fotoğrafını Çekin", key="ed_cam_in")
            alt_c_file = st.file_uploader("veya Telefondan Tek Fotoğraf Seçin:", type=["png", "jpg", "jpeg"], key="ed_alt_c")
            act_pic = c_input if c_input else alt_c_file
            if act_pic:
                raw_c_img = ImageOps.exif_transpose(Image.open(act_pic)).convert("RGB")
                st.write("📐 **Sayfayı Çerçeveyle Kırpın:**")
                cropped_p = st_cropper(raw_c_img, realtime_update=True, box_color='#2563eb') if CROPPER_SUPPORT else raw_c_img
                if st.button("✂️ Bu Sayfayı Kitabın Sonuna Ekle", type="primary", key="btn_crop_add_ed"):
                    with st.spinner("Sayfa taranıyor..."):
                        new_p_obj, engine_used, err = process_single_image(cropped_p)
                        pages.append(new_p_obj)
                        st.session_state.editor_page_idx = len(pages) - 1
                        st.success(f"Sayfa {len(pages)} olarak eklendi! (Motor: {engine_used})")
                        time.sleep(0.5)
                        st.rerun()

        elif add_mode == "📁 Fotoğraf(lar) Yükle":
            new_files = st.file_uploader("Ek Kitap Sayfalarını Seçin (PNG/JPG):", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="ed_multi_files")
            if new_files and st.button("⚡ Seçilen Fotoğrafları Kitaba Ekle", type="primary", key="btn_files_add_ed"):
                p_bar = st.progress(0)
                s_txt = st.empty()
                total_n = len(new_files)
                for idx_f, nf in enumerate(new_files):
                    s_txt.text(f"Ekleniyor: {idx_f + 1} / {total_n}...")
                    b_img = ImageOps.exif_transpose(Image.open(nf)).convert("RGB")
                    if split_new_spreads and (b_img.width / b_img.height) > 1.05:
                        mid = b_img.width // 2
                        p1, _, _ = process_single_image(b_img.crop((0, 0, mid, b_img.height)))
                        p2, _, _ = process_single_image(b_img.crop((mid, 0, b_img.width, b_img.height)))
                        pages.append(p1)
                        pages.append(p2)
                    else:
                        p_single, _, _ = process_single_image(b_img)
                        pages.append(p_single)
                    del b_img
                    gc.collect()
                    p_bar.progress((idx_f + 1) / total_n)
                st.session_state.editor_page_idx = len(pages) - 1
                st.success("Fotoğraflar kitaba eklendi! Yukarıdan kaydetmeyi unutmayın.")
                time.sleep(0.5)
                st.rerun()

        elif add_mode == "📄 Taranmış PDF Ekle":
            if not PDF_SUPPORT:
                st.error("PyMuPDF kütüphanesi eksik.")
            else:
                new_pdf = st.file_uploader("Ek PDF Belgesi Seçin:", type=["pdf"], key="ed_pdf_in")
                if new_pdf:
                    pdf_data = new_pdf.read()
                    pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
                    max_p = len(pdf_doc)
                    p_range = st.slider("Eklenecek Sayfa Aralığı:", min_value=1, max_value=max_p, value=(1, max_p), key="slider_ed_pdf")
                    
                    if st.button("⚡ PDF Sayfalarını Kitaba Ekle", type="primary", key="btn_pdf_add_ed"):
                        start_idx = p_range[0] - 1
                        end_idx = p_range[1]
                        tot_sel = end_idx - start_idx
                        p_bar = st.progress(0)
                        s_txt = st.empty()
                        
                        for step_i, p_no in enumerate(range(start_idx, end_idx)):
                            s_txt.text(f"PDF Sayfası İşleniyor: {step_i + 1} / {tot_sel}...")
                            pix = pdf_doc[p_no].get_pixmap(dpi=130)
                            base_img = Image.open(io.BytesIO(pix.tobytes("jpeg"))).convert("RGB")
                            if split_new_spreads and (base_img.width / base_img.height) > 1.05:
                                mid = base_img.width // 2
                                p1, _, _ = process_single_image(base_img.crop((0, 0, mid, base_img.height)))
                                p2, _, _ = process_single_image(base_img.crop((mid, 0, base_img.width, base_img.height)))
                                pages.append(p1)
                                pages.append(p2)
                            else:
                                p_single, _, _ = process_single_image(base_img)
                                pages.append(p_single)
                            del pix, base_img
                            gc.collect()
                            p_bar.progress((step_i + 1) / tot_sel)
                            
                        pdf_doc.close()
                        st.session_state.editor_page_idx = len(pages) - 1
                        st.success("PDF sayfaları kitaba eklendi! Yukarıdan kaydetmeyi unutmayın.")
                        time.sleep(0.5)
                        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    if total_p == 0:
        st.info("Kitapta henüz sayfa bulunmuyor. Lütfen yukarıdaki panelden sayfa ekleyin.")
    else:
        if st.session_state.editor_page_idx >= total_p:
            st.session_state.editor_page_idx = total_p - 1
        p_idx = st.session_state.editor_page_idx
        curr_page = pages[p_idx]

        col_left, col_right = st.columns([1, 1.35])
        with col_left:
            st.markdown(f"### 📄 {T('zen_page')} {p_idx + 1} / {total_p}")
            row_sel, row_up, row_down, row_del = st.columns([2, 1, 1, 1])
            with row_sel:
                new_idx = st.selectbox("Sayfa Git:", options=list(range(total_p)), format_func=lambda i: f"{T('zen_page')} {i + 1}", index=p_idx, label_visibility="collapsed")
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
                if st.button("🗑️ Sayfayı Sil"):
                    pages.pop(p_idx)
                    st.session_state.editor_page_idx = max(0, min(p_idx, len(pages) - 1))
                    st.rerun()

            col_act1, col_act2 = st.columns([1, 1])
            with col_act1:
                if st.button(T("split_page_btn"), type="primary", use_container_width=True):
                    with st.spinner("Sayfa ortadan ikiye bölünüyor ve yeniden okunuyor..."):
                        try:
                            img_bytes = base64.b64decode(curr_page['img_b64'])
                            orig_pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                            w, h = orig_pil.size
                            mid_x = w // 2
                            
                            p1, _, _ = process_single_image(orig_pil.crop((0, 0, mid_x, h)))
                            p2, _, _ = process_single_image(orig_pil.crop((mid_x, 0, w, h)))
                            
                            pages[p_idx] = p1
                            pages.insert(p_idx + 1, p2)
                            st.success("Sayfa başarıyla bölündü!")
                            time.sleep(0.4)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Bölme hatası: {e}")

            with col_act2:
                if p_idx < total_p - 1:
                    if st.button(T("merge_page_btn"), type="secondary", use_container_width=True):
                        with st.spinner("Sayfalar yan yana birleştirilip taranıyor..."):
                            try:
                                merged_obj = merge_two_pages(pages[p_idx], pages[p_idx + 1])
                                pages[p_idx] = merged_obj
                                pages.pop(p_idx + 1)
                                st.success("İki sayfa başarıyla birleştirildi!")
                                time.sleep(0.4)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Birleştirme hatası: {e}")
                else:
                    st.button("🔗 Son Sayfa (Birleştirilemez)", disabled=True, use_container_width=True)

            if st.button(T("rescan_page_btn"), use_container_width=True):
                with st.spinner("Sayfa taranıyor..."):
                    try:
                        img_bytes = base64.b64decode(curr_page['img_b64'])
                        orig_pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                        re_obj, engine_used, err = process_single_image(orig_pil)
                        curr_page['boxes'] = re_obj['boxes']
                        if "Gemini" in engine_used:
                            st.success(f"✨ Başarılı! {engine_used} ile okundu.")
                        else:
                            if err:
                                st.error(f"Gemini Hatası: {err}")
                            st.warning("Motor: EasyOCR kullanıldı.")
                        time.sleep(0.8)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Tarama hatası: {e}")

            # SAYFA ÖNİZLEMESİ
            overlay_divs = "".join([
                f'<div style="position:absolute;left:{b["left"]}%;top:{b["top"]}%;width:{b["width"]}%;height:{b["height"]}%;border:2px solid #38bdf8;background:rgba(56,189,248,0.15);pointer-events:none;box-sizing:border-box;border-radius:3px;">'
                f'<span style="position:absolute;top:-15px;left:0;background:#0284c7;color:#ffffff;font-size:10px;font-weight:bold;padding:0 4px;border-radius:2px;line-height:14px;">#{b_i+1}</span>'
                f'</div>'
                for b_i, b in enumerate(curr_page.get("boxes", []))
            ])
            preview_html = (
                f'<div style="text-align:center;background:#0f172a;border-radius:8px;padding:10px;margin-top:10px;position:relative;display:inline-block;width:100%;">'
                f'<div style="position:relative;display:inline-block;max-width:100%;">'
                f'<img src="data:image/jpeg;base64,{curr_page["img_b64"]}" style="max-width:100%;max-height:480px;object-fit:contain;border-radius:4px;display:block;" />'
                f'{overlay_divs}'
                f'</div></div>'
            )
            st.markdown(preview_html, unsafe_allow_html=True)

        with col_right:
            st.markdown("### 🔤 Tespit Edilen Kelimeler ve Cümleler")
            st.caption("Cümlelerin sırasını aşağıdaki ⬆️ / ⬇️ imleç butonlarıyla değiştirebilirsiniz.")

            num_boxes = len(curr_page["boxes"])
            if num_boxes > 1:
                st.markdown("#### ↕️ Cümle / Kelime Sırasını Kaydır")
                col_pick, col_mv_u, col_mv_d = st.columns([2.5, 1, 1])
                with col_pick:
                    move_target_idx = st.selectbox(
                        "Taşınacak Cümle:",
                        options=list(range(num_boxes)),
                        format_func=lambda i: f"#{i+1}: {curr_page['boxes'][i]['text'][:30]}...",
                        key=f"reorder_select_{p_idx}",
                        label_visibility="collapsed"
                    )
                with col_mv_u:
                    if st.button("⬆️ Yukarı", disabled=(move_target_idx == 0), use_container_width=True, key=f"btn_u_{p_idx}"):
                        curr_page["boxes"][move_target_idx], curr_page["boxes"][move_target_idx - 1] = curr_page["boxes"][move_target_idx - 1], curr_page["boxes"][move_target_idx]
                        st.rerun()
                with col_mv_d:
                    if st.button("⬇️ Aşağı", disabled=(move_target_idx >= num_boxes - 1), use_container_width=True, key=f"btn_d_{p_idx}"):
                        curr_page["boxes"][move_target_idx], curr_page["boxes"][move_target_idx + 1] = curr_page["boxes"][move_target_idx + 1], curr_page["boxes"][move_target_idx]
                        st.rerun()

            table_data = [{"Sıra": i + 1, "Kaldır 🗑️": False, "Metin (Fransızca)": b["text"]} for i, b in enumerate(curr_page["boxes"])]
            edited_table = st.data_editor(
                table_data,
                key=f"editor_table_{p_idx}_{len(curr_page['boxes'])}",
                use_container_width=True,
                height=300,
                column_config={
                    "Sıra": st.column_config.NumberColumn("Sıra #", min_value=1, max_value=max(1, num_boxes), step=1, width="small"),
                    "Kaldır 🗑️": st.column_config.CheckboxColumn("Kaldır 🗑️", default=False, width="small"),
                    "Metin (Fransızca)": st.column_config.TextColumn("Metin (Fransızca)", required=True)
                }
            )

            col_app1, col_app2 = st.columns([2, 1.2])
            with col_app1:
                if st.button("🔄 Değişiklikleri Bu Sayfaya Uygula", type="primary", use_container_width=True):
                    valid_items = []
                    for i, row in enumerate(edited_table):
                        is_deleted = row.get("Kaldır 🗑️", False)
                        text_val = str(row.get("Metin (Fransızca)", "")).strip()
                        order_val = row.get("Sıra", i + 1)
                        if not is_deleted and text_val:
                            if i < len(curr_page["boxes"]):
                                box_obj = dict(curr_page["boxes"][i])
                            else:
                                box_obj = {"id": f"b_{len(valid_items)}", "left": 10, "top": 10, "width": 80, "height": 8}
                            box_obj["text"] = text_val
                            box_obj["clean"] = clean_word_key(text_val)
                            valid_items.append((order_val, box_obj))
                    
                    valid_items.sort(key=lambda x: x[0])
                    curr_page["boxes"] = [item[1] for item in valid_items]
                    st.success("Bu sayfanın kelimeleri ve sırası başarıyla güncellendi!")
                    time.sleep(0.3)
                    st.rerun()

            with col_app2:
                if st.button("🧹 Sayfa Nolarını Temizle", use_container_width=True):
                    curr_page["boxes"] = [b for b in curr_page["boxes"] if not b["text"].strip().isdigit()]
                    st.rerun()

            with st.expander("⚡ Bu Sayfanın Metnini Blok Halinde Toplu Düzelt"):
                curr_joined = " ".join([b["text"] for b in curr_page["boxes"]])
                bulk_input = st.text_area("Sayfada olması gereken doğru metin:", value=curr_joined, height=90)
                if st.button("✨ Sayfa Metnini Bu Cümleyle Yenile"):
                    if bulk_input.strip():
                        words = [w for w in bulk_input.strip().split() if w]
                        new_bulk_boxes = []
                        for w_i, w_txt in enumerate(words):
                            if w_i < len(curr_page["boxes"]):
                                old_box = dict(curr_page["boxes"][w_i])
                                old_box["text"] = w_txt
                                old_box["clean"] = clean_word_key(w_txt)
                                new_bulk_boxes.append(old_box)
                            else:
                                new_bulk_boxes.append({
                                    "id": f"b_{w_i}",
                                    "text": w_txt,
                                    "clean": clean_word_key(w_txt),
                                    "left": round(5 + (w_i % 5) * 18, 1),
                                    "top": round(20 + (w_i // 5) * 12, 1),
                                    "width": 16,
                                    "height": 9
                                })
                        curr_page["boxes"] = new_bulk_boxes
                        st.success("Sayfa metni tek seferde yenilendi! 'Değişiklikleri Kaydet' ile kaydedebilirsiniz.")
                        time.sleep(0.4)
                        st.rerun()

            with st.expander("➕ Sayfaya Eksik Kalan Kelime / Cümle Ekle"):
                missed_text = st.text_input("Görselde okunmamış metni buraya yazın:", key=f"missed_{p_idx}")
                if st.button("Metni Sayfaya Dahil Et", key=f"btn_missed_{p_idx}"):
                    if missed_text.strip():
                        new_b = {
                            "id": f"b_{len(curr_page['boxes'])}",
                            "text": missed_text.strip(),
                            "clean": clean_word_key(missed_text.strip()),
                            "left": 10, "top": 85, "width": 80, "height": 8
                        }
                        curr_page["boxes"].append(new_b)
                        st.success("Metin sayfaya eklendi!")
                        st.rerun()

# ==========================================
# 7. ANA KÜTÜPHANE EKRANI (EN YENİ KİTAPLAR EN ÜSTTE)
# ==========================================
else:
    col_info1, col_thanks, col_info2, col_info3 = st.columns([2.5, 1.2, 1.8, 1])
    with col_info1: st.markdown(f"👤 `{st.session_state.user_email}`")
    with col_thanks:
        if st.button(T("thanks_btn"), use_container_width=True): record_thanks(st.session_state.user_email); st.toast(T("thanks_success"))
    with col_info2:
        new_lang = st.selectbox("Dil", options=list(LANGUAGES.keys()), format_func=lambda x: f"{LANGUAGES[x]['flag']} {LANGUAGES[x]['name']}", index=list(LANGUAGES.keys()).index(st.session_state.app_lang) if st.session_state.app_lang in LANGUAGES else 0, label_visibility="collapsed")
        if new_lang != st.session_state.app_lang: st.session_state.app_lang = new_lang; st.rerun()
    with col_info3:
        if st.button(T("logout"), use_container_width=True): st.session_state.logged_in = False; st.rerun()

    st.markdown(f"<h2 style='text-align: center; color: #1e3a8a;'>{T('lib_title')}</h2>", unsafe_allow_html=True)
    
    col_ref1, col_ref2 = st.columns([4.2, 0.8])
    with col_ref2:
        if st.button("🔄 Yenile", use_container_width=True):
            st.rerun()

    saved_books, b_err = get_saved_books()
    if b_err:
        st.error(f"Veritabanı Uyarısı: {b_err} (Lütfen 'Yenile' butonuna basınız)")
        
    if not saved_books:
        st.info(T("empty_lib"))
    else:
        book_titles = {}
        for b in saved_books:
            short_d = format_short_date(b.get("date", ""))
            date_suffix = f" • 📅 {short_d}" if short_d else ""
            book_titles[b["book_id"]] = f"{b['title']} ({b['page_count']} sayfa){date_suffix}"
            
        selected_id = st.selectbox(T("select_book"), options=list(book_titles.keys()), format_func=lambda x: book_titles[x])
        
        col_r, col_e, col_d = st.columns([2, 2, 1])
        with col_r:
            if st.button(T("open_read"), type="primary", use_container_width=True):
                with st.spinner(T("ocr_processing")):
                    book_pages, l_err = load_book_content(selected_id)
                    if book_pages:
                        st.session_state.uploaded_book_pages = book_pages
                        st.session_state.current_book_title = next((b["title"] for b in saved_books if b["book_id"] == selected_id), "")
                        st.session_state.reading_mode = True; st.rerun()
                    else:
                        st.error(l_err)
        with col_e:
            if st.button(T("edit_book"), use_container_width=True) and st.session_state.user_role == "admin":
                with st.spinner("Kitap düzenleyiciye yükleniyor..."):
                    book_pages, l_err = load_book_content(selected_id)
                    if book_pages:
                        st.session_state.editor_pages = book_pages
                        st.session_state.editor_orig_book_id = selected_id
                        st.session_state.editor_book_title = next((b["title"] for b in saved_books if b["book_id"] == selected_id), "")
                        st.session_state.editor_page_idx = 0
                        st.session_state.editor_mode = True; st.rerun()
                    else:
                        st.error(l_err)
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
                if uploaded_pdf:
                    pdf_bytes = uploaded_pdf.read()
                    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    total_pdf_p = len(pdf_doc)
                    
                    st.info(f"PDF Belgesi Algılandı: Toplam **{total_pdf_p} sayfa** içeriyor.")
                    pdf_range = st.slider("Taranacak Sayfa Aralığı:", min_value=1, max_value=total_pdf_p, value=(1, total_pdf_p))
                    
                    if st.button("⚡ PDF'i Çözümle & Düzenleyiciye Aktar", type="primary", use_container_width=True):
                        extracted_pages = []
                        start_p = pdf_range[0] - 1
                        end_p = pdf_range[1]
                        count_p = end_p - start_p
                        
                        prog_bar = st.progress(0)
                        stat_text = st.empty()
                        
                        for idx_s, p_num in enumerate(range(start_p, end_p)):
                            stat_text.text(f"Sayfa {idx_s + 1} / {count_p} taranıyor...")
                            pix = pdf_doc[p_num].get_pixmap(dpi=130)
                            base_img = Image.open(io.BytesIO(pix.tobytes("jpeg"))).convert("RGB")
                            
                            if split_spreads and (base_img.width / base_img.height) > 1.05:
                                mid = base_img.width // 2
                                p1, _, _ = process_single_image(base_img.crop((0, 0, mid, base_img.height)))
                                p2, _, _ = process_single_image(base_img.crop((mid, 0, base_img.width, base_img.height)))
                                extracted_pages.append(p1)
                                extracted_pages.append(p2)
                            else:
                                p_single, _, _ = process_single_image(base_img)
                                extracted_pages.append(p_single)
                                
                            del pix, base_img
                            gc.collect()
                            prog_bar.progress((idx_s + 1) / count_p)
                            
                        pdf_doc.close()
                        stat_text.text("Tarama tamamlandı! Düzenleyiciye aktarılıyor...")
                        st.session_state.editor_pages = extracted_pages
                        st.session_state.editor_book_title = book_title_input.strip() or "İsimsiz Kitap"
                        st.session_state.editor_orig_book_id = None
                        st.session_state.editor_page_idx = 0
                        st.session_state.editor_mode = True
                        st.rerun()

            elif upload_mode == "📸 Kameradan Çek & Kırp":
                cam_pic = st.camera_input("Sayfanın Fotoğrafını Çekin")
                alt_file = st.file_uploader("veya Telefondan Tek Fotoğraf Seçin:", type=["png", "jpg"])
                active_pic = cam_pic if cam_pic else alt_file
                if active_pic:
                    raw_img = ImageOps.exif_transpose(Image.open(active_pic)).convert("RGB")
                    c_img = st_cropper(raw_img, realtime_update=True, box_color='#2563eb') if CROPPER_SUPPORT else raw_img
                    if st.button("✂️ Sepete Ekle"):
                        buf = io.BytesIO(); c_img.save(buf, format="JPEG"); st.session_state.staged_camera_pages.append(buf.getvalue())
                        st.success(f"Eklendi! Sepette: {len(st.session_state.staged_camera_pages)}")
                if len(st.session_state.staged_camera_pages) > 0:
                    if st.button("⚡ Sepettekileri Düzenleyiciye Aktar", type="primary"):
                        st.session_state.editor_pages = [process_single_image(Image.open(io.BytesIO(b)).convert("RGB"))[0] for b in st.session_state.staged_camera_pages]
                        st.session_state.staged_camera_pages = []
                        st.session_state.editor_book_title = book_title_input
                        st.session_state.editor_orig_book_id = None
                        st.session_state.editor_page_idx = 0
                        st.session_state.editor_mode = True; st.rerun()

            else:
                upl_files = st.file_uploader("Kitap sayfaları (PNG/JPG):", type=["png", "jpg"], accept_multiple_files=True)
                if upl_files and st.button("⚡ Taramayı Başlat", type="primary", use_container_width=True):
                    extracted_pages = []
                    total_f = len(upl_files)
                    prog_bar = st.progress(0)
                    stat_text = st.empty()
                    
                    for f_i, file in enumerate(upl_files):
                        stat_text.text(f"Fotoğraf {f_i + 1} / {total_f} taranıyor...")
                        b_img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
                        if split_new_spreads and (b_img.width / b_img.height) > 1.05:
                            mid = b_img.width // 2
                            p1, _, _ = process_single_image(b_img.crop((0, 0, mid, b_img.height)))
                            p2, _, _ = process_single_image(b_img.crop((mid, 0, b_img.width, b_img.height)))
                            extracted_pages.append(p1)
                            extracted_pages.append(p2)
                        else:
                            p_single, _, _ = process_single_image(b_img)
                            extracted_pages.append(p_single)
                        del b_img
                        gc.collect()
                        prog_bar.progress((f_i + 1) / total_f)
                        
                    stat_text.text("Tarama tamamlandı! Düzenleyiciye aktarılıyor...")
                    st.session_state.editor_pages = extracted_pages
                    st.session_state.editor_book_title = book_title_input
                    st.session_state.editor_orig_book_id = None
                    st.session_state.editor_page_idx = 0
                    st.session_state.editor_mode = True
                    st.rerun()

    st.markdown("<br><br><hr>", unsafe_allow_html=True)
    
    # ATATÜRK VE MİTİ ANMA BUTONU
    st.markdown(
        f"""
        <div style="text-align: center; color: #94a3b8; font-size: 13.5px; padding-top: 5px; margin-bottom: 15px;">
            ✍️ <b>{T('created_by')}</b>
        </div>
        """, unsafe_allow_html=True
    )
    
    t_title = translate_turkish_to_target(T("miti_title"), st.session_state.app_lang)
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
