Fixed that when errors happen in 'WBEMListener.start()', the callback thread
is cleaned up in all cases. This also fixes long wait times for certain
test cases in the listener unit test.
