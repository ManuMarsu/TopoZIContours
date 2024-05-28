import cv2
import numpy as np
from osgeo import gdal


def apply_convolution_opencv(input_raster_path, output_raster_path, kernel):
    ds = gdal.Open(input_raster_path, gdal.GA_ReadOnly)
    
    # Lecture du raster dans un array numpy
    raster_array = ds.GetRasterBand(1).ReadAsArray()
    
    # Conversion en un format qui convient à OpenCV
    raster_float = raster_array.astype(np.float32)
    
    # Convolution avec OpenCV
    convolved_array = cv2.filter2D(raster_float, -1, kernel)
    
    # Sauvegarde du résultat dans un nouveau raster
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(output_raster_path, ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Float32)
    out_ds.SetProjection(ds.GetProjection())
    out_ds.SetGeoTransform(ds.GetGeoTransform())
    out_ds.GetRasterBand(1).WriteArray(convolved_array)
    out_ds.FlushCache()
    
    ds = None
    out_ds = None

def generate_gaussian_kernel(size, sigma):
    # Créez un espace linéaire pour générer le noyau bidimensionnel
    ax = np.linspace(-(size // 2), (size // 2), size)
    xx, yy = np.meshgrid(ax, ax)

    # Formule pour le noyau gaussien 2D
    kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    kernel = kernel / kernel.sum()
    
    return kernel


# taille = 25
# gaussian_kernel = generate_gaussian_kernel(taille, 2)
# i = 1
# for sigma in range(25, 70, 5):
#     gaussian_kernel += generate_gaussian_kernel(taille, (sigma / 10))
#     i += 1
# gaussian_kernel = gaussian_kernel / i
# input_path = "ValleeOurceLIDAR.tif"
# output_path = f"ValleeOurceLIDAR_filtre_openCV_int_{taille}_{taille}_{sigma}.tif"

# apply_convolution_opencv(input_path, output_path, gaussian_kernel)

'''
# Exemple d'utilisation :
for taille in [15, 20, 25, 30, 35, 40]:
    for sigma in range(2, 7):
        gaussian_kernel = generate_gaussian_kernel(taille, sigma)

        input_path = "ValleeOurceLIDAR.tif"
        output_path = f"ValleeOurceLIDAR_filtre_openCV_{taille}_{taille}_{sigma}.tif"

        apply_convolution_opencv(input_path, output_path, gaussian_kernel)
'''

# Exemple d'utilisation :
# Pour le filtrage MNT : taille 25 sigma 6
# Pour le filtrage hauteurs d'eau : taille 7 sigma 5
for taille in [25]:
    for sigma in [6]:
        gaussian_kernel = generate_gaussian_kernel(taille, sigma)

        input_path = "Lidar_Ource_ReleveExtremites.tif"
        output_path = f"Lidar_Ource_ReleveExtremites_{taille}_{taille}_{sigma}.tif"

        apply_convolution_opencv(input_path, output_path, gaussian_kernel)