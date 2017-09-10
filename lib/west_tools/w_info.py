# Copyright (C) 2017 Matthew C. Zwier and Lillian T. Chong
#
# This file is part of WESTPA.
#
# WESTPA is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# WESTPA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WESTPA.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, division; __metaclass__ = type
import logging
import itertools

# Let's suppress those numpy warnings.
import warnings
#warnings.filterwarnings('ignore', category=DeprecationWarning)
#warnings.filterwarnings('ignore', category=RuntimeWarning)
#warnings.filterwarnings('ignore', category=FutureWarning)

import sys, random, math
import numpy, h5py
import numpy as np
from h5py import h5s

import westpa
from west.data_manager import weight_dtype, n_iter_dtype, seg_id_dtype
from westtools import (WESTMasterCommand, WESTTool, WESTDataReader, IterRangeSelection, WESTSubcommand,
                       ProgressIndicatorComponent, BinMappingComponent)
from westpa import h5io

class WIWest(WESTSubcommand):
    subcommand = 'init'
    help_text = 'Pull information from a WESTPA HDF5 file without the configuration (rc) present.'
    description = '''\
'''
    def __init__(self, parent):
        super(WIWest,self).__init__(parent)
        
        # We're trying to initialize the west.h5 file, if available.
        # However, we can't guarantee that it exists.
        self.data_reader = WESTDataReader()
        self.iter_range = IterRangeSelection()
        self.binning = BinMappingComponent()
        self.data_manager = None
        
        self.output_filename = None
        # This is actually applicable to both.
        self.assignment_filename = None
        
        self.output_file = None
        self.assignments_file = None
        
        self.evolution_mode = None
        
        self.mcbs_alpha = None
        self.mcbs_acalpha = None
        self.mcbs_nsets = None

        # Now we're adding in things that come from the old w_kinetics
        self.do_compression = True
        
            
    def add_args(self, parser):
        self.data_reader.add_args(parser)
        #subparsers = parser.add_subparsers(help='available commands')
        #info_parser = subparsers.add_parser('init', help='Display information about binning.')
        parser.add_argument('-n', '--n-iter', type=int, 
                                 help='''Consider initial points of segment N_ITER (default: current iteration).''')
        parser.add_argument('--detail', action='store_true',
                                 help='''Display detailed per-bin information in addition to summary
                                 information.''')
        parser.add_argument('-d', '--data', type=str, default=None,
                                 help='''The list of data to output.''')
        parser.add_argument('-l', '--line', action='store_true',
                                 help='''Report as single line.  Otherwise, use multiline key: value report.''')
        suppress = ['--bins-from-system', '--bins-from-expr', '--bins-from-function', '--bins-from-file']
        self.binning.add_args(parser, suppress=suppress)
        #self.iter_range.include_args['iter_step'] = True
        #self.iter_range.add_args(parser)

        #iogroup = parser.add_argument_group('input/output options')
        #iogroup.add_argument('-a', '--assignments', default='assign.h5',
        #                    help='''Bin assignments and macrostate definitions are in ASSIGNMENTS
        #                    (default: %(default)s).''')
        
        #iogroup.add_argument('-o', '--output', dest='output', default=self.default_output_file,
        #                    help='''Store results in OUTPUT (default: %(default)s).''')

    def process_args(self, args):
        # Open the data reader, which is necessary...
        self.data_reader.process_args(args)
        self.data_manager = self.data_reader.data_manager
        self.data_reader.open(mode='r')
        self.n_iter = getattr(args,'n_iter', None) or 1
        self.data = getattr(args, 'data', None)
        if self.data is not None:
            self.data = self.data.split(' ')
        # We don't seem to know the bin hash, but heeeey.  If it the iter is 1, I think it's assumed/enforced
        # that the bin hash is what we initialized the simulation with.
        if self.n_iter == 1:
            self.binning.mapper_source_hash = self.data_manager.we_h5file['bin_topologies']['index']['hash'][0]
        self.binning.set_we_h5file_info(self.n_iter, self.data_reader)
        self.binning.process_args(args)
        self.line = getattr(args, 'line')
        self.args = args
        #with self.data_reader:
        #    self.iter_range.process_args(args, default_iter_step=None)
        #if self.iter_range.iter_step is None:
            #use about 10 blocks by default
        #    self.iter_range.iter_step = max(1, (self.iter_range.iter_stop - self.iter_range.iter_start) // 10)
        
        #self.output_filename = args.output
        #self.assignments_filename = args.assignments

    def w_info(self):
        #print(dir(self.data_manager))
        #print(self.data_manager.we_h5file)
        #print(self.data_manager.current_iteration)
        #print(self.data_manager.get_iter_group(1).keys())
        #print(self.data_manager.get_iter_group(1).attrs.keys())
        #print(self.binning.mapper)
        # Okay, that seems to work, now.  We have the bin mapper, ergo we can...
        #iter_group = self.data_manager.get_iter_group(self.n_iter)
        #print(iter_group.keys())
        #print(dir(self.binning.mapper))
        #print(self.binning.mapper.boundaries)
        #print(self.binning.mapper.labels)
        west = self.WESTInfoBlob(self.data_reader, self.binning, self.args, self.n_iter)
        #print(west.binning.mapper.labels)
        #west.n_iter = 19
        #print(west.binning.mapper.labels)
        #print(west.iter_group.keys())
        #for tstate in west.tstates:
        #    print(tstate)
        #print(west.recycling_events)
        #print(west.aggregate_walkers)
        #self.report_default_n_iter(west)
        self.print_report(west, line=self.line, args=self.data)

    def lprint(self, k, l, ls, s=':'):
        import types, string
        if type(l) == types.ListType or type(l) == types.TupleType:
            #print(str(k).rjust(ls), s)
            print(string.capwords(str(k).replace('_',' ').replace('-',' ').replace('.', ' ')).rjust(ls), s)
            for i in l:
                self.lprint(k=' ',l=i,ls=ls,s=' ')
        elif type(l) == types.DictType:
            print(string.capwords(str(k).replace('_',' ').replace('-',' ').replace('.', ' ')).rjust(ls), s)
            label_size = 0
            for key, value in l.iteritems():
                label_size = max(label_size, len(key))
            for key, i in l.iteritems():
                self.lprint(k=key,l=i,ls=ls+label_size+len(s),s=':')
        else:
            print(string.capwords(str(k).replace('_',' ').replace('-',' ').replace('.', ' ')).rjust(ls), s, str(l).ljust(20))
            #print(str(k).rjust(ls), s, str(l).ljust(20))

    def deepgetattr(self, obj, attr):
        # We check to see if the object is callable.  If so, do it.  Why not?  Otherwise, no.
        # First, remove any function calls...
        #print(attr)
     #   no_func_call = attr.split('(')
    #    if callable(reduce (getattr, no_func_call[0].split('.'), obj)) == True:
        try:
            # DANGEROUS AS
            return eval(attr, {'__builtins__': {}}, obj.__dict__)
            #print("YAY")
            #func = reduce (getattr, no_func_call[0].split('.'), obj)
            #args = no_func_call[1].replace(')','')
            #args = args.split('[')
            #print(args)
            #if len(args) > 1:
            #    args[1] = args[1].replace(']','')
            #    return func(args[0])[args[1]]
            #else:
            #    return func(args[0])
        except:
            return reduce (getattr, attr.split('.'), obj)

    def print_report(self, west, line=False, s1=':', s2=';', args=None):
        # Here, we're just going to print out these quantities...
        # We'll want to put in some more appropriate formatting eventually, but
        if args == None:
            args = ['n_iter', 'aggregate_walkers', 'recycling_events', 'tstates', 'mapper.labels', 'mapper.boundaries']
        import pprint, types
        output = {}
        label_size = 0
        for arg in args:
            try:
                if type(self.deepgetattr(west,arg)) == types.GeneratorType:
                    output[arg] = []
                    for t in self.deepgetattr(west,arg):
                        output[arg].append(t)
                else:
                    output[arg] = self.deepgetattr(west,arg)
                label_size = max(label_size, len(arg))
            except Exception as e:
                # Not an attribute.  Ergo, just... throw in an error, and go from there.
                output[arg] = 'ERROR - ' + str(e)
        if line == False:
            for arg in args:
                k = arg
                v = output[k]
                #self.lprint(k='', l=output, ls=0, s='')
                self.lprint(k,v,label_size, s1)
        else:
            #output_string = ''
            #for arg in args:
            #    k = arg
            #    v = output[k]
            print(s2.join(str(output[arg]) for arg in args))
                #self.line_print(k, v, s2)

    class WESTInfoBlob():
        '''
        A little class to ease pulling data in from WESTPA in a 'reporter friendly' way.
        Nothing too large, mind you.  But it should utilize the data manager and h5file without the need
        for the rc, and it should be able to return data that can be utilized in reporting.
        '''
        def __init__(self, data_reader, binning, args, n_iter = 1):
            # west is the west h5file from the data reader.
            # We should be able to change the iteration, if desired.
            self.data_reader = data_reader
            self.data_manager = self.data_reader.data_manager
            self.we_h5file = self.data_manager.we_h5file
            self.binning = binning
            self.args = args
            #self.iter_group = None
            self.n_iter = n_iter

        @property
        def n_iter(self):
            return self._n_iter

        @n_iter.setter
        def n_iter(self, n_iter):
            self._n_iter = n_iter
            if self._n_iter == 1:
                self.binning.mapper_source_hash = self.data_manager.we_h5file['bin_topologies']['index']['hash'][0]
            self.binning.set_we_h5file_info(self._n_iter, self.data_reader)
            self.binning.process_args(self.args)
            self.iter_group = self.data_manager.get_iter_group(self._n_iter)

        @property
        def mapper(self):
            return self.binning.mapper

        @property
        def iter_group(self):
            return self._iter_group
        
        @iter_group.setter
        def iter_group(self, group):
            self._iter_group = group

        @property
        def tstates(self):
            if 'tstates' in self.iter_group.keys():
                for label,pcoord in itertools.izip(self.iter_group['tstates']['index'],self.iter_group['tstates']['pcoord']):
                    # We want the bin id, as well.  Call the bin mapper assign function.
                    binid = self.mapper.assign([pcoord])
                    yield {'Label': label,'Progress Coordinate': pcoord, 'Bin ID': binid}

        @property
        def recycling_events(self):
            # Just go through and sum up the aggregate number of events.
            self._recycling_events = 0
            for i in range(1, self.n_iter+1):
                iter_group = self.data_manager.get_iter_group(i)
                self._recycling_events += len(np.where(iter_group['seg_index']['endpoint_type'] == 3)[0])
            return self._recycling_events

        @property
        def aggregate_walkers(self):
            self._aggregate_walkers = self.data_manager.we_h5file['summary']['n_particles'][:self.n_iter].sum()
            return self._aggregate_walkers



    def go(self):
        self.w_info()


    def print_function(self, west):
        ''' Built in print function to print requested information '''
        return 0

class WDirect(WESTMasterCommand, WESTTool):
    prog='w_direct'
    #subcommands = [AvgTraceSubcommand,AvgMatrixSubcommand]
    subcommands = [WIWest]
    subparsers_title = 'direct kinetics analysis schemes'

if __name__ == '__main__':
    WDirect().main()