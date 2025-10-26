# Patoloji Kategorilerine Göre Vaka Kuralları ve Validasyon

from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

class DifficultyLevel(Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"

class PathologyCategory(Enum):
    INFECTIOUS = "infectious"
    NEOPLASTIC = "neoplastic"
    IMMUNOLOGIC = "immunologic"
    TRAUMATIC = "traumatic"
    DEVELOPMENTAL = "developmental"
    SYSTEMIC = "systemic"
    REACTIVE = "reactive"
    RARE = "rare_conditions"

@dataclass
class CategoryRules:
    """Her patoloji kategorisi için özel kurallar"""
    
    category: PathologyCategory
    min_cases_per_level: Dict[DifficultyLevel, int]
    required_features: List[str]
    optional_features: List[str]
    assessment_focus: Dict[str, float]  # Değerlendirme ağırlıkları
    special_considerations: List[str]

# ============================================================================
# KATEGORİ KURALLARI TANIMLAMALARI
# ============================================================================

INFECTIOUS_DISEASE_RULES = CategoryRules(
    category=PathologyCategory.INFECTIOUS,
    min_cases_per_level={
        DifficultyLevel.BASIC: 8,
        DifficultyLevel.INTERMEDIATE: 8,
        DifficultyLevel.EXPERT: 4
    },
    required_features=[
        "etiyolojik ajan bilgisi",
        "bulaşma yolu",
        "karakteristik klinik bulgular",
        "tanı yöntemi (kültür/smear/PCR)",
        "antimikrobiyal tedavi protokolü"
    ],
    optional_features=[
        "immunokompromize hasta faktörü",
        "antibiyotik direnci",
        "komplikasyonlar"
    ],
    assessment_focus={
        "mikrobiyal tanımlama": 0.25,
        "tedavi seçimi": 0.30,
        "enfeksiyon kontrolü": 0.25,
        "komplikasyon önleme": 0.20
    },
    special_considerations=[
        "Antibiyotik seçiminde alerji kontrolü ZORUNLU",
        "Viral enfeksiyonlarda antibiyotik reçete edilmemeli",
        "Fungal enfeksiyonlarda predispozan faktörler sorgulanmalı",
        "İmmun yetmezlik durumunda konsültasyon gerekli"
    ]
)

NEOPLASTIC_DISEASE_RULES = CategoryRules(
    category=PathologyCategory.NEOPLASTIC,
    min_cases_per_level={
        DifficultyLevel.BASIC: 5,
        DifficultyLevel.INTERMEDIATE: 10,
        DifficultyLevel.EXPERT: 8
    },
    required_features=[
        "lezyon karakteristikleri (boyut, sınır, konsistans)",
        "malignite risk faktörleri",
        "TNM evreleme (malign vakalar için)",
        "biyopsi endikasyonu",
        "acil sevk kriterleri"
    ],
    optional_features=[
        "genetik predispozisyon",
        "metastaz değerlendirmesi",
        "adjuvan tedavi seçenekleri"
    ],
    assessment_focus={
        "erken tanı": 0.30,
        "risk stratifikasyonu": 0.25,
        "sevk zamanlaması": 0.25,
        "hasta bilgilendirme": 0.20
    },
    special_considerations=[
        "Premalign lezyonlarda ZORUNLU takip protokolü",
        "Asemptomatik lezyon = tehlike sinyali",
        "Erken sevk = hayat kurtarır vurgusu",
        "2 haftada iyileşmeyen ülser = biyopsi",
        "Field cancerization konsepti açıklanmalı"
    ]
)

IMMUNOLOGIC_DISEASE_RULES = CategoryRules(
    category=PathologyCategory.IMMUNOLOGIC,
    min_cases_per_level={
        DifficultyLevel.BASIC: 3,
        DifficultyLevel.INTERMEDIATE: 10,
        DifficultyLevel.EXPERT: 7
    },
    required_features=[
        "otoimmün mekanizma",
        "sistemik manifestasyonlar",
        "immunosupresif tedavi seçenekleri",
        "dental tedavi modifikasyonları",
        "multidisipliner yönetim"
    ],
    optional_features=[
        "genetik faktörler",
        "tetikleyici faktörler",
        "alevlenme-remisyon paternleri"
    ],
    assessment_focus={
        "oral-sistemik bağlantı": 0.30,
        "immunosupresyon riskleri": 0.25,
        "tedavi koordinasyonu": 0.25,
        "uzun dönem takip": 0.20
    },
    special_considerations=[
        "Kortikosteroid yan etkileri bilgisi ZORUNLU",
        "Dental prosedür öncesi medikal konsültasyon",
        "Nikolsky sign değerlendirmesi",
        "Immunosupresif tedavi altında enfeksiyon riski yüksek"
    ]
)

TRAUMATIC_LESION_RULES = CategoryRules(
    category=PathologyCategory.TRAUMATIC,
    min_cases_per_level={
        DifficultyLevel.BASIC: 5,
        DifficultyLevel.INTERMEDIATE: 3,
        DifficultyLevel.EXPERT: 2
    },
    required_features=[
        "travma kaynağı identifikasyonu",
        "kronik vs akut travma ayrımı",
        "iyileşme süreci beklentisi",
        "travma kaynağı eliminasyonu"
    ],
    optional_features=[
        "alışkanlık (bruksizm, dil ısırma)",
        "iatrojenik nedenler",
        "self-mutilation"
    ],
    assessment_focus={
        "neden-sonuç ilişkisi": 0.35,
        "kronik travma riski": 0.25,
        "önleyici yaklaşım": 0.25,
        "iyileşme takibi": 0.15
    },
    special_considerations=[
        "2 hafta içinde iyileşme beklenir",
        "Travma kaynağı elimine edilmezse rekürrens",
        "Kronik travma = premalign potansiyel",
        "Şüpheli travma öyküsü = abus olasılığı"
    ]
)

DEVELOPMENTAL_ANOMALY_RULES = CategoryRules(
    category=PathologyCategory.DEVELOPMENTAL,
    min_cases_per_level={
        DifficultyLevel.BASIC: 5,
        DifficultyLevel.INTERMEDIATE: 6,
        DifficultyLevel.EXPERT: 4
    },
    required_features=[
        "gelişimsel timing",
        "genetik/herediter faktörler",
        "sendrom ilişkisi",
        "fonksiyonel etki"
    ],
    optional_features=[
        "aile taraması",
        "prenatal faktörler",
        "cerrahi/ortodontik müdahale"
    ],
    assessment_focus={
        "anomali tanımlama": 0.30,
        "sendrom ayırımı": 0.25,
        "tedavi gerekliliği": 0.25,
        "genetik danışmanlık": 0.20
    },
    special_considerations=[
        "Çoklu anomali = sendrom araştır",
        "Aile öyküsü sorgulanmalı",
        "Erken tanı = daha iyi prognoz",
        "Multidisipliner yaklaşım (ortodonti, cerrahi, genetik)"
    ]
)

SYSTEMIC_MANIFESTATION_RULES = CategoryRules(
    category=PathologyCategory.SYSTEMIC,
    min_cases_per_level={
        DifficultyLevel.BASIC: 3,
        DifficultyLevel.INTERMEDIATE: 10,
        DifficultyLevel.EXPERT: 7
    },
    required_features=[
        "primer sistemik hastalık",
        "oral manifestasyon mekanizması",
        "sistemik hastalık kontrolü",
        "dental tedavi modifikasyonları",
        "medikal konsültasyon"
    ],
    optional_features=[
        "ilaç yan etkileri",
        "nutrisyonel faktörler",
        "metabolik bozukluklar"
    ],
    assessment_focus={
        "oral bulgu-sistemik hastalık bağlantısı": 0.35,
        "medikal durum değerlendirmesi": 0.25,
        "tedavi modifikasyonları": 0.25,
        "multidisipliner iletişim": 0.15
    },
    special_considerations=[
        "Oral bulgular sistemik hastalığın ilk belirtisi olabilir",
        "Kontrolsüz sistemik hastalık = dental tedavi ertele",
        "İlaç etkileşimleri mutlaka kontrol et",
        "Düzenli medikal takip şart"
    ]
)

REACTIVE_LESION_RULES = CategoryRules(
    category=PathologyCategory.REACTIVE,
    min_cases_per_level={
        DifficultyLevel.BASIC: 4,
        DifficultyLevel.INTERMEDIATE: 2,
        DifficultyLevel.EXPERT: 1
    },
    required_features=[
        "irritan faktör identifikasyonu",
        "lezyon gelişim mekanizması",
        "cerrahi eksizyon endikasyonu",
        "rekürrens önleme"
    ],
    optional_features=[
        "hormonal faktörler",
        "sistemik predispozisyon"
    ],
    assessment_focus={
        "irritan eliminasyonu": 0.30,
        "cerrahi planlama": 0.30,
        "histopatolojik doğrulama": 0.25,
        "rekürrens riski": 0.15
    },
    special_considerations=[
        "İrritasyon kaynağı çıkarılmazsa nüks eder",
        "Cerrahi eksizyon sırasında tam çıkarılmalı",
        "Histopatolojik inceleme ZORUNLU",
        "Oral hijyen eğitimi önemli"
    ]
)

RARE_CONDITION_RULES = CategoryRules(
    category=PathologyCategory.RARE,
    min_cases_per_level={
        DifficultyLevel.BASIC: 0,  # Rare cases are not basic
        DifficultyLevel.INTERMEDIATE: 3,
        DifficultyLevel.EXPERT: 5
    },
    required_features=[
        "nadir görülme sıklığı bilgisi",
        "literatür tarama becerisi",
        "uzman konsültasyonu kararı",
        "atipik prezentasyon tanıma"
    ],
    optional_features=[
        "genetik testler",
        "moleküler patoloji",
        "deneysel tedaviler"
    ],
    assessment_focus={
        "literatür kullanımı": 0.25,
        "ayırıcı tanı genişliği": 0.30,
        "uzman sevk kararı": 0.25,
        "belirsizlik yönetimi": 0.20
    },
    special_considerations=[
        "Literatür araştırma izin verilebilir",
        "Emin değilsen konsülte et mesajı",
        "Nadir = her zaman düşün ama önce sık olanlar",
        "Atipik bulgular dik