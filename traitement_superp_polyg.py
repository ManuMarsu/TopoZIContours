from osgeo import gdal, ogr, osr
import os
import numpy as np

def cpte_parents(arbre, id):
    if id not in arbre.keys():
        return 0
    else:
        cpte = 0
        for parent in arbre[id]:
            cpte += 1 + cpte_parents(arbre, parent)
        return cpte

######################### PARAMETRES #########################
fichier = "CN_T5_polyg_lisse_simpl_valide"

##############################################################


# Ouverture du gpkg contenant les polygones de niveau
ds0 = ogr.Open(f"{fichier}.gpkg", 0) # Ouverture en mode lecture seule
if ds0 is None:
    print("Impossible d'ouvrir le fichier " + fichier)
    exit(1)
lyr0 = ds0.GetLayer()

# Création d'une nouvelle couche qui contiendra uniquement les polygones de niveau dont le champ ELEV est strictement supérieur à 0 et dont la surface est supérieure à 50 m²
driver = ogr.GetDriverByName('GPKG')
ds = driver.CreateDataSource(f'{fichier}_temp.gpkg')
lyr = ds.CreateLayer(f'{fichier}_temp_etape1', geom_type=lyr0.GetGeomType(), srs=lyr0.GetSpatialRef())
# Add fields
for i in range(lyr0.GetLayerDefn().GetFieldCount()):
    lyr.CreateField(lyr0.GetLayerDefn().GetFieldDefn(i))

# On parcours les entités et on supprime les entités pour lesquelles soit le champ ELEV est strictement inférieur à 0, soit la surface du polygone est inférieure à 50 m²
for ent0 in lyr0:
    try:
        if ent0.GetField("ELEV") >= 0 and ent0.GetGeometryRef().Area() >= 50:
            lyr.CreateFeature(ent0)
    except:
        print(f"Erreur pour l'entité {ent0.GetFID()}")
print(f"Suppression effectuée des entités pour lesquelles le champ ELEV est strictement inférieur à 0 ou la surface du polygone est inférieure à 50 m²")

# Ajout d'un champ "Surface" contenant la surface de chaque entité
lyr.ResetReading()
lyr.CreateField(ogr.FieldDefn("Surface", ogr.OFTReal))
for ent in lyr:
    geom = ent.GetGeometryRef()
    geom_area = geom.Area()
    ent.SetField("Surface", geom_area)
    lyr.SetFeature(ent)

# On parcours les entités (dans le sens des surfaces croissantes) dont le champ ELEV vaut 0 ; pour chacune de ces entités, on reparcours (dans le sens des surfaces croissantes) les entités restantes (dont le champ ELEV est égal à 0) et si une de ces entités contient l'entité en cours de traitement, on crée un trou dans 
# l'entité trouvé selon les limites de l'entité en cours de traitement

# On commence par trier les entités par ordre croissant de surface
lyr.ResetReading()
entites = {}
for ent in lyr:
    # Récupération de la valeur du champ ELEV
    elev = ent.GetField("ELEV")
    if elev in entites.keys():
        entites[elev].append(ent)
    else:
        entites[elev] = [ent]
    entites[elev].append(ent)
for elev in entites.keys():
    entites[elev] = sorted(entites[elev], key=lambda x: x.GetField("Surface"))

# Initialisation de l'arbre de comptage des inclusions
arbre = {}

lyr.ResetReading()
for elev in entites.keys():
    for ent in entites[elev]:
        # On vérifie que la géométrie soit valide, et sinon on passe à l'entité suivante
        if ent.GetGeometryRef().IsValid() == False:
            continue
        geom = ent.GetGeometryRef()
        for ent2 in entites[elev]:
            if ent2.GetFID() != ent.GetFID():
                geom2 = ent2.GetGeometryRef()
                # On vérifie que la géométrie soit valide, et sinon on passe à l'entité suivante
                if geom2.IsValid() == False:
                    continue
                if geom2.Contains(geom):
                    geom3 = geom2.Difference(geom)
                    ent2.SetGeometry(geom3)
                    lyr.SetFeature(ent2)
                    id_out = ent2.GetFID()
                    id_in = ent.GetFID()
                    print(f"Trou correspondant à l'entité {str(id_in)} créé dans l'entité {str(id_out)}")
                    
                    if id_in in arbre.keys():
                        arbre[id_in].append(id_out)
                    else:
                        arbre[id_in] = [id_out]

