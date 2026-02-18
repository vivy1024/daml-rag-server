#!/usr/bin/env python3
import os
print(f"ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not_set')}")
print(f"DEBUG: {os.getenv('DEBUG', 'not_set')}")
