"""Phase 1 - Detect: which chat vendor a brand runs, and whether it is AI or human.

Public surface:
  SignatureDetector - fetch a homepage and classify it (vendor + kind)
  signatures        - the 62-vendor fingerprint library + match_html()
"""
from . import signatures
from .detector import SignatureDetector

__all__ = ["signatures", "SignatureDetector"]
