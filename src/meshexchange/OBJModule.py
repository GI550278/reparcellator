from PIL import Image as PILImage
from io import BytesIO


class OBJModule:
    def __init__(self):
        pass

    def extendedExchangeToOBJFile(self, e, out_dir, out_name):
        out_obj = out_dir + "\\" + out_name + ".obj"
        out_mdl = out_dir + "\\" + out_name + ".mdl"

        mdl_file = open(out_mdl, 'w')
        obj_file = open(out_obj, 'w')

        for subpartIndex in range(len(e.parts[0]['subparts'])):
            subpart = e.parts[0]['subparts'][subpartIndex]
            OnTexture = subpart['imageIndex'] is not None

            if OnTexture:
                tex_name = out_name + '_' + str(subpartIndex)
                out_tex = out_dir + "\\" + tex_name + ".jpg"

                imageBlob = e.images[subpart['imageIndex']]['imageBlob']
                blob = BytesIO(imageBlob)
                img = PILImage.open(blob)
                img.save(out_tex, format='jpeg')

                mdl_file.write('newmtl material' + str(subpartIndex) + '\n')
                mdl_file.write('Ka 1.000000 1.000000 1.000000\n')
                mdl_file.write('Kd 1.000000 1.000000 1.000000\n')
                mdl_file.write('Ks 0.000000 0.000000 0.000000\n')
                mdl_file.write('Tr 1.000000\n')
                mdl_file.write('illum 1\n')
                mdl_file.write('Ns 0.000000\n')
                mdl_file.write('map_Kd ' + tex_name + '.jpg\n')

                obj_file.write('mtllib ' + out_name + '.mdl\n')

        shifts = [1]
        for subpartIndex in range(len(e.parts[0]['subparts'])):
            subpart = e.parts[0]['subparts'][subpartIndex]

            for v in subpart['vertices']:
                v2 = [v[0], -v[2], v[1]]
                obj_file.write('v ' + ' '.join(map(str, map(lambda x: round(x, 3), v2))))
                obj_file.write('\n')

            shifts.append(shifts[subpartIndex] + len(subpart['vertices']))

        for subpartIndex in range(len(e.parts[0]['subparts'])):
            subpart = e.parts[0]['subparts'][subpartIndex]

            for vt in subpart['texCoords']:
                obj_file.write('vt ' + str(vt[0]) + ' ' + str(1 - vt[1]))
                obj_file.write('\n')

        for subpartIndex in range(len(e.parts[0]['subparts'])):
            shift = shifts[subpartIndex]
            subpart = e.parts[0]['subparts'][subpartIndex]

            OnTexture = subpart['imageIndex'] is not None
            if OnTexture:
                obj_file.write('usemtl material' + str(subpartIndex) + '\n')
            for f in subpart['indices']:
                obj_file.write('f {0}/{0} {1}/{1} {2}/{2}'.format(*list(map(lambda x: x + shift, f))))
                obj_file.write('\n')

        mdl_file.close()
        obj_file.close()
