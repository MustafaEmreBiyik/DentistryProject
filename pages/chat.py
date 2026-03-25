"""
Silent Evaluator Chat Interface
================================
Clean messaging UI with background evaluation saving.
Students see ONLY the conversation - no scores or warnings during chat.
"""

import os
import sys
import json
import logging
import time
from typing import Optional, List, Tuple, Any, Dict
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from app.student_profile import init_student_profile
from app.frontend.components import render_sidebar, DEFAULT_MODEL
from db.database import SessionLocal, StudentSession, ChatLog, SystemMetricLog, init_db

# Initialize systems
init_student_profile()
init_db()

# Try optional imports
try:
    from app.agent import DentalEducationAgent
except Exception as e:
    DentalEducationAgent = None
    print(f"⚠️ DentalEducationAgent import error: {e}")

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ==================== DATABASE HELPERS ====================

def get_or_create_session(student_id: str, case_id: str) -> int:
    """
    Get existing session or create new one for student+case combination.
    ALWAYS returns the most recent session for this student+case.
    """
    db = SessionLocal()
    try:
        # Find the most recent session for this student+case
        existing = db.query(StudentSession).filter_by(
            student_id=student_id,
            case_id=case_id
        ).order_by(StudentSession.start_time.desc()).first()
        
        if existing:
            LOGGER.info(f"Reusing session {existing.id} for {student_id} on {case_id}")
            return existing.id
        
        # Create new session only if none exists
        new_session = StudentSession(
            student_id=student_id,
            case_id=case_id,
            current_score=0.0
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        LOGGER.info(f"Created new session {new_session.id} for {student_id} on {case_id}")
        return new_session.id
    except Exception as e:
        LOGGER.error(f"Session creation failed: {e}")
        db.rollback()
        return -1
    finally:
        db.close()


def save_message_to_db(
    session_id: int,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Save chat message to database with optional metadata.
    Updates session score if metadata contains assessment.
    
    Args:
        session_id: Database session ID
        role: 'user' or 'assistant'
        content: Message text
        metadata: Evaluation results (saved silently, not shown to user)
    """
    if session_id < 0:
        return False
    
    write_started = time.perf_counter()
    db = SessionLocal()
    try:
        # Save chat log
        chat_log = ChatLog(
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=metadata,
            timestamp=datetime.utcnow()
        )
        db.add(chat_log)
        
        # Update session score if this is an assistant message with assessment
        if role == "assistant" and metadata:
            assessment = metadata.get("assessment", {})
            action_score = assessment.get("score", 0)
            
            if action_score > 0:
                # Get current session and update cumulative score
                session = db.query(StudentSession).filter_by(id=session_id).first()
                if session:
                    session.current_score = (session.current_score or 0) + action_score
                    LOGGER.info(f"Updated session {session_id} score: +{action_score} -> {session.current_score}")
        
        db.commit()
        write_ms = round((time.perf_counter() - write_started) * 1000, 2)
        save_system_metric(
            metric_name="db_write_latency_ms",
            metric_value=write_ms,
            status="success",
            session_id=session_id,
            metadata={"role": role}
        )
        return True
    except Exception as e:
        write_ms = round((time.perf_counter() - write_started) * 1000, 2)
        save_system_metric(
            metric_name="db_write_latency_ms",
            metric_value=write_ms,
            status="failed",
            session_id=session_id,
            metadata={"role": role, "error": str(e)}
        )
        LOGGER.error(f"Failed to save message: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def save_system_metric(
    metric_name: str,
    metric_value: Optional[float] = None,
    status: Optional[str] = None,
    session_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist one operational metric event for pilot telemetry."""
    db = SessionLocal()
    try:
        metric_log = SystemMetricLog(
            session_id=session_id,
            metric_name=metric_name,
            metric_value=metric_value,
            status=status,
            metadata_json=metadata or {},
            timestamp=datetime.utcnow(),
        )
        db.add(metric_log)
        db.commit()
    except Exception as e:
        # Metric logging must never break chat flow.
        LOGGER.warning(f"Metric log write failed for {metric_name}: {e}")
        db.rollback()
    finally:
        db.close()


def is_task_completion_action(interpreted_action: str) -> bool:
    """Treat diagnosis actions as task-completion milestones."""
    return isinstance(interpreted_action, str) and interpreted_action.startswith("diagnose_")


def has_reasoning_deviation(silent_evaluation: Dict[str, Any]) -> bool:
    """Deviation signal from Shadow/Silent evaluator output."""
    if not isinstance(silent_evaluation, dict) or not silent_evaluation:
        return False

    is_accurate = silent_evaluation.get("is_clinically_accurate")
    has_safety_violation = bool(silent_evaluation.get("safety_violation"))
    missing_info = silent_evaluation.get("missing_critical_info")
    has_missing_info = isinstance(missing_info, list) and len(missing_info) > 0

    return (is_accurate is False) or has_safety_violation or has_missing_info


# ==================== MAIN INTERFACE ====================

def main() -> None:
    st.set_page_config(
        page_title="Oral Patoloji Sohbet",
        page_icon="💬",
        layout="centered"
    )
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # ==================== SIDEBAR ====================
    def reset_chat():
        """Callback to reset chat state"""
        st.session_state.messages = []
        st.session_state.db_session_id = None
        st.rerun()
    
    # Render reusable sidebar
    sidebar_data = render_sidebar(
        page_type="chat",
        show_case_selector=True,
        show_model_selector=True,
        custom_actions={
            "🔄 Yeni Sohbet": reset_chat
        }
    )

    # ==================== CHAT AREA ====================
    st.title("💬 Oral Patoloji Sohbet")
    st.caption("Eğitimsel bir konuşma deneyimi")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Merhaba! Size nasıl yardımcı olabilirim?"
            }
        ]
    
    # Initialize or get database session
    # CRITICAL: Always verify session exists for current case
    profile = st.session_state.get("student_profile") or {}
    student_id = profile.get("student_id", "web_user_default")
    
    # Check if we need to refresh session ID
    need_new_session = (
        "db_session_id" not in st.session_state or 
        st.session_state.db_session_id is None or
        st.session_state.db_session_id < 0
    )
    
    if need_new_session:
        st.session_state.db_session_id = get_or_create_session(
            student_id=student_id,
            case_id=st.session_state.current_case_id
        )
        LOGGER.info(f"Session initialized: {st.session_state.db_session_id} for case {st.session_state.current_case_id}")

    # Initialize agent
    agent_instance = None
    if DentalEducationAgent and GEMINI_API_KEY:
        try:
            # Use selected model from session state
            selected_model = st.session_state.get("selected_model", DEFAULT_MODEL)
            agent_instance = DentalEducationAgent(
                api_key=GEMINI_API_KEY,
                model_name=selected_model
            )
        except Exception as e:
            LOGGER.error(f"Agent initialization failed: {e}")
            st.error("⚠️ Sistem başlatılamadı. Lütfen yöneticinize başvurun.")
            st.stop()
    else:
        st.error("❌ Agent veya API key mevcut değil.")
        st.stop()

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ==================== USER INPUT ====================
    if user_input := st.chat_input("Mesajınızı yazın..."):
        # Display user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Save user message to DB (no metadata for user messages)
        save_message_to_db(
            session_id=st.session_state.db_session_id,
            role="user",
            content=user_input,
            metadata=None
        )

        # Process with agent
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("✍️ Düşünüyor...")

            try:
                api_started = time.perf_counter()
                # Update agent state with current case
                profile = st.session_state.get("student_profile") or {}
                student_id = profile.get("student_id", "web_user_default")
                
                # Process input through agent
                result = agent_instance.process_student_input(
                    student_id=student_id,
                    raw_action=user_input,
                    case_id=st.session_state.current_case_id
                )
                api_response_ms = round((time.perf_counter() - api_started) * 1000, 2)
                
                # Extract response text
                response_text = result.get("llm_interpretation", {}).get("explanatory_feedback", "")
                
                if not response_text:
                    response_text = "Üzgünüm, şu anda yanıt veremiyorum."
                
                # Display ONLY the conversation text (no scores, no warnings)
                placeholder.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # ==================== SILENT SAVE ====================
                # Save evaluation to database WITHOUT showing it to the user
                interpreted_action_for_log = (
                    result.get("scoring_action")
                    or result.get("scoring_interpretation", {}).get("interpreted_action")
                    or result.get("llm_interpretation", {}).get("interpreted_action")
                )

                evaluation_metadata = {
                    "interpreted_action": interpreted_action_for_log,
                    "assessment": result.get("assessment", {}),
                    "silent_evaluation": result.get("silent_evaluation", {}),
                    "api_response_time_ms": api_response_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                    "case_id": st.session_state.current_case_id
                }
                
                save_message_to_db(
                    session_id=st.session_state.db_session_id,
                    role="assistant",
                    content=response_text,
                    metadata=evaluation_metadata
                )

                save_system_metric(
                    metric_name="api_response_time_ms",
                    metric_value=api_response_ms,
                    status="success",
                    session_id=st.session_state.db_session_id,
                    metadata={
                        "case_id": st.session_state.current_case_id,
                        "interpreted_action": interpreted_action_for_log,
                    },
                )

                if is_task_completion_action(interpreted_action_for_log or ""):
                    save_system_metric(
                        metric_name="task_completion_event",
                        metric_value=1.0,
                        status="completed",
                        session_id=st.session_state.db_session_id,
                        metadata={
                            "case_id": st.session_state.current_case_id,
                            "action": interpreted_action_for_log,
                        },
                    )

                deviation = has_reasoning_deviation(result.get("silent_evaluation", {}))
                save_system_metric(
                    metric_name="reasoning_deviation",
                    metric_value=1.0 if deviation else 0.0,
                    status="deviation" if deviation else "aligned",
                    session_id=st.session_state.db_session_id,
                    metadata={
                        "case_id": st.session_state.current_case_id,
                        "action": interpreted_action_for_log,
                    },
                )
                
                # Log silently (for admin/debug purposes only)
                LOGGER.info(
                    f"[Silent Eval] Action: {evaluation_metadata['interpreted_action']}, "
                    f"Accurate: {evaluation_metadata['silent_evaluation'].get('is_clinically_accurate', 'N/A')}"
                )

            except Exception as e:
                api_elapsed_ms = round((time.perf_counter() - api_started) * 1000, 2)
                save_system_metric(
                    metric_name="api_response_time_ms",
                    metric_value=api_elapsed_ms,
                    status="failed",
                    session_id=st.session_state.get("db_session_id"),
                    metadata={
                        "case_id": st.session_state.get("current_case_id"),
                        "error": str(e),
                    },
                )
                LOGGER.exception(f"Chat processing failed: {e}")
                error_text = "⚠️ Bir hata oluştu. Lütfen tekrar deneyin."
                placeholder.markdown(error_text)
                st.session_state.messages.append({"role": "assistant", "content": error_text})

    # ==================== FEEDBACK COLLECTION ====================
    # Show feedback form after meaningful conversation (10+ messages)
    if len(st.session_state.messages) >= 10:
        if "feedback_submitted" not in st.session_state or not st.session_state.feedback_submitted:
            st.divider()
            st.markdown("### 📝 Oturumu Değerlendirin")
            st.caption("Geri bildiriminiz araştırmamız için çok değerlidir.")
            
            with st.form("feedback_form", clear_on_submit=True):
                col_rating, col_comment = st.columns([1, 2])
                
                with col_rating:
                    rating = st.slider(
                        "Genel Memnuniyet",
                        min_value=1,
                        max_value=5,
                        value=3,
                        help="1 = Çok Kötü, 5 = Mükemmel"
                    )
                    st.caption("⭐" * rating)
                
                with col_comment:
                    comment = st.text_area(
                        "Yorumlarınız (Opsiyonel)",
                        placeholder="Bu deneyim hakkında düşüncelerinizi paylaşın...",
                        height=100
                    )
                
                submitted = st.form_submit_button("📤 Gönder", type="primary")
                
                if submitted:
                    # Save feedback to database
                    db = SessionLocal()
                    try:
                        from db.database import FeedbackLog
                        
                        feedback = FeedbackLog(
                            session_id=st.session_state.db_session_id,
                            rating=rating,
                            comment=comment if comment.strip() else None,
                            timestamp=datetime.utcnow()
                        )
                        db.add(feedback)
                        db.commit()
                        
                        st.session_state.feedback_submitted = True
                        st.success("✅ Teşekkürler! Geri bildiriminiz kaydedildi. 🎉")
                        st.balloons()
                        
                        LOGGER.info(f"Feedback saved: Session {st.session_state.db_session_id}, Rating: {rating}")
                    except Exception as e:
                        LOGGER.error(f"Failed to save feedback: {e}")
                        st.error("⚠️ Geri bildirim kaydedilemedi.")
                        db.rollback()
                    finally:
                        db.close()


if __name__ == "__main__":
    main()