# Ajout d'un champ "ASupprimer" contenant le nombre d'inclusions de chaque entité dans des entités supra
lyr.ResetReading()
lyr.CreateField(ogr.FieldDefn("NombreInclusions", ogr.OFTReal))
for ent in lyr:
    cpte_inclusion = 0 
    try:
        cpte_inclusion = len(arbre[ent.GetFID()]) if ent.GetFID() in arbre.keys() else 0
    except:
        print(f"Erreur pour l'entité {ent.GetFID()}")
    ent.SetField("NombreInclusions", cpte_inclusion)
    lyr.SetFeature(ent)
print(f"Identification effectuée des entités incluses dans d'autres entités")

# Create a new layer with the same definition as the original layer
lyr2 = ds.CreateLayer(f'{fichier}_temp_etape2', geom_type=lyr.GetGeomType(), srs=lyr.GetSpatialRef())
# Add fields
for i in range(lyr.GetLayerDefn().GetFieldCount()):
    lyr2.CreateField(lyr.GetLayerDefn().GetFieldDefn(i))

# Loop over the features in the original layer
lyr.ResetReading()
for feat in lyr:
    # If the feature is marked for deletion, skip it
    if feat.GetFID() in arbre.keys() and len(arbre[feat.GetFID()]) % 2 == 1:
        print(f"Entité in : {feat.GetFID()} - Entités out : {str(arbre[feat.GetFID()])} - Cptes entité in : {str([cpte_parents(arbre, arbre[feat.GetFID()][i]) for i in range(len(arbre[feat.GetFID()]))])}")
    else:
    # Otherwise, add it to the new layer
        lyr2.CreateFeature(feat)
print(f"Suppression effectuée des entités incluses un nombre impair de fois dans d'autres entités")

ds3 = driver.CreateDataSource(f'{fichier}_resultat.gpkg')
lyr3 = ds3.CreateLayer(f'{fichier}_resultat', geom_type=ogr.wkbMultiPolygon, srs=lyr.GetSpatialRef())
# Add fields
for i in range(lyr2.GetLayerDefn().GetFieldCount()):
    lyr3.CreateField(lyr2.GetLayerDefn().GetFieldDefn(i))


elev = {}
lst_elev = []
# On fusionne les entités avec le même attribut ELEV
lyr2.ResetReading()
for feat2 in lyr2:
    if feat2.GetField("ELEV") not in elev.keys():
        elev[feat2.GetField("ELEV")] = feat2
        lst_elev.append(feat2.GetField("ELEV"))
        lyr3.CreateFeature(feat2)
        lyr3.ResetReading()
        for feat3 in lyr3:
            if feat3.GetField("ELEV") == feat2.GetField("ELEV"):
                elev[feat2.GetField("ELEV")] = feat3
    else:
        # Sinon, on fusionne les géométries
        geom2 = feat2.GetGeometryRef()
        geom3 = elev[feat2.GetField("ELEV")].GetGeometryRef()
        geom_union = geom2.Union(geom3)
        elev[feat2.GetField("ELEV")].SetGeometry(geom_union)
        lyr3.SetFeature(elev[feat2.GetField("ELEV")])
print(f"Fusion effectuée des entités ayant le même attribut ELEV")

# Tri de la liste lst_elev dans l'ordre croissant
lst_elev = sorted(lst_elev)
for index in range(len(lst_elev) - 1):
    elev_class_sup = lst_elev[index + 1]
    elev_class_inf = lst_elev[index]
    lyr3.ResetReading()
    for feat in lyr3:
        if feat.GetField("ELEV") == elev_class_sup:
            feat_class_sup = feat
        if feat.GetField("ELEV") == elev_class_inf:
            feat_class_inf = feat
    geom_sup = feat_class_sup.GetGeometryRef()
    geom_inf = feat_class_inf.GetGeometryRef()
    geom_diff = geom_inf.Difference(geom_sup)
    feat_class_inf.SetGeometry(geom_diff)
    lyr3.SetFeature(feat_class_inf)
print(f"Suppression effectuée des parties des entités de niveau ELEV supérieur incluses dans les entités de niveau ELEV inférieur")

# Recalcul des champs 'Surface'
lyr3.ResetReading()
for feat in lyr3:
    geom = feat.GetGeometryRef()
    geom_area = geom.Area()
    feat.SetField("Surface", geom_area)
    lyr3.SetFeature(feat)

# Close the new layers
lyr3 = None
lyr2 = None
lyr = None
ds = None

# Close the original layer
lyr0 = None
ds0 = None





