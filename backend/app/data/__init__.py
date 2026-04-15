"""FlowMind AI -- Data Layer Package.

Contains database clients and data generators:

    * ``firebase_client`` -- Firebase RTDB wrapper with in-memory mock
      fallback and async connection pooling.
    * ``mock_generator`` -- Time-varying stadium crowd data generator
      with cache and background refresh.
"""
