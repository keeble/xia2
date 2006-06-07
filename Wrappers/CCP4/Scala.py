#!/usr/bin/env python
# Scala.py
# Maintained by G.Winter
# 5th June 2006
# 
# A wrapper for the CCP4 program Scala, for scaling & merging reflections.
# 
# Provides:
# 
# Scaling of reflection data from Mosflm and other programs.
# Merging of unmerged reflection data.
# Characterisazion of data from scaling statistics.
# 
# Versions:
# 
# Since this will be a complex interface, the first stage is to satisfy the
# most simple scaling requirements, which is to say taking exactly one
# dataset from Mosflm via Sortmtz and scaling this. This will produce
# the appropriate statistics. This corresponds to Simple 1 in the use case
# documentation.
# 
# 
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Scala(DriverType = None):
    '''A factory for ScalaWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class ScalaWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Scala, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.setExecutable('scala')

            # input and output files
            self._scalepack = None

            # scaling parameters
            self._resolution = None

            # scales file for recycling
            self._scales_file = None

            # this defaults to SCALES - and is useful for when we
            # want to refine the SD parameters because we can
            # recycle the scale factors through the above interface
            self._new_scales_file = None

            # this flag indicates that the input reflections are already
            # scaled and just need merging e.g. from XDS/XSCALE.
            self._onlymerge = False

            # this is almost certainly wanted
            self._bfactor = True

            # this will often be wanted
            self._anomalous = False

            # this is almost certainly wanted
            self._tails = True

            # alternative for this is 'batch'
            self._mode = 'rotation'

            # these are only relevant for 'rotation' mode scaling
            self._spacing = 5
            self._secondary = 6

            # this defines how many cycles of
            # scaling we're allowing before convergence
            self._cycles = 20

            # less common parameters - see scala manual page:
            # (C line 1800)
            #
            # "Some alternatives
            #  >> Recommended usual case
            #  scales rotation spacing 5 secondary 6 bfactor off tails
            #
            #  >> If you have radiation damage, you need a Bfactor,
            #  >>  but a Bfactor at coarser intervals is more stable
            #  scales  rotation spacing 5 secondary 6  tails \
            #     bfactor on brotation spacing 20
            #  tie bfactor 0.5 - restraining the Bfactor also helps"

            self._brotation = None
            self._bfactor_tie = None
            
            # standard error parameters - now a dictionary to handle
            # multiple runs
            self._sd_parameters = { } 
            self._project_crystal_dataset = { }
            self._runs = []

            return

        # getter and setter methods

        def addSd_correction(self, set, sdfac, sdadd, sdb = 0.0):
            '''Add a set of SD correction parameters for a given
            set of reflections (initially set = full or partial.)'''

            if not set in ['full', 'partial', 'both']:
                raise RuntimeError, 'set not known "%s"' % set

            self._sd_parameters[set] = (sdfac, sdadd, sdb)
            return

        def setScalepack(self, scalepack):
            '''Set the output mode to POLISH UNMERGED to this
            file.'''

            self._scalepack = scalepack
            return

        def setResolution(self, resolution):
            '''Set the resolution limit for the scaling -
            default is to include all reflections.'''

            self._resolution = resolution
            return

        def setScales_file(self, scales_file):
            '''Set the file containing all of the scales required for
            this run. Used when fiddling the error parameters or
            obtaining stats to different resolutions. See also
            setNew_scales_file(). This will switch on ONLYMERGE RESTORE.'''

            self._scales_file = scales_file
            return

        def setNew_scales_file(self, new_scales_file):
            '''Set the file to which the scales will be written. This
            will allow reusing through the above interface.'''

            self._new_scales_file = new_scales_file
            return

        def setOnlymerge(self, onlymerge = True):
            '''Switch on merging only - this will presume that the
            input reflections are scaled already.'''

            self._onlymerge = onlymerge
            return

        def setBfactor(self, bfactor = True, brotation = None):
            '''Switch on/off bfactor refinement, optionally with the
            spacing for the bfactor refinement (in degrees.)'''

            self._bfactor = bfactor

            if brotation:
                self._brotation = brotation
                
            return

        def setAnomalous(self, anomalous = True):
            '''Switch on/off separating of anomalous pairs.'''

            self._anomalous = anomalous
            return

        def setTails(self, tails = True):
            '''Switch on/off tails correction.'''

            self._tails = tails
            return

        def setScaling_parameters(self, mode,
                                  spacing = None, secondary = None):
            '''Set up the scaling: mode is either rotation or batch.
            Spacing indicates the width of smoothing for scales with
            rotation mode scaling, secondary defines the number
            of spherical harmonics which can be used for the secondary
            beam correction. Defaults (5, 6) provided for these seem
            to work most of the time.'''

            if not mode in ['rotation', 'batch']:
                raise RuntimeError, 'unknown scaling mode "%s"' % mode

            if mode == 'batch':
                self._mode = 'batch'
                return

            self._mode = 'rotation'

            if spacing:
                self._spacing = spacing

            if secondary:
                self._secondary = secondary

            return

        def setCycles(self, cycles):
            '''Set the maximum number of cycles allowed for the scaling -
            this assumes the default convergence parameters.'''

            self._cycles = cycles

            return

        def check_scala_errors(self):
            '''Check for Scala specific errors. Raise RuntimeError if
            error is found.'''

            output = self.get_all_output()

            for line in output:
                if 'File must be sorted' in line:
                    raise RuntimeError, 'hklin not sorted'

            return

        def merge(self):
            '''Actually merge the already scaled reflections.'''

            self.checkHklin()
            self.checkHklout()

            if not self._onlymerge:
                raise RuntimeError, 'for scaling use scale()'

            if not self._scalepack:
                self.setTask('Merging scaled reflections from %s => %s' % \
                             (os.path.split(self.getHklin())[-1],
                              os.path.split(self.getHklout())[-1]))
            else:
                self.setTask('Merging reflections from %s => scalepack %s' % \
                             (os.path.split(self.getHklin())[-1],
                              os.path.split(self._scalepack)[-1]))

                self.addCommand_line('scalepack')
                self.addCommand_line(self._scalepack)

            self.start()
            # for the harvesting information
            self.input('usecwd')
            self.input('run 1 all')
            self.input('scales constant')
            self.input('initial unity')

            if self._anomalous:
                self.input('anomalous on')
            else:
                self.input('anomalous off')

            if self._scalepack:
                self.input('output polish unmerged')

            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
                self.check_ccp4_errors()
                self.check_scala_errors()

            except RuntimeError, e:
                try:
                    os.remove(self.getHklout())
                except:
                    pass

                if self._scalepack:
                    try:
                        os.remove(self._scalepack)
                    except:
                        pass

                raise e

            # if we scaled to a scalepack file, delete the
            # mtz file we created

            if self._scalepack:
                try:
                    os.remove(self.getHklout())
                except:
                    pass

            return self.get_ccp4_status()
            
        def scale(self):
            '''Actually perform the scaling.'''

            self.checkHklin()
            self.checkHklout()

            if self._new_scales_file:
                self.addCommand_line('SCALES')
                self.addCommand_line(self._new_scales_file)

            if self._onlymerge:
                raise RuntimeError, 'use merge() method'

            if not self._scalepack:
                self.setTask('Scaling reflections from %s => %s' % \
                             (os.path.split(self.getHklin())[-1],
                              os.path.split(self.getHklout())[-1]))
            else:
                self.setTask('Scaling reflections from %s => scalepack %s' % \
                             (os.path.split(self.getHklin())[-1],
                              os.path.split(self._scalepack)[-1]))
                             
                self.addCommand_line('scalepack')
                self.addCommand_line(self._scalepack)

            self.start()
            # for the harvesting information
            self.input('usecwd')
                
            # fixme this works ok for UC1 but won't handle anything
            # more sophisticated
            self.input('run 1 all')

            # assemble the scales command
            if self._mode == 'rotation':
                scale_command = 'scales rotation spacing %f' % self._spacing

                if self._secondary:
                    scale_command += ' secondary %f' % self._secondary

                if self._bfactor:
                    scale_command += ' bfactor on'

                    if self._brotation:
                        scale_command += ' brotation %f' % self._brotation
                    
                else:
                    scale_command += ' bfactor off'

                if self._tails:
                    scale_command += ' tails'

                self.input(scale_command)

            else:

                scale_command = 'scales batch'
                    
                if self._bfactor:
                    scale_command += ' bfactor on'

                    if self._brotation:
                        scale_command += ' brotation %f' % self._brotation
                    
                else:
                    scale_command += ' bfactor off'

                if self._tails:
                    scale_command += ' tails'

                self.input(scale_command)

            # next any 'generic' parameters

            if self._resolution:
                self.input('resolution %f' % self._resolution)

            self.input('cycles %d' % self._cycles)

            for key in self._sd_parameters:
                # the input order for these is sdfac, sdB, sdadd...
                parameters = self._sd_parameters[key]
                self.input('sdcorrection %s %f %f %f' % \
                           (key, parameters[0], parameters[2], parameters[1]))

            if self._anomalous:
                self.input('anomalous on')
            else:
                self.input('anomalous off')

            if self._scalepack:
                self.input('output polish unmerged')

            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
                self.check_ccp4_errors()
                self.check_scala_errors()

            except RuntimeError, e:
                try:
                    os.remove(self.getHklout())
                except:
                    pass

                if self._scalepack:
                    try:
                        os.remove(self._scalepack)
                    except:
                        pass

                raise e

            # if we scaled to a scalepack file, delete the
            # mtz file we created

            if self._scalepack:
                try:
                    os.remove(self.getHklout())
                except:
                    pass

            return self.get_ccp4_status()
            

    return ScalaWrapper()

if __name__ == '__main__':

    # run a couple of tests - this will depend on the unit tests for
    # XIACore having been run...

    s = Scala()
    
    hklin_unsorted = os.path.join(os.environ['DPA_ROOT'],
                                  'Data', 'Test', 'Mtz', '12287_1_E1_1_10.mtz')
    hklin = os.path.join(os.environ['XIA2CORE_ROOT'],
                         'Python', 'UnitTest', '12287_1_E1_sorted.mtz')

    hklout = '12287_1_E1_scaled.mtz'

    s.setHklin(hklin_unsorted)
    s.setHklout(hklout)

    s.setResolution(1.65)

    # switch on all of the options I want
    s.setAnomalous()
    s.setTails()
    s.setBfactor()

    s.setScaling_parameters('rotation')

    # this is in the order fac, add, B
    s.addSd_correction('full', 1.0, 0.02, 15.0)
    s.addSd_correction('partial', 1.0, 0.00, 15.0)

    print s.scale()

    s.write_log_file('scala.log')
    

