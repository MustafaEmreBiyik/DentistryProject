"""
🕵️‍♂️ CASE SWITCH BUG FIX VERIFICATION SCRIPT
============================================
Checks if different cases create different session IDs
"""

import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "dentai_app.db")

print("=" * 70)
print("🔍 CASE SWITCH BUG FIX VERIFICATION")
print("=" * 70)
print(f"📁 Database: {DB_PATH}")
print()

# Connect to database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get table info
print("📋 TABLE STRUCTURE:")
cursor.execute("PRAGMA table_info(student_sessions)")
columns = cursor.fetchall()
for col in columns:
    print(f"   • {col[1]:20s} -> {col[2]}")
print()

# Fetch LAST 5 sessions (most recent test data)
print("=" * 70)
print("📊 LAST 5 SESSIONS (MOST RECENT FIRST):")
print("=" * 70)

cursor.execute("""
    SELECT id, student_id, case_id, current_score, start_time
    FROM student_sessions
    ORDER BY id DESC
    LIMIT 5
""")

sessions = cursor.fetchall()

if not sessions:
    print("❌ NO SESSIONS FOUND IN DATABASE")
    conn.close()
    exit(1)

print(f"{'ID':<5} {'Student ID':<20} {'Case ID':<25} {'Score':<8} {'Start Time'}")
print("-" * 70)

for session in sessions:
    session_id, student_id, case_id, score, start_time = session
    print(f"{session_id:<5} {student_id:<20} {case_id:<25} {score:<8} {start_time}")

print()
print("=" * 70)
print("🔬 ANALYSIS:")
print("=" * 70)

# Extract unique case IDs from last 5 sessions
unique_cases = list(set([s[2] for s in sessions]))
print(f"✓ Unique case_id values found: {len(unique_cases)}")
for case in unique_cases:
    print(f"  • {case}")
print()

# Check if different cases have different session IDs
if len(sessions) >= 2:
    last_two = sessions[:2]  # Most recent 2 sessions
    
    session1_id, _, case1_id, _, time1 = last_two[0]
    session2_id, _, case2_id, _, time2 = last_two[1]
    
    print(f"🔎 LAST TWO SESSIONS:")
    print(f"   Session #{session1_id} → Case: {case1_id}")
    print(f"   Session #{session2_id} → Case: {case2_id}")
    print()
    
    if case1_id != case2_id:
        # Different cases
        if session1_id != session2_id:
            print("✅ ✅ ✅ CONFIRMED: FIX IS WORKING!")
            print(f"   Different cases ({case1_id} vs {case2_id}) have DIFFERENT session IDs")
            print(f"   ({session1_id} vs {session2_id})")
            print()
            print("   🎉 DATA INTEGRITY PRESERVED - READY FOR PILOT!")
            verdict = "PASS"
        else:
            print("❌ ❌ ❌ FAILED: BUG STILL EXISTS!")
            print(f"   Different cases ({case1_id} vs {case2_id}) share SAME session ID ({session1_id})")
            print()
            print("   ⚠️ DATA CORRUPTION RISK - DO NOT DEPLOY!")
            verdict = "FAIL"
    else:
        # Same case
        print("ℹ️  Last two sessions are for the SAME case.")
        print("   Cannot verify fix from this data.")
        print()
        print("   📝 RECOMMENDATION: Test by switching to a different case and sending a message.")
        verdict = "INCONCLUSIVE"
else:
    print("⚠️  Only 1 session found. Need at least 2 sessions to verify.")
    verdict = "INCONCLUSIVE"

# Check chat logs for context
print()
print("=" * 70)
print("💬 RECENT CHAT ACTIVITY (Last 3 messages):")
print("=" * 70)

cursor.execute("""
    SELECT cl.session_id, ss.case_id, cl.role, cl.content, cl.timestamp
    FROM chat_logs cl
    JOIN student_sessions ss ON cl.session_id = ss.id
    ORDER BY cl.id DESC
    LIMIT 3
""")

chats = cursor.fetchall()
for chat in chats:
    session_id, case_id, role, content_preview, timestamp = chat
    content_short = content_preview[:50] + "..." if len(content_preview) > 50 else content_preview
    print(f"Session #{session_id} ({case_id})")
    print(f"  [{role}]: {content_short}")
    print(f"  @ {timestamp}")
    print()

conn.close()

print("=" * 70)
print(f"FINAL VERDICT: {verdict}")
print("=" * 70)
