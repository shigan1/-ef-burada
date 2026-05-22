# --- 1. KÜTÜPHANELER ---
# Web sunucumuzu kurmak ve dosya/form verisi almak için gereken araçlar
from fastapi import FastAPI, UploadFile, File, Form
# Frontend (tarayıcı) ile Backend (Python) arasındaki güvenlik duvarını (CORS) aşmak için
from fastapi.middleware.cors import CORSMiddleware
# Google'ın yeni nesil yapay zeka araçları
from google import genai
from google.genai import types
# Fotoğrafı yapay zekanın anlayabileceği formata çevirmek için gereken araçlar
import PIL.Image
import io
# Yapay zekadan gelen metni Python verisine (Sözlük/Dizi) çevirmek için
import json

# --- 2. SUNUCU AYARLARI ---
# FastAPI sunucu uygulamamızı başlatıyoruz
app = FastAPI()

# Web sitenin (örneğin localhost:3000 veya HTML dosyası) bu Python sunucusuna 
# engellenmeden istek atabilmesi için kapıları açıyoruz (CORS ayarları)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Herkes istek atabilir (Canlıya alırken sitenin linki yazılır)
    allow_methods=["*"], # Tüm istek tiplerine (GET, POST vb.) izin ver
    allow_headers=["*"], # Tüm başlık (header) verilerine izin ver
)

# --- 3. YAPAY ZEKA BAĞLANTISI ---
# Google Gemini API anahtarını tanımlıyoruz (Güvenliğin için bunu kimseyle paylaşma)
API_KEY = "Api_Kodu_Buraya"
# Modeli çağırmak için bir istemci (client) oluşturuyoruz
client = genai.Client(api_key=API_KEY)

