import os
import shutil
import numpy as np
from libensemble.libE_worker import Worker
from libensemble.utils.loc_stack import LocationStack


def test_range_single_element():
    work = {'H_fields': ['x', 'num_nodes', 'ranks_per_node'], 'tag': 1,
    'libE_info': {'H_rows': np.array([5]), 'blocking': [2, 3, 4], 'workerID': 1}}
    assert Worker._extract_H_ranges(work) == '5', \
        'Failed to correctly parse single H row'


def test_range_two_separate_elements():
    work = {'H_fields': ['x', 'num_nodes', 'ranks_per_node'], 'tag': 1,
    'libE_info': {'H_rows': np.array([2, 8]), 'workerID': 1}}
    assert Worker._extract_H_ranges(work) == '2_8', \
        'Failed to correctly parse nonsequential H rows'


def test_range_two_ranges():
    work = {'H_fields': ['x', 'num_nodes', 'ranks_per_node'], 'tag': 1,
    'libE_info': {'H_rows': np.array([0, 1, 2, 3, 4, 7, 8]), 'workerID': 1}}
    assert Worker._extract_H_ranges(work) == '0-4_7-8', \
        'Failed to correctly parse multiple H ranges'


def test_range_mixes():
    work = {'H_fields': ['x', 'num_nodes', 'ranks_per_node'], 'tag': 1,
    'libE_info': {'H_rows': np.array([2, 3, 4, 6, 8, 9, 11, 14]), 'workerID': 1}}
    assert Worker._extract_H_ranges(work) == '2-4_6_8-9_11_14', \
        'Failed to correctly parse H row single elements and ranges.'

def test_stage_and_indicate():
    locs = LocationStack()
    calcdir = './calc'
    inputdir = './input'
    inputfile = './input/file'
    stgfile = '.COPY_PARENT_STAGED'

    for dir in [inputdir, calcdir]:
        os.makedirs(dir, exist_ok=True)

    open(inputfile, 'w')

    Worker._stage_and_indicate(locs, inputdir, calcdir, stgfile)
    assert 'file' in os.listdir(calcdir), 'File not staged into working directory'
    assert stgfile in os.listdir(calcdir), 'Stage indication file not created'


def test_clean_out_copy_back():

    class FakeWorker:
        def __init__(self, libE_specs, prefix, startdir):
            self.libE_specs = libE_specs
            self.prefix = prefix
            self.startdir = startdir

    libE_specs = {'sim_input_dir': './input', 'copy_input_to_parent': True, 'copy_back_output': True}
    prefix = './calc'
    copybackdir = './calc_back'
    startdir = '.'

    os.makedirs(copybackdir, exist_ok=True) # Normally created by manager

    fake_worker = FakeWorker(libE_specs, prefix, startdir)
    Worker._clean_out_copy_back(fake_worker)

    assert '.COPY_PARENT_STAGED' not in os.listdir(prefix), 'Stage indication file not deleted'
    assert 'file' in os.listdir(copybackdir), 'File not copied back to starting dir'

    for dir in [prefix, copybackdir, 'input']:
        shutil.rmtree(dir)


if __name__ == '__main__':
    test_range_single_element()
    test_range_two_separate_elements()
    test_range_two_ranges()
    test_range_mixes()
    test_stage_and_indicate()
    test_clean_out_copy_back()
