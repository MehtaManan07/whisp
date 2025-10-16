"""
Script to update existing users' timezones based on their phone numbers.

This is useful for backfilling timezone data for users created before
the timezone field was added.

Usage:
    python scripts/update_user_timezones.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db.engine import get_db_util
from app.modules.users.service import UsersService
from app.utils.timezone_detection import detect_timezone_from_phone, get_timezone_display_name


async def update_all_user_timezones():
    """Update timezones for all users based on their phone numbers."""
    users_service = UsersService()
    
    async for db in get_db_util():
        print("🔍 Fetching all users...")
        users = await users_service.get_all_users(db, limit=1000)
        
        if not users:
            print("No users found.")
            return
        
        print(f"Found {len(users)} users. Updating timezones...\n")
        
        updated_count = 0
        skipped_count = 0
        
        for user in users:
            # Skip if user already has a non-UTC timezone
            if user.timezone and user.timezone != "UTC":
                print(f"⏭️  Skipping user {user.id} - already has timezone: {user.timezone}")
                skipped_count += 1
                continue
            
            # Skip if no phone number
            if not user.phone_number:
                print(f"⏭️  Skipping user {user.id} - no phone number")
                skipped_count += 1
                continue
            
            # Detect timezone
            detected_tz = detect_timezone_from_phone(user.phone_number)
            
            if detected_tz == "UTC":
                print(f"⚠️  Could not detect timezone for user {user.id} (phone: {user.phone_number})")
                skipped_count += 1
                continue
            
            # Update timezone
            try:
                await users_service.update_user_timezone(db, user.id, detected_tz)
                tz_display = get_timezone_display_name(detected_tz)
                print(f"✅ Updated user {user.id} ({user.phone_number}) → {tz_display}")
                updated_count += 1
            except Exception as e:
                print(f"❌ Error updating user {user.id}: {e}")
        
        print(f"\n📊 Summary:")
        print(f"   Updated: {updated_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Total: {len(users)}")


if __name__ == "__main__":
    print("🌍 User Timezone Update Script")
    print("=" * 50)
    asyncio.run(update_all_user_timezones())
    print("\n✨ Done!")

