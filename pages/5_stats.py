"""
İstatistik Sayfası - Dental Tutor AI
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sys

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.student_profile import init_student_profile
from app.frontend.components import render_sidebar
from db.database import SessionLocal, StudentSession, ChatLog, init_db
import json

# Initialize systems
init_student_profile()
init_db()

# Page config
st.set_page_config(
    page_title="Dental Tutor AI - İstatistikler",
    page_icon="📊",
    layout="wide"
)

# ==================== SIDEBAR ====================
render_sidebar(
    page_type="stats",
    show_case_selector=False,
    show_model_selector=False
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("📊 Performans İstatistikleri")
st.markdown("---")

# ==================== LOAD DATA FROM DATABASE ====================
def load_student_stats():
    """Load statistics from database for current student."""
    profile = st.session_state.get("student_profile") or {}
    student_id = profile.get("student_id", "web_user_default")
    
    db = SessionLocal()
    try:
        # Get all sessions for this student
        sessions = db.query(StudentSession).filter_by(student_id=student_id).all()
        
        if not sessions:
            return {
                "action_history": [],
                "total_score": 0,
                "total_actions": 0,
                "completed_cases": set()
            }
        
        action_history = []
        total_score = 0
        total_actions = 0
        completed_cases = set()
        
        for session in sessions:
            # Get chat logs for this session
            logs = db.query(ChatLog).filter_by(
                session_id=session.id,
                role="assistant"  # Only assistant messages have evaluation metadata
            ).all()
            
            for log in logs:
                if log.metadata_json:
                    try:
                        metadata = log.metadata_json if isinstance(log.metadata_json, dict) else json.loads(log.metadata_json)
                        
                        # Extract action info
                        interpreted_action = metadata.get("interpreted_action", "unknown")
                        assessment = metadata.get("assessment", {})
                        score = assessment.get("score", 0)
                        outcome = assessment.get("rule_outcome", "N/A")
                        
                        # Only count if it's an ACTION (not CHAT)
                        if interpreted_action and interpreted_action != "general_chat" and interpreted_action != "error":
                            action_record = {
                                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "N/A",
                                "case_id": metadata.get("case_id", session.case_id),
                                "action": interpreted_action,
                                "score": score,
                                "outcome": outcome
                            }
                            action_history.append(action_record)
                            total_score += score
                            total_actions += 1
                            completed_cases.add(session.case_id)
                    except Exception as e:
                        st.error(f"Error parsing metadata: {e}")
                        continue
        
        return {
            "action_history": action_history,
            "total_score": total_score,
            "total_actions": total_actions,
            "completed_cases": completed_cases
        }
    
    except Exception as e:
        st.error(f"Veritabanı hatası: {e}")
        return {
            "action_history": [],
            "total_score": 0,
            "total_actions": 0,
            "completed_cases": set()
        }
    finally:
        db.close()

# Load stats from database
stats = load_student_stats()
action_history = stats["action_history"]
total_score = stats["total_score"]
total_actions = stats["total_actions"]
completed_cases = stats["completed_cases"]

# Overview Metrics
st.markdown("## 🎯 Genel Bakış")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-value">{total_score}</p>
        <p class="metric-label">Toplam Puan</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
        <p class="metric-value">{total_actions}</p>
        <p class="metric-label">Toplam Eylem</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    avg_score = total_score / total_actions if total_actions > 0 else 0
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
        <p class="metric-value">{avg_score:.1f}</p>
        <p class="metric-label">Ortalama Puan/Eylem</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
        <p class="metric-value">{len(completed_cases)}</p>
        <p class="metric-label">Tamamlanan Vaka</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Action History
if action_history:
    st.markdown("## 📋 Son Eylemler")
    
    # Create DataFrame
    df = pd.DataFrame(action_history)
    
    # Display table
    st.dataframe(
        df[['timestamp', 'case_id', 'action', 'score', 'outcome']].tail(10),
        width='stretch',
        hide_index=True
    )
    
    # ==================== CSV EXPORT FOR RESEARCHERS ====================
    st.markdown("---")
    st.markdown("### 📥 Araştırmacılar İçin Veri İndirme")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        # Export action history
        csv_actions = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📊 Eylem Geçmişi (CSV)",
            data=csv_actions,
            file_name=f"dental_tutor_actions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            type="primary",
            help="Tüm öğrenci eylemleri ve puanları"
        )
    
    with col_exp2:
        # Export detailed chat logs (for paper analysis)
        try:
            from db.database import SessionLocal, ChatLog, StudentSession
            
            db = SessionLocal()
            detailed_logs = []
            
            # Query ALL chat logs with session info (for pilot study - all students)
            logs = db.query(
                ChatLog.id,
                ChatLog.session_id,
                StudentSession.student_id,
                StudentSession.case_id,
                ChatLog.role,
                ChatLog.content,
                ChatLog.timestamp,
                ChatLog.metadata_json
            ).join(StudentSession).order_by(ChatLog.timestamp).all()
            
            for log in logs:
                log_dict = {
                    'chat_id': log[0],
                    'session_id': log[1],
                    'student_id': log[2],
                    'case_id': log[3],
                    'role': log[4],
                    'content': log[5][:200] + '...' if len(log[5]) > 200 else log[5],  # Truncate long messages
                    'timestamp': log[6].strftime('%Y-%m-%d %H:%M:%S') if log[6] else 'N/A'
                }
                
                # Extract metadata if available
                if log[7]:
                    metadata = log[7] if isinstance(log[7], dict) else json.loads(log[7])
                    log_dict['action'] = metadata.get('interpreted_action', '')
                    log_dict['score'] = metadata.get('assessment', {}).get('score', 0)
                    log_dict['clinically_accurate'] = metadata.get('silent_evaluation', {}).get('is_clinically_accurate', 'N/A')
                else:
                    log_dict['action'] = ''
                    log_dict['score'] = 0
                    log_dict['clinically_accurate'] = 'N/A'
                
                detailed_logs.append(log_dict)
            
            db.close()
            
            if detailed_logs:
                df_detailed = pd.DataFrame(detailed_logs)
                csv_detailed = df_detailed.to_csv(index=False, encoding='utf-8-sig')
                
                st.download_button(
                    label="📝 Detaylı Chat Logları (CSV)",
                    data=csv_detailed,
                    file_name=f"dental_tutor_chatlogs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    type="secondary",
                    help="Tam konuşma geçmişi ve değerlendirmeler"
                )
        except Exception as e:
            st.warning(f"Detaylı log export hatası: {e}")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Puan Trendi")
        
        if len(df) > 0:
            df['cumulative_score'] = df['score'].cumsum()
            
            fig = px.line(
                df, 
                y='cumulative_score',
                title='Kümülatif Puan',
                labels={'cumulative_score': 'Toplam Puan', 'index': 'Eylem Sırası'}
            )
            fig.update_traces(line_color='#667eea', line_width=3)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width='stretch')
    
    with col2:
        st.markdown("### 🎯 Vaka Dağılımı")
        
        case_counts = df['case_id'].value_counts()
        
        fig = px.pie(
            values=case_counts.values,
            names=case_counts.index,
            title='Vaka Başına Eylem Sayısı'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, width='stretch')
    
    st.markdown("---")
    
    # Score Distribution
    st.markdown("### 📊 Puan Dağılımı")
    
    fig = px.histogram(
        df, 
        x='score',
        nbins=20,
        title='Eylem Puanları Histogramı',
        labels={'score': 'Puan', 'count': 'Frekans'}
    )
    fig.update_traces(marker_color='#667eea')
    st.plotly_chart(fig, width='stretch')
    
    st.markdown("---")
    
    # Performance by Action Type
    if 'action' in df.columns:
        st.markdown("### 🔍 Eylem Tipine Göre Performans")
        
        action_stats = df.groupby('action').agg({
            'score': ['count', 'sum', 'mean']
        }).round(2)
        action_stats.columns = ['Kullanım Sayısı', 'Toplam Puan', 'Ortalama Puan']
        action_stats = action_stats.sort_values('Toplam Puan', ascending=False)
        
        st.dataframe(action_stats, width='stretch')

else:
    st.info("📭 Henüz eylem geçmişi bulunmuyor. Vaka çalışmasına başlamak için chat sayfasına gidin!")
    
    if st.button("💬 Vaka Çalışmasına Başla", type="primary"):
        st.switch_page("pages/chat.py")

st.markdown("---")

# Back to Home
if st.button("🏠 Ana Sayfaya Dön", width="stretch"):
    st.switch_page("pages/0_home.py")
