import numpy as np

data = np.fromfile("jammed.bin", dtype=np.int8)
data_u8 = (data.astype(np.int16) + 128).astype(np.uint8)
data_u8.tofile("jammed_uint8.bin")
