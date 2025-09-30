Fixed long wait times when errors happened in the WBEMListener startup, by
cleaning up the callback thread when exceptions are raised.
