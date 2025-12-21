"""
Iceberg Terminal entry point.

Run with: python -m iceberg
"""

import sys
from .app import IcebergApp
from .config import Config


def main():
    """Launch the Iceberg terminal"""
    try:
        # Load configuration
        config = Config.load()

        # Create and run app
        app = IcebergApp(config=config)
        app.run()

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(
            "\nMake sure the StockStreet database and CSV files exist:",
            file=sys.stderr,
        )
        print("  - ../StockStreet/Data/stockstreet.sqlite", file=sys.stderr)
        print("  - ../StockStreet/Data/nasdaq100.csv", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
