import numpy as np

data = np.fromfile("gps_z_jammerem.bin", dtype=np.int8)
data_u8 = (data.astype(np.int16) + 128).astype(np.uint8)
data_u8.tofile("gps_z_jammerem_uint8.bin")
