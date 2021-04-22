from libensemble.tools.alloc_support import avail_worker_ids, sim_work, gen_work, count_gens


def give_sim_work_first(W, H, sim_specs, gen_specs, alloc_specs, persis_info):
    """
    This allocation function gives (in order) entries in ``H`` to idle workers
    to evaluate in the simulation function. The fields in ``sim_specs['in']``
    are given. If all entries in `H` have been given a be evaluated, a worker
    is told to call the generator function, provided this wouldn't result in
    more than ``alloc_specs['user']['num_active_gen']`` active generators.

    This fast_alloc variation of give_sim_work_first is useful for cases that
    simply iterate through H, issuing evaluations in order and, in particular,
    is likely to be faster if there will be many small evaluations, given that
    this function contains fewer column length operations.

    .. seealso::
        `test_fast_alloc.py <https://github.com/Libensemble/libensemble/blob/develop/libensemble/tests/regression_tests/test_fast_alloc.py>`_ # noqa
    """

    Work = {}
    gen_count = count_gens(W)

    for i in avail_worker_ids(W):
        # Skip any cancelled points
        while persis_info['next_to_give'] < len(H) and H[persis_info['next_to_give']]['cancel_requested']:
            persis_info['next_to_give'] += 1

        # Give sim work if possible
        if persis_info['next_to_give'] < len(H):

            sim_work(Work, i, sim_specs['in'], [persis_info['next_to_give']], [])
            persis_info['next_to_give'] += 1

        elif gen_count < alloc_specs['user'].get('num_active_gens', gen_count+1):

            # Give gen work
            persis_info['total_gen_calls'] += 1
            gen_count += 1
            gen_in = gen_specs.get('in', [])
            return_rows = range(len(H)) if gen_in else []
            gen_work(Work, i, gen_in, return_rows, persis_info.get(i))

    return Work, persis_info
