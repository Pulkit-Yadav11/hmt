"""
run_local.py — Run the checker on your PC in a loop with desktop popups.
Use this if you want real-time alerts ON YOUR MACHINE without GitHub Actions.

Run:  python run_local.py
Stop: Ctrl+C
"""

import time
import subprocess
import sys

CHECK_INTERVAL_MINUTES = 10  # how often to check


def main():
    print(f"HMT Stock Bot — checking every {CHECK_INTERVAL_MINUTES} minutes")
    print("Press Ctrl+C to stop\n")

    while True:
        try:
            subprocess.run([sys.executable, "checker.py"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Checker error: {e}")
        except KeyboardInterrupt:
            print("\nStopped by user.")
            break

        print(f"\nSleeping {CHECK_INTERVAL_MINUTES} min…\n")
        try:
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("\nStopped by user.")
            break


if __name__ == "__main__":
    main()
