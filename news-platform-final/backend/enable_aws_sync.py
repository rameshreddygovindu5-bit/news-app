#!/usr/bin/env python3
"""
Enable AWS sync in configuration
"""
import os
from pathlib import Path

def enable_aws_sync():
    """Update .env to enable AWS sync"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found. Please copy .env.example to .env first.")
        return False
    
    # Read current .env
    lines = env_file.read_text(encoding='utf-8').splitlines()
    
    # Update relevant lines
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('SCHEDULE_AWS_SYNC_ENABLED='):
            lines[i] = 'SCHEDULE_AWS_SYNC_ENABLED=true'
            updated = True
        elif line.startswith('IS_LOCAL_DEV='):
            lines[i] = 'IS_LOCAL_DEV=true'
            updated = True
        elif line.startswith('SCHEDULE_AWS_SYNC_MINUTES='):
            lines[i] = 'SCHEDULE_AWS_SYNC_MINUTES=*/5'
            updated = True
    
    # Add missing lines if not present
    if not any('SCHEDULE_AWS_SYNC_ENABLED=' in line for line in lines):
        lines.append('SCHEDULE_AWS_SYNC_ENABLED=true')
        updated = True
    if not any('IS_LOCAL_DEV=' in line for line in lines):
        lines.append('IS_LOCAL_DEV=true')
        updated = True
    if not any('SCHEDULE_AWS_SYNC_MINUTES=' in line for line in lines):
        lines.append('SCHEDULE_AWS_SYNC_MINUTES=*/5')
        updated = True
    
    if updated:
        env_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print("✅ AWS sync enabled in .env")
        print("   - IS_LOCAL_DEV=true")
        print("   - SCHEDULE_AWS_SYNC_ENABLED=true") 
        print("   - SCHEDULE_AWS_SYNC_MINUTES=*/5")
        print("\n⚠️  Make sure AWS_DB_* variables are set in .env")
        return True
    else:
        print("✅ AWS sync already enabled")
        return True

if __name__ == "__main__":
    enable_aws_sync()
