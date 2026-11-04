"""Create the demo administrator through the same seed path.

The previous hard-coded password has been removed. Export ADMIN_PASSWORD
and MEMBER_PASSWORD, then run this script from the backend directory.
"""
from seed_demo import main

if __name__ == "__main__":
    main()
