import argparse
import logging
import sys
from src.utils.publish_manager import PublishManager
from src.utils.logging_config import setup_logging

def main():
    parser = argparse.ArgumentParser(description="Sanitize and publish traderBot repo.")
    parser.add_argument("--mode", choices=["incremental", "full"], default="incremental",
                        help="Publication mode (default: incremental)")
    parser.add_argument("--msg", help="Commit message for the update")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    try:
        manager = PublishManager()
        manager.run_publish(mode=args.mode, commit_msg=args.msg)
    except Exception as e:
        logging.error("Publication failed: %s", e)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
