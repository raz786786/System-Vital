"""
Event Log Scout - Retrieves Windows Event Logs for AI analysis
"""

import win32evtlog
import win32evtlogutil
import win32con
from datetime import datetime
from typing import List, Dict

class EventLogScout:
    """Class to retrieve and filter Windows Event Logs"""
    
    def __init__(self):
        self.server = 'localhost'
        
    def get_recent_errors(self, log_type: str = "System", limit: int = 50) -> List[Dict]:
        """
        Retrieves the most recent Error/Critical events from a specific log
        log_type: "System" or "Application"
        """
        logs = []
        try:
            # Open the event log
            hand = win32evtlog.OpenEventLog(self.server, log_type)
            
            # Read flags: Backwards from latest, and seek based on record number
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            
            total = win32evtlog.GetNumberOfEventLogRecords(hand)
            
            count = 0
            while count < limit:
                events = win32evtlog.ReadEventLog(hand, flags, 0)
                if not events:
                    break
                
                for event in events:
                    # Filter for ERROR (1) and CRITICAL (even though 1 is usually enough)
                    # Event types: 1=Error, 2=Warning, 4=Info
                    if event.EventType == win32con.EVENTLOG_ERROR_TYPE:
                        msg = win32evtlogutil.SafeFormatMessage(event, log_type)
                        
                        logs.append({
                            'time': event.TimeGenerated.Format(),
                            'source': event.SourceName,
                            'event_id': event.EventID & 0xFFFF, # Mask to get friendly ID
                            'type': 'ERROR',
                            'message': msg
                        })
                        count += 1
                        if count >= limit:
                            break
                            
            win32evtlog.CloseEventLog(hand)
            
        except Exception as e:
            print(f"Error reading {log_type} logs: {e}")
            
        return logs

    def get_all_diagnostic_logs(self) -> Dict[str, List[Dict]]:
        """Fetch errors from both System and Application logs"""
        return {
            'system': self.get_recent_errors("System", 100),
            'application': self.get_recent_errors("Application", 100)
        }

if __name__ == "__main__":
    scout = EventLogScout()
    system_errors = scout.get_recent_errors("System", 5)
    for err in system_errors:
        print(f"[{err['time']}] {err['source']} (ID: {err['event_id']}): {err['message'][:100]}...")
