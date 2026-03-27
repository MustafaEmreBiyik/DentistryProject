"""
Hata Bildirim Sayfasi
Kullanicilardan hizli teknik hata geri bildirimi toplar.
"""

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from app.frontend.components import render_sidebar

st.set_page_config(
    page_title="Dental Tutor - Hata Bildir",
    page_icon="🐞",
    layout="wide",
    initial_sidebar_state="expanded"
)

render_sidebar(
    page_type="feedback",
    show_case_selector=False,
    show_model_selector=False
)

st.title("🐞 Hata Bildir")
st.caption("iPhone mi tarayici mi daha net gorebilmek icin asagidaki formu doldurun.")

st.markdown(
    """
### Ne isimize yarar?
- Sorunun cihaz mi tarayici mi oldugunu ayristirir.
- Hangi sayfada patladigini tek bakista gosterir.
- Tekrarlanabilirlik ve ag bilgisi ile teshisi hizlandirir.
"""
)

reporter_name = st.session_state.get("user_name", "")
default_case = st.session_state.get("current_case_id", "")

with st.form("bug_report_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        full_name = st.text_input("Ad Soyad", value=reporter_name)
        device_type = st.selectbox(
            "Cihaz",
            ["iPhone", "Android", "iPad", "Windows PC", "Mac", "Diger"]
        )
        os_name = st.text_input("Isletim Sistemi", placeholder="Orn: iOS 17.4")
        browser_name = st.selectbox(
            "Tarayici",
            ["Safari", "Chrome", "Edge", "Firefox", "Samsung Internet", "Diger"]
        )
        browser_version = st.text_input("Tarayici Surumu", placeholder="Orn: 17.3")

    with col2:
        page_name = st.text_input("Hata Alinan Sayfa", placeholder="Orn: chat")
        case_id = st.text_input("Vaka ID", value=default_case)
        network_type = st.selectbox("Ag Turu", ["Wi-Fi", "Mobil Veri", "Kurumsal Ag", "Bilmiyorum"])
        reproducible = st.radio("Her denemede oluyor mu?", ["Evet", "Hayir", "Bazen"], horizontal=True)
        blocker = st.selectbox("Etkisi", ["Site acilmiyor", "Giris yapilamiyor", "Mesaj gonderilmiyor", "Yavaslik", "Diger"])

    step_when_failed = st.text_area(
        "Hangi adimda bozuldu?",
        placeholder="Orn: Login olduktan sonra Vaka Calismasi'na tiklayinca beyaz ekran oluyor."
    )
    error_message = st.text_area(
        "Gordugunuz hata mesaji",
        placeholder="Orn: 500 Internal Server Error / Connection reset"
    )

    submitted = st.form_submit_button("Kaydet", type="primary", use_container_width=True)

if submitted:
    if not page_name or not step_when_failed:
        st.warning("Lutfen en azindan sayfa ve hata adimini doldurun.")
    else:
        report = {
            "reported_at": datetime.utcnow().isoformat() + "Z",
            "reporter": full_name.strip(),
            "device_type": device_type,
            "os_name": os_name.strip(),
            "browser_name": browser_name,
            "browser_version": browser_version.strip(),
            "page_name": page_name.strip(),
            "case_id": case_id.strip(),
            "network_type": network_type,
            "reproducible": reproducible,
            "impact": blocker,
            "step_when_failed": step_when_failed.strip(),
            "error_message": error_message.strip(),
        }

        feedback_dir = Path(__file__).resolve().parent.parent / "data"
        feedback_dir.mkdir(parents=True, exist_ok=True)
        feedback_file = feedback_dir / "bug_reports.jsonl"

        with feedback_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(report, ensure_ascii=False) + "\n")

        st.success("Hata bildirimi kaydedildi. Tesekkurler.")
        st.info("Takip icin ekip bu kaydi bug_reports.jsonl dosyasindan gorebilir.")

st.divider()

with st.expander("Teknik not", expanded=False):
    st.write(
        "Bu form, cihaz ve tarayici farkini analiz etmek icin alanlari standart formatta toplar "
        "ve data/bug_reports.jsonl dosyasina satir satir yazar."
    )