# --- 4. API UCU (ENDPOINT) ---
# Web sitesi bu adrese ("/tarif-al") POST isteği attığında bu fonksiyon çalışacak
@app.post("/tarif-al")
async def tarif_al(
    resim: UploadFile = File(...), # Kullanıcıdan zorunlu olarak bir resim dosyası alıyoruz
    zorluk: str = Form("kolay")    # Kullanıcıdan yemek zorluk derecesini alıyoruz (Göndermezse 'kolay' varsayıyoruz)
):
    # try-except bloğu: İşlem sırasında sunucu çökerse programı kapatmak yerine except kısmına atla
    try:
        # --- 5. GÖRSEL İŞLEME ---
        # Yüklenen resmi bilgisayarın hafızasında okuyoruz
        image_data = await resim.read()
        # Okunan resmi yapay zekanın kabul edeceği PIL Image formatına dönüştürüyoruz
        img = PIL.Image.open(io.BytesIO(image_data))
        
        # --- 6. YAPAY ZEKA KOMUTU (PROMPT) ---
        # Modele tam olarak ne yapmasını istediğimizi ve hangi formatta cevap vereceğini söylüyoruz
        komut = f"""
        Sen usta ve yaratıcı bir şefsin. Ekteki fotoğrafı dikkatlice incele.
        
        GÖREV:
        1. Önce fotoğrafta gördüğün TÜM yenebilir malzemeleri belirle ve bunu "dolaptaki_malzemeler" listesine yaz.
        2. SADECE bu listedeki malzemeleri (ve yağ, tuz, baharat gibi temel ev ürünlerini) kullanarak {zorluk} seviyesinde birbirinden TAMAMEN FARKLI 2 yemek tarifi üret.
        
        KURALLAR:
        - İki tarif aynı yemeğin laciverti OLAMAZ (Örn: Biri omlet, diğeri çırpılmış yumurta olamaz). Tatları, isimleri ve tarzları birbirinden tamamen farklı olmalı.
        - Bir tarifte listedeki malzemelerin sadece bir kısmını, diğer tarifte farklı bir kısmını kullanabilirsin. Hepsini her tarifte aynı anda kullanmak zorunda değilsin.
        - Fotoğrafta OLMAYAN hiçbir ana malzemeyi (et, peynir, farklı sebze vb.) tariflere KESİNLİKLE ekleme.

        Cevabını SADECE aşağıdaki JSON formatında ver, başka hiçbir kelime yazma:
        {{
          "dolaptaki_malzemeler": ["Gördüğün Tüm Malzeme 1", "Gördüğün Tüm Malzeme 2"],
          "tarifler": [
            {{
              "baslik": "1. Yemek",
              "malzemeler": ["Sadece bu tarifte kullanılanlar..."],
              "adimlar": ["Adım 1", "Adım 2"],
              "ingilizce_gorsel_kelimesi": "Delicious [ENGLISH RECIPE NAME] plate food photography"
            }},
            {{
              "baslik": "2. Yemek (ZORUNLU)",
              "malzemeler": ["Sadece bu tarifte kullanılanlar..."],
              "adimlar": ["Adım 1", "Adım 2"],
              "ingilizce_gorsel_kelimesi": "Delicious [ENGLISH RECIPE NAME] plate food photography"
            }}
          ]
        }}
        
        DİKKAT: "tarifler" dizisi KESİNLİKLE 2 obje içermelidir! 1 tarif kesinlikle kabul edilemez.
        """
        
        # --- 7. MODELİ ÇAĞIRMA ---
        # Gemini modeline komutumuzu ve resmi gönderiyoruz
        cevap = client.models.generate_content(
            model='gemini-2.5-flash', # Kullandığımız hızlı ve ücretsiz model
            contents=[komut, img],    # Gönderilen veriler
            config=types.GenerateContentConfig(
                response_mime_type="application/json", # Yapay zekayı SADECE JSON vermeye zorluyoruz (Markdown vs. yazmasını engeller)
            )
        )
        
        # Yapay zekanın ürettiği metin formatındaki JSON'u, gerçek bir Python Sözlüğüne (Dictionary) çeviriyoruz
        sonuc_json = json.loads(cevap.text)
        
        # Hata ayıklama (Debug) için üretilen sonucu VS Code siyah terminaline yazdırıyoruz
        # (Bu satırlar kodun çalışması için zorunlu değildir ama arka planda ne döndüğünü görmek için hayat kurtarır)
        print("\n=== BAŞARIYLA ÜRETİLEN JSON ===")
        print(json.dumps(sonuc_json, indent=2, ensure_ascii=False))
        print("===============================\n")
        
        # Çıkan sonucu frontend'e (web sitene) başarılı bir şekilde geri gönderiyoruz
        return sonuc_json
        
    # --- 8. HATA YAKALAMA (ERROR HANDLING) ---
    except Exception as e:
        # Kodun herhangi bir yerinde hata çıkarsa sistemi çökertme, hatayı bir değişkene at
        hata_mesaji = str(e)
        
        # Hatayı terminale yazdır (senin görmen için)
        print(f"\n!!! HATA: {hata_mesaji} !!!\n")
        
        # Eğer hatanın sebebi API kotasının dolması (Çok hızlı istek atılması) ise:
        if "429" in hata_mesaji or "quota" in hata_mesaji.lower():
            return {"hata": "⏳ Şefimiz biraz yoruldu (Hız limitine takıldık). Lütfen 1 dakika bekleyip tekrar deneyin!"}
            
        # Eğer hatanın sebebi Google sunucularının o anlık aşırı yoğun olması ise:
        elif "503" in hata_mesaji or "demand" in hata_mesaji.lower():
            return {"hata": "👨‍🍳 Google sunucuları şu anda çok yoğun. Lütfen 10-15 saniye bekleyip tekrar deneyin!"}
            
        # Resim okunamaması veya yapay zekanın JSON formatını bozması gibi diğer tüm hatalar için:
        else:
            return {"hata": "Tarifler oluşturulurken beklenmeyen bir hata oluştu."}