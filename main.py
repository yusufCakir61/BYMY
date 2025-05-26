import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import multiprocessing
from config.config_handler import load_config
from discovery.discovery_process import run_discovery_process
from network.network_process import run_network_process
from cli.cli_process import run_cli

if __name__ == "__main__":
    manager = multiprocessing.Manager()
    known_users = manager.dict()

    config = load_config()

    p1 = multiprocessing.Process(target=run_discovery_process, args=(config["whoisport"],))
    p2 = multiprocessing.Process(target=run_network_process, args=(known_users,))

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
