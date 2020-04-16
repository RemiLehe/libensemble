"""
This module contains functions for implementing an persistent NSGA2 generator
function. The evaluation of the fitness of the current population's members
occurs in `evaluate_pop`, where the points are communicated to the libEnsemble
manager; the manager coordinates their evaluation and then returns their
`fitness_values`.
"""

__all__ = ['deap_nsga2','evaluate_pop','nsga2_toolbox']

from deap import base, creator, tools
import numpy as np
import array

from libensemble.message_numbers import STOP_TAG, PERSIS_STOP, FINISHED_PERSISTENT_GEN_TAG
from libensemble.tools.gen_support import sendrecv_mgr_worker_msg


def uniform(low, up, size=None):
    try:
        return [np.random.uniform(a, b) for a, b in zip(low, up)]
    except TypeError:
        return [np.random.uniform(a, b) for a, b in zip([low] * size, [up] * size)]


def nsga2_toolbox(gen_specs):
    '''
    Returns a DEAP toolbox for use in a NSGA2 loop, derived from `this example.
    <https://github.com/ChristopherMayes/xdeap/blob/master/xdeap/nsga2_tools.py>`_
    '''
    w = gen_specs['user']['weights']
    eta = gen_specs['user']['eta']
    inp = gen_specs['user']['indpb']
    lb = gen_specs['user']['lb']
    ub = gen_specs['user']['ub']
    dim = gen_specs['user']['indiv_size']

    creator.create('MyFitness', base.Fitness, weights=w)
    creator.create('Individual', array.array, typecode='d', fitness=creator.MyFitness)
    toolbox = base.Toolbox()

    toolbox.register('attr_float', uniform, lb, ub, dim)
    toolbox.register('individual', tools.initIterate, creator.Individual, toolbox.attr_float)
    toolbox.register('population', tools.initRepeat, list, toolbox.individual)

    toolbox.register('mate', tools.cxSimulatedBinaryBounded, low=lb, up=ub, eta=eta)
    toolbox.register('mutate', tools.mutPolynomialBounded, low=lb, up=ub, eta=eta, indpb=inp)
    toolbox.register('select', tools.selNSGA2)

    return toolbox


def evaluate_pop(g, deap_object, Out, comm):
    '''
    Evaluates the fitness of a population by communicating the individuals in
    the population to the libEnsemble manager, and then awaiting their fitness_values.
    '''
    # Take population or list of individuals
    # Sending individuals from population to sim to calc fitness
    for index, ind in enumerate(deap_object):
        Out['individual'][index] = ind
        Out['generation'][index] = g
    # Sending work to sim_f, which is defined in main call script
    # A fitness value will be returned in calc_in
    tag, Work, calc_in = sendrecv_mgr_worker_msg(comm, Out)

    if tag not in [STOP_TAG, PERSIS_STOP]:
        for i, ind in enumerate(deap_object):
            # Attaching fitness values from sim to population
            # i.e. replacing values with those generated by the sim

            if isinstance(calc_in['fitness_values'][i], tuple):
                ind.fitness.values = calc_in['fitness_values'][i]
            else:
                ind.fitness.values = (calc_in['fitness_values'][i],)

    return deap_object, tag


def deap_nsga2(H, persis_info, gen_specs, libE_info):
    '''
    An implementation of the NSGA2 evolutionary algorithm.
    '''
    # Check to make sure boundaries are list, not array
    if isinstance(gen_specs['user']['lb'], list):
        if isinstance(gen_specs['user']['ub'], list):
            pass
    else:
        print('Lower or Upper bound is not a list')
        print('This will break DEAP crossover function')
        assert isinstance(gen_specs['user']['lb'], list), "lb is wrong type"
        assert isinstance(gen_specs['user']['ub'], list), "ub is wrong type"

    # Initialize NSGA2 DEAP toolbox
    toolbox = nsga2_toolbox(gen_specs)

    g = 0  # generation count
    # CXPB  is the probability with which two individuals are crossed
    MU, CXPB = gen_specs['user']['pop_size'], gen_specs['user']['cxpb']
    pop = toolbox.population(n=MU)  # MU is Population size ( # of individuals)
    comm = libE_info['comm']

    # Running fitness calc for first generation
    Out = np.zeros(gen_specs['user']['pop_size'], dtype=gen_specs['out'])
    pop, tag = evaluate_pop(g, pop, Out, comm)

    # This is just to assign the crowding distance to the individuals
    # no actual selection is done
    pop = toolbox.select(pop, len(pop))

    # Begin the evolution
    while tag not in [STOP_TAG, PERSIS_STOP]:
        # A new generation
        g = g + 1
        print("-- Generation %i --" % g, flush=True)

        # Apply crossover and mutation on the offspring
        offspring = tools.selTournamentDCD(pop, len(pop))
        offspring = [toolbox.clone(ind) for ind in offspring]

        for ind1, ind2 in zip(offspring[::2], offspring[1::2]):
            if np.random.uniform() <= CXPB:
                toolbox.mate(ind1, ind2)

            toolbox.mutate(ind1)
            toolbox.mutate(ind2)
            del ind1.fitness.values, ind2.fitness.values

        # Evaluate the individuals with an invalid fitness
        # These are individuals who had their fitness deleted by crossover or mutation
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]

        # Need to check that there were invalid in divides first.
        # When using small test number of points (2, 5, etc)
        # There is a probability that there will be no invalid individuals
        if invalid_ind:
            print('Finished evaluating population, doing selection now.')
            # Running fitness calc on gens > 0
            invalid_ind, tag = evaluate_pop(g, invalid_ind, Out, comm)
            if tag not in [STOP_TAG, PERSIS_STOP]:
                # Select the next generation population
                pop = toolbox.select(pop + offspring, MU)
        else:
            print('There were no invalid individuals')
            # Don't update population
            pass

        fits = [ind.fitness.values[0] for ind in pop]
        if tag in [STOP_TAG, PERSIS_STOP]:
            # Min value when exiting
            print('Met exit criteria. Current minimum is:', np.min(fits))
        else:
            print('Current minimum:', np.min(fits))
            print('Sum of fit values at end of loop', sum(fits))

    return Out, persis_info, FINISHED_PERSISTENT_GEN_TAG
