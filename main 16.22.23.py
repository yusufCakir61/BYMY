import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import multiprocessing
from config_handler import load_config
from discovery_process import run_discovery_process
from network_process import run_network_process
from cli_process import run_cli

if __name__ == "__main__":
    manager = multiprocessing.Manager()
    known_users = manager.dict()
    image_events = manager.list()

    config = load_config()
    config["image_events"] = image_events

    p1 = multiprocessing.Process(target=run_discovery_process, args=(config["whoisport"],))
    p2 = multiprocessing.Process(target=run_network_process, args=(known_users, config))

    p1.start()
    p2.start()

    try:
        run_cli(config, known_users)
    except KeyboardInterrupt:
        print("🛑 Beende Chat.")

    p1.terminate()
    p2.terminate()
    p1.join()
    p2.join()
