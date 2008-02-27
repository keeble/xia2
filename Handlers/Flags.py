#!/usr/bin/env python
# Flags.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 4th May 2007
# 
# A singleton to handle flags, which can be imported more easily
# as it will not suffer the problems with circular references that
# the CommandLine singleton suffers from.

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

class _Flags:
    '''A singleton to manage boolean flags.'''

    def __init__(self):
        self._quick = False
        self._fiddle_sd = False
        self._migrate_data = False
        self._trust_timestaps = False
        self._parallel = 0
        self._ccp4_61 = False

        # File from which to copy the FreeR_flag column
        self._freer_file = None

        # these are development parameters for the XDS implementation
        self._z_min = 0.0
        self._refine = True
        self._zero_dose = False
        self._relax = True

        # options to support the -spacegroup flag - the spacegroup is
        # set from this, the lattice and pointgroup derived from such
        self._spacegroup = None
        self._pointgroup = None
        self._lattice = None

        # and these for the mosflm implementation
        self._cellref_mode = 'both'
        self._old_mosflm = False

        # and these are general rejection criteria
        self._rejection_threshold = 1.5
        self._i_over_sigma_limit = 2.0
        
        return

    def set_ccp4_61(self, ccp4_61):
        self._ccp4_61 = ccp4_61
        return

    def get_ccp4_61(self):
        return self._ccp4_61

    def set_cellref_mode(self, cellref_mode):
        if not cellref_mode in ['default', 'parallel', 'orthogonal', 'both']:
            raise RuntimeError, 'cellref_mode %s unknown' % cellref_mode

        self._cellref_mode = cellref_mode

        return

    def set_spacegroup(self, spacegroup):
        '''A handler for the command-line option -spacegroup - this will
        set the spacegroup and derive from this the pointgroup and lattice
        appropriate for such...'''

        from Handlers.Syminfo import Syminfo

        # validate by deriving the pointgroup and lattice...

        pointgroup = Syminfo.get_pointgroup(spacegroup)
        lattice = Syminfo.get_lattice(spacegroup)

        # assign

        self._spacegroup = spacegroup
        self._pointgroup = pointgroup
        self._lattice = lattice

        # debug print

        from Handlers.Streams import Debug

        Debug.write('Derived information from spacegroup flag: %s' % \
                    spacegroup)
        Debug.write('Pointgroup: %s  Lattice: %s' % (pointgroup, lattice))

        return

    def get_spacegroup(self):
        return self._spacegroup

    def get_pointgroup(self):
        return self._pointgroup

    def get_lattice(self):
        return self._lattice

    def get_cellref_mode(self):
        return self._cellref_mode

    def set_quick(self, quick):
        self._quick = quick
        return

    def get_quick(self):
        return self._quick

    def set_fiddle_sd(self, fiddle_sd):
        self._fiddle_sd = fiddle_sd
        return

    def get_fiddle_sd(self):
        return self._fiddle_sd

    def set_relax(self, relax):
        self._relax = relax
        return

    def get_relax(self):
        return self._relax

    def set_migrate_data(self, migrate_data):
        self._migrate_data = migrate_data
        return

    def get_migrate_data(self):
        return self._migrate_data

    def set_trust_timestamps(self, trust_timestamps):
        self._trust_timestamps = trust_timestamps
        return

    def get_trust_timestamps(self):
        return self._trust_timestamps

    def set_old_mosflm(self, old_mosflm):
        self._old_mosflm = old_mosflm
        return

    def get_old_mosflm(self):
        return self._old_mosflm

    def set_parallel(self, parallel):
        self._parallel = parallel
        return

    def get_parallel(self):
        return self._parallel

    def set_z_min(self, z_min):
        self._z_min = z_min
        return

    def get_z_min(self):
        return self._z_min

    def set_freer_file(self, freer_file):

        # mtzdump this file to make sure that there is a FreeR_flag
        # column therein...

        freer_file = os.path.abspath(freer_file)

        if not os.path.exists(freer_file):
            raise RuntimeError, '%s does not exist' % freer_file

        from Wrappers.CCP4.Mtzdump import Mtzdump

        mtzdump = Mtzdump()
        mtzdump.set_hklin(freer_file)
        mtzdump.dump()
        
        if not 'FreeR_flag' in [t[0] for t in mtzdump.get_columns()]:
            raise RuntimeError, 'no FreeR_flag column in %s' % freer_file

        self._freer_file = freer_file
        return

    def get_freer_file(self):
        return self._freer_file

    def set_rejection_threshold(self, rejection_threshold):
        self._rejection_threshold = rejection_threshold
        return

    def get_rejection_threshold(self):
        return self._rejection_threshold

    def set_i_over_sigma_limit(self, i_over_sigma_limit):
        self._i_over_sigma_limit = i_over_sigma_limit
        return

    def get_i_over_sigma_limit(self):
        return self._i_over_sigma_limit

    def set_refine(self, refine):
        self._refine = refine
        return

    def get_refine(self):
        return self._refine

    def set_zero_dose(self, zero_dose):
        self._zero_dose = zero_dose
        return

    def get_zero_dose(self):
        return self._zero_dose

Flags = _Flags()




    
