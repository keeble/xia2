import sys
import os
import math
from scitbx import matrix
from scitbx.math.euler_angles import xyz_angles
from scitbx.math import r3_rotation_axis_and_angle_as_matrix

sys.path.append(os.environ['XIA2_ROOT'])

from cftbx.coordinate_frame_converter import coordinate_frame_converter

def ersatz_misset(integrate_lp):
    a_s = []
    b_s = []
    c_s = []

    for record in open(integrate_lp):
        if 'COORDINATES OF UNIT CELL A-AXIS' in record:
            a = map(float, record.split()[-3:])
            a_s.append(matrix.col(a))
        elif 'COORDINATES OF UNIT CELL B-AXIS' in record:
            b = map(float, record.split()[-3:])
            b_s.append(matrix.col(b))
        elif 'COORDINATES OF UNIT CELL C-AXIS' in record:
            c = map(float, record.split()[-3:])
            c_s.append(matrix.col(c))

    assert(len(a_s) == len(b_s) == len(c_s))

    ub0 = matrix.sqr(a_s[0].elems + b_s[0].elems + c_s[0].elems).inverse()

    for j in range(len(a_s)):
        ub = matrix.sqr(a_s[j].elems + b_s[j].elems + c_s[j].elems).inverse()
        print '%7.3f %7.3f %7.3f' % tuple(xyz_angles(ub.inverse() * ub0))

    return

def parse_xds_xparm_scan_info(xparm_file):
    '''Read an XDS XPARM file, get the scan information.'''

    values = map(float, open(xparm_file).read().split())

    assert(len(values) == 42)

    img_start = values[0]
    osc_start = values[1]
    osc_range = values[2]

    return img_start, osc_start, osc_range

def nint(a):
    return int(round(a))

def ersatz_misset_predict(xparm_xds, spot_xds):
    '''As well as possible, try to predict the misorientation angles as a
    function of frame # from the indexed spots from the XDS IDXREF step.
    Calculation will be performed in CBF coordinae frame.'''

    cfc = coordinate_frame_converter(xparm_xds)
    axis = cfc.get_c('rotation_axis')
    wavelength = cfc.get('wavelength')
    beam = (1.0 / wavelength) * cfc.get_c('sample_to_source').normalize()
    U, B = cfc.get_u_b()
    UB = U * B
    
    detector_origin = cfc.get_c('detector_origin')
    detector_fast = cfc.get_c('detector_fast')
    detector_slow = cfc.get_c('detector_slow')
    pixel_size_fast, pixel_size_slow = cfc.get('detector_pixel_size_fast_slow')
    size_fast, size_slow = cfc.get('detector_size_fast_slow')
    
    img_start, osc_start, osc_range = parse_xds_xparm_scan_info(xparm_xds)

    for record in open(spot_xds):
        values = map(float, record.split())
        if len(values) != 7:
            continue
        hkl = tuple(map(nint, values[-3:]))
        if hkl == (0, 0, 0):
            continue

        x, y, f = values[:3]

        phi = ((f - img_start + 1) * osc_range + osc_start) * math.pi / 180.0
    
        lab_xyz = detector_origin + \
                  detector_fast * x * pixel_size_fast + \
                  detector_slow * y * pixel_size_slow

        rec_xyz = ((1.0 / wavelength) * lab_xyz.normalize() + beam).rotate(
            axis, - phi)

        calc_xyz = UB * hkl

        # now compute vector and angle to overlay calculated position on
        # observed position, then convert this to a matrix

        shift_axis = calc_xyz.cross(rec_xyz)
        shift_angle = calc_xyz.angle(rec_xyz)

        M = matrix.sqr(r3_rotation_axis_and_angle_as_matrix(
            shift_axis, shift_angle))

        rx, ry, rz = xyz_angles(M)

        print '%.3f %.3f %.3f %.3f' % (phi * 180.0 / math.pi, rx, ry, rz)
        
if __name__ == '__main__':
    ersatz_misset_predict(sys.argv[1], sys.argv[2])
                                  
