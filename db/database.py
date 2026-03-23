"""
DentAI Database Setup
=====================
SQLAlchemy models and database configuration.
Supports SQLite (Local) and PostgreSQL (Production).
"""

import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==================== VERİTABANI KONFIGÜRASYONU ====================

# Streamlit Cloud için st.secrets'dan oku, yoksa environment variable'dan al
try:
    import streamlit as st
    DATABASE_URL = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL"))
except (ImportError, FileNotFoundError, AttributeError):
    # Streamlit yoksa veya secrets.toml yoksa, environment variable kullan
    DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render/Heroku gibi platformlar 'postgres://' verebilir, SQLAlchemy için 'postgresql://' olmalı
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # PostgreSQL için Supabase connection settings
    # Streamlit Cloud için SSL ve connection pooling ayarları
    engine_kwargs = {
        "pool_pre_ping": True,  # Bağlantıyı kullanmadan önce test et
        "pool_recycle": 300,  # 5 dakikada bir bağlantıları yenile
        "pool_size": 5,  # Connection pool boyutu
        "max_overflow": 2,  # Ekstra bağlantı limiti
        "connect_args": {
            "connect_timeout": 10,  # 10 saniye bağlantı timeout'u
            "sslmode": "require",  # Supabase için SSL gerekli
        }
    }
else:
    # Lokal geliştirme için SQLite
    DATABASE_URL = "sqlite:///./dentai_app.db"
    # Streamlit + SQLite için check_same_thread=False kritik!
    engine_kwargs = {"connect_args": {"check_same_thread": False}}

# Engine oluştur
engine = create_engine(
    DATABASE_URL,
    echo=False,  # True yaparsanız SQL sorgularını görebilirsiniz (debug için)
    **engine_kwargs
)

# Session factory (her veritabanı işlemi için yeni session)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base (tüm modeller bundan türeyecek)
Base = declarative_base()


# ==================== VERİTABANI MODELLERİ ====================

class StudentSession(Base):
    """
    Öğrenci Oturumu Tablosu
    -----------------------
    Her öğrencinin bir vaka üzerindeki çalışma oturumunu takip eder.
    """
    __tablename__ = "student_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, nullable=False, index=True)  # Öğrenci kimliği
    case_id = Column(String, nullable=False)  # Hangi vaka üzerinde çalışıyor
    current_score = Column(Float, default=0.0)  # Anlık puan
    start_time = Column(DateTime, default=datetime.datetime.utcnow)  # Oturum başlangıç zamanı

    # İlişki: Bir oturumun birden fazla chat mesajı olabilir
    chat_logs = relationship("ChatLog", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StudentSession(id={self.id}, student={self.student_id}, case={self.case_id}, score={self.current_score})>"


class ChatLog(Base):
    """
    Sohbet Geçmişi Tablosu
    ----------------------
    Öğrenci-AI arasındaki tüm mesajları kaydeder.
    MedGemma validasyon sonuçlarını metadata_json alanında saklar.
    """
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("student_sessions.id"), nullable=False)  # Hangi oturuma ait
    role = Column(String, nullable=False)  # 'user', 'assistant', veya 'system_validator'
    content = Column(Text, nullable=False)  # Mesaj içeriği
    metadata_json = Column(JSON, nullable=True)  # MedGemma analiz sonuçları (JSON formatında)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)  # Mesaj zamanı

    # İlişki: Her chat log bir oturuma aittir
    session = relationship("StudentSession", back_populates="chat_logs")

    def __repr__(self):
        return f"<ChatLog(id={self.id}, session_id={self.session_id}, role={self.role})>"


class FeedbackLog(Base):
    """
    Öğrenci Geri Bildirim Tablosu
    ----------------------------
    Öğrencilerin oturum sonunda verdikleri geri bildirimleri saklar.
    Akademik makale için nitel veri toplama.
    """
    __tablename__ = "feedback_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("student_sessions.id"), nullable=False)  # Hangi oturuma ait
    rating = Column(Integer, nullable=False)  # 1-5 yıldız memnuniyet puanı
    comment = Column(Text, nullable=True)  # Öğrenci yorumları (opsiyonel)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)  # Geri bildirim zamanı

    def __repr__(self):
        return f"<FeedbackLog(id={self.id}, session_id={self.session_id}, rating={self.rating})>"


# ==================== VERİTABANI FONKSİYONLARI ====================

def init_db():
    """
    Veritabanını başlat (tüm tabloları oluştur).
    Uygulama ilk çalıştırıldığında çağrılmalı.
    """
    try:
        # Streamlit Cloud için: Bağlantıyı test et
        import streamlit as st
        
        # Bağlantı test et
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Tabloları oluştur (varsa atlayacak)
        Base.metadata.create_all(bind=engine)
        
    except ImportError:
        # Streamlit yoksa (lokal geliştirme), normal oluştur
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # Streamlit Cloud için hata mesajı
        try:
            import streamlit as st
            st.error(f"""
            ⚠️ Veritabanı bağlantı hatası!
            
            **Olası Çözümler:**
            1. Streamlit Cloud ayarlarından 'Secrets' bölümüne `DATABASE_URL` ekleyin
            2. Supabase veritabanınızın aktif olduğundan emin olun (free tier pause olabilir)
            3. Supabase'de Connection Pooler kullanın (port 6543)
            4. Bağlantı string'inde özel karakterler URL-encoded olmalı
            
            **Detaylı hata:** `{str(e)}`
            """)
            # Hata fırlat ki kullanıcı görsün
            raise
        except ImportError:
            # Streamlit yoksa exception'ı direkt fırlat
            raise


def get_db():
    """
    Veritabanı session generator (Dependency Injection için).
    
    Kullanım örneği:
    ---------------
    db = next(get_db())
    try:
        # Veritabanı işlemleri
        db.add(new_session)
        db.commit()
    finally:
        db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== TEST BLOĞU ====================

if __name__ == "__main__":
    """
    Bu dosyayı doğrudan çalıştırarak veritabanını oluşturabilirsiniz:
    python app/db/database.py
    """
    print("🚀 Veritabanı oluşturuluyor...")
    init_db()
    print("✅ Database created successfully!")
    print(f"📁 Dosya konumu: {DATABASE_URL}")
    
    # Test: Örnek bir session oluştur
    db = SessionLocal()
    try:
        test_session = StudentSession(
            student_id="test_student_001",
            case_id="olp_001",
            current_score=0.0
        )
        db.add(test_session)
        db.commit()
        db.refresh(test_session)
        
        print(f"✅ Test session oluşturuldu: {test_session}")
        
        # Test: Örnek bir chat log ekle
        test_chat = ChatLog(
            session_id=test_session.id,
            role="user",
            content="Hastanın tıbbi geçmişini öğrenmek istiyorum.",
            metadata_json=None
        )
        db.add(test_chat)
        db.commit()
        
        print(f"✅ Test chat log oluşturuldu: {test_chat}")
        print("\n🎉 Veritabanı testi başarılı!")
        
    except Exception as e:
        print(f"❌ Test sırasında hata: {e}")
        db.rollback()
    finally:
        db.close()
 