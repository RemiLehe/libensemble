# """
# Runs libEnsemble 1D sampling test with worker profiling.
#
# Execute via one of the following commands (e.g. 3 workers):
#    mpiexec -np 4 python3 test_1d_sampling.py
#    python3 test_1d_sampling.py --nworkers 3 --comms local
#    python3 test_1d_sampling.py --nworkers 3 --comms tcp
#
# The number of concurrent evaluations of the objective function will be 4-1=3.
# """

# Do not change these lines - they are parsed by run-tests.sh
# TESTSUITE_COMMS: mpi local tcp
# TESTSUITE_NPROCS: 2 4

import numpy as np
import os

from libensemble.libE import libE
from libensemble.sim_funcs.one_d_func import one_d_example as sim_f
from libensemble.gen_funcs.sampling import latin_hypercube_sample as gen_f
from libensemble.utils import parse_args, add_unique_random_streams

nworkers, is_master, libE_specs, _ = parse_args()

libE_specs['profile_worker'] = True

sim_specs = {'sim_f': sim_f, 'in': ['x'], 'out': [('f', float)]}

gen_specs = {'gen_f': gen_f,
             'out': [('x', float, (1,))],
             'user': {'gen_batch_size': 500,
                      'lb': np.array([-3]),
                      'ub': np.array([3]),
                      }
             }

persis_info = add_unique_random_streams({}, nworkers + 1)

exit_criteria = {'gen_max': 501}

# Perform the run
H, persis_info, flag = libE(sim_specs, gen_specs, exit_criteria, persis_info,
                            libE_specs=libE_specs)

if is_master:
    assert len(H) >= 501
    print("\nlibEnsemble with random sampling has generated enough points")

    prof_files = ['worker_{}.prof'.format(i+1) for i in range(nworkers)]
    for file in prof_files:
        assert file in os.listdir(), 'Expected profile {} not found after run'.format(file)
        with open(file, 'r') as f:
            data = f.read().split()
            num_calls = int(data[0])
            num_worker_funcs_profiled = sum(['libE_worker' in i for i in data])
        assert num_calls >= 600, 'Insufficient number of function calls ' + \
            'recorded: ' + num_calls
        assert num_worker_funcs_profiled >= 8, 'Insufficient number of ' + \
            'libE_worker functions profiled: ' + num_worker_funcs_profiled

        os.remove(file)
