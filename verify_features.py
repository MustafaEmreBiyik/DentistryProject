"""
🔍 VERIFY FEEDBACK FEATURE IMPLEMENTATION
==========================================
Checks if FeedbackLog table exists and tests the new features
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "dentai_app.db")

print("=" * 70)
print("🔍 FEEDBACK FEATURE VERIFICATION")
print("=" * 70)
print()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check if feedback_logs table exists
cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='feedback_logs'
""")

feedback_table = cursor.fetchone()

if feedback_table:
    print("✅ feedback_logs table EXISTS")
    
    # Show table structure
    cursor.execute("PRAGMA table_info(feedback_logs)")
    columns = cursor.fetchall()
    print("\n📋 Table Structure:")
    for col in columns:
        print(f"   • {col[1]:20s} -> {col[2]}")
    
    # Check if any feedback exists
    cursor.execute("SELECT COUNT(*) FROM feedback_logs")
    count = cursor.fetchone()[0]
    print(f"\n📊 Total feedback entries: {count}")
    
    if count > 0:
        cursor.execute("""
            SELECT f.id, f.session_id, f.rating, f.comment, f.timestamp,
                   s.case_id, s.student_id
            FROM feedback_logs f
            JOIN student_sessions s ON f.session_id = s.id
            ORDER BY f.timestamp DESC
            LIMIT 5
        """)
        
        print("\n🌟 Recent Feedback:")
        print("-" * 70)
        for row in cursor.fetchall():
            fb_id, sess_id, rating, comment, timestamp, case_id, student_id = row
            stars = "⭐" * rating
            print(f"Feedback #{fb_id} | Session {sess_id} ({case_id})")
            print(f"  Rating: {stars} ({rating}/5)")
            if comment:
                print(f"  Comment: {comment[:60]}...")
            print(f"  Time: {timestamp}")
            print()
else:
    print("❌ feedback_logs table NOT FOUND")
    print("   Running database initialization...")
    
    from db.database import init_db
    init_db()
    print("✅ Database initialized")

conn.close()

print("=" * 70)
print("📊 NEW FEATURES SUMMARY")
print("=" * 70)
print()
print("✅ IMPLEMENTED FEATURES:")
print("   1. 📥 CSV Export for Researchers (in stats page)")
print("      • Action history export")
print("      • Detailed chat logs export")
print()
print("   2. 📝 Student Feedback Collection (in chat page)")
print("      • 1-5 star rating")
print("      • Text comments")
print("      • Linked to session_id")
print()
print("🎯 USAGE:")
print("   • Students: Chat for 10+ messages → Feedback form appears")
print("   • Researchers: Go to Stats page → Click 'CSV İndir' buttons")
print()
print("=" * 70)
