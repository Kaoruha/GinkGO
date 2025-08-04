#!/usr/bin/env python3
"""
Manual Data Worker Starter - Debug Script
This script allows you to manually start a data worker in the foreground for debugging purposes.
"""

def main():
    """Start a data worker manually in the foreground"""
    print("Starting Ginkgo Data Worker manually...")
    print("This will run the worker in the foreground for debugging.")
    print("Press Ctrl+C to stop the worker.")
    
    try:
        # Import the threading manager
        from ginkgo.libs.core.threading import GinkgoThreadManager
        
        # Create thread manager instance
        gtm = GinkgoThreadManager()
        
        print(f"Current worker count: {gtm.get_worker_count()}")
        print("Starting data worker process...")
        
        # Start the data worker in foreground (this will block)
        gtm.run_data_worker()
        
    except KeyboardInterrupt:
        print("\nReceived Ctrl+C, stopping worker...")
    except Exception as e:
        print(f"Error starting worker: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Worker stopped.")

if __name__ == "__main__":
    main()