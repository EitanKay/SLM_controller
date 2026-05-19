import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# Load the raw 16-bit TIF
img = Image.open('output/camera_c  apture_43690.tif')
img_array = np.array(img)

# Display ignoring the 65,535 limit, bounded to the actual data max
plt.imshow(img_array, cmap='gray', vmin=img_array.min(), vmax=img_array.max())
plt.colorbar() # shows you the actual pixel intensity numbers next to it
plt.show() 